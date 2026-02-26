import logging
import traceback
from datetime import datetime, date, timedelta
from typing import Any

import httpx

from src.config import settings
from src.database import AsyncSessionLocal
from src.repositories.report_repository import ReportRepository
from src.repositories.tariff_repository import TariffRepository
from src.services.influx_reader import influx_reader
from src.services import (
    calculate_energy,
    calculate_demand,
    calculate_load_factor,
    calculate_reactive,
    calculate_power_quality,
    calculate_cost,
    generate_insights,
)
from src.pdf.builder import generate_consumption_pdf, generate_comparison_pdf
from src.storage.minio_client import minio_client, StorageError
from src.utils.serialization import clean_for_json, extract_engine_data


logger = logging.getLogger(__name__)


def is_error(result: dict) -> bool:
    return isinstance(result, dict) and result.get("success") is False


def get_float(val):
    if val is None:
        return 0.0
    from decimal import Decimal
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    return 0.0


async def run_consumption_report(report_id: str, params: dict) -> None:
    async with AsyncSessionLocal() as db:
        repo = ReportRepository(db)
        tariff_repo = TariffRepository(db)
        
        try:
            await repo.update_report(report_id, status="processing", progress=5)
            
            device_id = params.get("device_ids", [None])[0]
            tenant_id = params.get("tenant_id")
            start_date_str = params.get("start_date")
            end_date_str = params.get("end_date")
            
            if not device_id or device_id == "all":
                device_id = params.get("device_ids", [""])[0]
            
            if isinstance(start_date_str, str):
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            else:
                start_date = start_date_str
                
            if isinstance(end_date_str, str):
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                end_date = end_date_str
            
            if not device_id or not tenant_id or not start_date or not end_date:
                await repo.update_report(
                    report_id,
                    status="failed",
                    error_code="INVALID_PARAMS",
                    error_message="Missing required parameters"
                )
                return
            
            await repo.update_report(report_id, progress=10)
            
            async with httpx.AsyncClient() as client:
                device_response = await client.get(
                    f"{settings.DEVICE_SERVICE_URL}/api/v1/devices/{device_id}"
                )
                
                if device_response.status_code != 200:
                    await repo.update_report(
                        report_id,
                        status="failed",
                        error_code="DEVICE_NOT_FOUND",
                        error_message=f"Device {device_id} not found"
                    )
                    return
                
                device_data = device_response.json()
                if isinstance(device_data, dict) and "data" in device_data:
                    device_data = device_data["data"]
                
                device_name = device_data.get("device_name", device_id)
                device_type = device_data.get("device_type", "unknown")
                phase_type = device_data.get("phase_type", "single")
                
                if device_type not in ("meter", "power_meter", "energy_meter"):
                    logger.warning(
                        f"Device {device_id} is type '{device_type}'. Proceeding anyway - will show friendly error if no data."
                    )
            
            await repo.update_report(report_id, progress=20)
            
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            
            fields = ["power", "voltage", "current", "power_factor", 
                      "reactive_power", "frequency", "thd"]
            
            rows = await influx_reader.query_telemetry(
                device_id=device_id,
                start_dt=start_dt,
                end_dt=end_dt,
                fields=fields
            )
            
            if not rows:
                await repo.update_report(
                    report_id,
                    status="failed",
                    error_code="NO_TELEMETRY_DATA",
                    error_message="Reports cannot be generated for this device. No telemetry data available for the selected period. Please try again later."
                )
                return
            
            await repo.update_report(report_id, progress=35)
            
            energy_result = calculate_energy(rows, phase_type)
            
            if is_error(energy_result):
                await repo.update_report(
                    report_id,
                    status="failed",
                    error_code=energy_result.get("error_code", "ENERGY_ERROR"),
                    error_message=energy_result.get("error_message", "Energy calculation failed")
                )
                return
            
            await repo.update_report(report_id, progress=50)
            
            energy_data = extract_engine_data(energy_result)
            power_series = energy_data.get("power_series", [])
            
            demand_result = calculate_demand(power_series, settings.DEMAND_WINDOW_MINUTES)
            
            await repo.update_report(report_id, progress=60)
            
            duration_hours = energy_data.get("duration_hours", 0)
            
            demand_data = extract_engine_data(demand_result)
            peak_demand_kw = demand_data.get("peak_demand_kw", 0) if demand_data else 0
            
            load_factor_result = calculate_load_factor(
                energy_data.get("total_kwh", 0),
                duration_hours,
                peak_demand_kw
            )
            
            await repo.update_report(report_id, progress=65)
            
            reactive_result = calculate_reactive(rows, phase_type)
            
            await repo.update_report(report_id, progress=70)
            
            power_quality_result = calculate_power_quality(rows)
            
            await repo.update_report(report_id, progress=75)
            
            tariff = await tariff_repo.get_tariff(tenant_id)
            tariff_dict = None
            
            if tariff:
                tariff_dict = {
                    "energy_rate_per_kwh": get_float(tariff.energy_rate_per_kwh),
                    "demand_charge_per_kw": get_float(tariff.demand_charge_per_kw),
                    "reactive_penalty_rate": get_float(tariff.reactive_penalty_rate),
                    "fixed_monthly_charge": get_float(tariff.fixed_monthly_charge),
                    "power_factor_threshold": get_float(tariff.power_factor_threshold) or 0.90,
                    "currency": str(tariff.currency) if tariff.currency is not None else "INR"
                }
            else:
                tariff_dict = {
                    "energy_rate_per_kwh": 8.0,
                    "demand_charge_per_kw": 0.0,
                    "reactive_penalty_rate": 0.0,
                    "fixed_monthly_charge": 0.0,
                    "power_factor_threshold": 0.90,
                    "currency": "INR"
                }
            
            reactive_data = extract_engine_data(reactive_result)
            total_kvarh = reactive_data.get("total_kvarh") if reactive_data else None
            duration_days = (end_date - start_date).days
            
            cost_result = calculate_cost(
                energy_data.get("total_kwh", 0),
                peak_demand_kw,
                total_kvarh,
                tariff_dict,
                duration_days
            )
            
            cost_error = None
            cost_result_data = None
            if is_error(cost_result):
                cost_error = cost_result.get("error_message", "Cost calculation failed")
            else:
                cost_result_data = cost_result.get("data")
            
            await repo.update_report(report_id, progress=80)
            
            insights = generate_insights(
                energy_result,
                demand_result if not is_error(demand_result) else None,
                load_factor_result,
                reactive_result,
                cost_result_data,
                device_name,
                duration_days
            )
            
            await repo.update_report(report_id, progress=85)
            
            daily_kwh_dict = energy_data.get("daily_kwh", {})
            daily_series = [{"date": k, "kwh": round(v, 2)} for k, v in sorted(daily_kwh_dict.items())]
            
            total_from_daily = sum(d["kwh"] for d in daily_series)
            
            load_factor_data = extract_engine_data(load_factor_result)
            reactive_data = extract_engine_data(reactive_result)
            power_quality_data = extract_engine_data(power_quality_result)
            
            await repo.update_report(report_id, progress=90)
            
            pdf_data = {
                "report_id": report_id,
                "device_name": device_name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_kwh": energy_data.get("total_kwh", 0),
                "avg_power_w": energy_data.get("avg_power_w", 0),
                "min_power_w": energy_data.get("min_power_w", 0),
                "peak_power_w": energy_data.get("peak_power_w", 0),
                "peak_demand_kw": demand_data.get("peak_demand_kw", None) if demand_data else None,
                "demand_error": demand_result.get("error_message") if is_error(demand_result) else None,
                "load_factor": load_factor_data if load_factor_data else None,
                "load_factor_error": load_factor_result.get("error_message") if is_error(load_factor_result) else None,
                "total_cost": cost_result_data.get("total_cost", None) if cost_result_data else None,
                "currency": tariff_dict.get("currency", "INR"),
                "daily_series": daily_series,
                "demand": demand_data if demand_data else None,
                "demand_windows": demand_data.get("all_window_averages", []) if demand_data else [],
                "load_factor_data": load_factor_data if load_factor_data else None,
                "reactive": reactive_data if reactive_data else None,
                "pf_distribution": reactive_data.get("pf_distribution", {}) if reactive_data else {},
                "power_quality": power_quality_data if power_quality_data else None,
                "power_quality_error": power_quality_result.get("error_message") if is_error(power_quality_result) else None,
                "cost": cost_result_data,
                "cost_error": cost_error,
                "insights": insights
            }
            
            pdf_data_clean = clean_for_json(pdf_data)
            
            pdf_bytes = generate_consumption_pdf(pdf_data)
            
            await repo.update_report(report_id, progress=95)
            
            s3_key = f"reports/{tenant_id}/{report_id}.pdf"
            minio_client.upload_pdf(pdf_bytes, s3_key)
            
            await repo.update_report(
                report_id,
                status="completed",
                progress=100,
                result_json=clean_for_json({
                    "energy": energy_result,
                    "demand": demand_result,
                    "load_factor": load_factor_result,
                    "reactive": reactive_result,
                    "power_quality": power_quality_result,
                    "cost": cost_result_data,
                    "insights": insights,
                    "daily_series": daily_series,
                    "daily_total_kwh": total_from_daily
                }),
                s3_key=s3_key,
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Report {report_id} failed: {traceback.format_exc()}")
            await repo.update_report(
                report_id,
                status="failed",
                error_code="INTERNAL_ERROR",
                error_message=str(e)
            )


async def run_comparison_report(report_id: str, params: dict) -> None:
    from src.services.comparison_engine import calculate_comparison
    
    async with AsyncSessionLocal() as db:
        repo = ReportRepository(db)
        
        try:
            await repo.update_report(report_id, status="processing", progress=10)
            
            tenant_id = params.get("tenant_id")
            comparison_type = params.get("comparison_type")
            
            if comparison_type == "machine_vs_machine":
                device_a = params.get("machine_a_id")
                device_b = params.get("machine_b_id")
                start_date_str = params.get("start_date")
                end_date_str = params.get("end_date")
                
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                await repo.update_report(report_id, progress=20)
                
                async with httpx.AsyncClient() as client:
                    resp_a = await client.get(f"{settings.DEVICE_SERVICE_URL}/api/v1/devices/{device_a}")
                    resp_b = await client.get(f"{settings.DEVICE_SERVICE_URL}/api/v1/devices/{device_b}")
                    
                    device_a_data = resp_a.json()
                    device_b_data = resp_b.json()
                    
                    if isinstance(device_a_data, dict) and "data" in device_a_data:
                        device_a_data = device_a_data["data"]
                    if isinstance(device_b_data, dict) and "data" in device_b_data:
                        device_b_data = device_b_data["data"]
                
                await repo.update_report(report_id, progress=30)
                
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date, datetime.max.time())
                
                fields = ["power", "voltage", "current", "power_factor"]
                
                rows_a = await influx_reader.query_telemetry(
                    device_id=device_a, start_dt=start_dt, end_dt=end_dt, fields=fields
                )
                rows_b = await influx_reader.query_telemetry(
                    device_id=device_b, start_dt=start_dt, end_dt=end_dt, fields=fields
                )
                
                if not rows_a or not rows_b:
                    await repo.update_report(
                        report_id,
                        status="failed",
                        error_code="NO_TELEMETRY_DATA",
                        error_message="Comparative analysis cannot be generated. No telemetry data available for one or both devices in the selected period. Please try again later."
                    )
                    return
                
                await repo.update_report(report_id, progress=40)
                
                phase_type_a = device_a_data.get("phase_type", "single")
                phase_type_b = device_b_data.get("phase_type", "single")
                
                energy_a = calculate_energy(rows_a, phase_type_a)
                energy_b = calculate_energy(rows_b, phase_type_b)
                
                if is_error(energy_a) or is_error(energy_b):
                    await repo.update_report(
                        report_id,
                        status="failed",
                        error_code="ENERGY_CALCULATION_ERROR",
                        error_message="Failed to calculate energy for one or both devices"
                    )
                    return
                
                await repo.update_report(report_id, progress=60)
                
                energy_data_a = extract_engine_data(energy_a)
                energy_data_b = extract_engine_data(energy_b)
                power_series_a = energy_data_a.get("power_series", [])
                power_series_b = energy_data_b.get("power_series", [])
                
                demand_a = calculate_demand(power_series_a, settings.DEMAND_WINDOW_MINUTES)
                demand_b = calculate_demand(power_series_b, settings.DEMAND_WINDOW_MINUTES)
                
                await repo.update_report(report_id, progress=70)
                
                comparison_result = calculate_comparison(
                    energy_a, energy_b, demand_a, demand_b,
                    device_a_data.get("device_name", device_a),
                    device_b_data.get("device_name", device_b)
                )
                
                if is_error(comparison_result):
                    await repo.update_report(
                        report_id,
                        status="failed",
                        error_code=comparison_result.get("error_code", "COMPARISON_ERROR"),
                        error_message=comparison_result.get("error_message", "Comparison calculation failed")
                    )
                    return
                
                await repo.update_report(report_id, progress=80)
                
                tariff_repo = TariffRepository(db)
                tariff = await tariff_repo.get_tariff(tenant_id)
                
                tariff_dict = {
                    "energy_rate_per_kwh": 8.0,
                    "currency": "INR"
                }
                if tariff:
                    tariff_dict = {
                        "energy_rate_per_kwh": float(tariff.energy_rate_per_kwh or 8.0),
                        "currency": str(tariff.currency or "INR")
                    }
                
                await repo.update_report(report_id, progress=90)
                
                pdf_data = {
                    "report_id": report_id,
                    "device_a_name": device_a_data.get("device_name", device_a),
                    "device_b_name": device_b_data.get("device_name", device_b),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "comparison": comparison_result.get("data", {}).get("metrics", {}),
                    "winner": comparison_result.get("data", {}).get("winner"),
                    "insights": comparison_result.get("data", {}).get("insights", []),
                    "currency": tariff_dict.get("currency", "INR")
                }
                
                pdf_bytes = generate_comparison_pdf(clean_for_json(pdf_data))
                
                s3_key = f"reports/{tenant_id}/{report_id}.pdf"
                minio_client.upload_pdf(pdf_bytes, s3_key)
                
                await repo.update_report(
                    report_id,
                    status="completed",
                    progress=100,
                    result_json=clean_for_json(comparison_result),
                    s3_key=s3_key,
                    completed_at=datetime.utcnow()
                )
                
            else:
                await repo.update_report(
                    report_id,
                    status="failed",
                    error_code="NOT_IMPLEMENTED",
                    error_message="Period vs Period comparison not yet implemented"
                )
                
        except Exception as e:
            logger.error(f"Comparison report {report_id} failed: {traceback.format_exc()}")
            await repo.update_report(
                report_id,
                status="failed",
                error_code="INTERNAL_ERROR",
                error_message=str(e)
            )
