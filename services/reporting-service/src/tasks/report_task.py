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
from src.pdf.builder import generate_consumption_pdf
from src.storage.minio_client import minio_client, StorageError


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
                    await repo.update_report(
                        report_id,
                        status="failed",
                        error_code="INVALID_DEVICE_TYPE",
                        error_message=f"Device {device_id} is a '{device_type}' sensor. Energy reports require a power meter device (device_type=meter)."
                    )
                    return
            
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
                    error_message="No telemetry data available for selected period"
                )
                return
            
            await repo.update_report(report_id, progress=35)
            
            energy_result = calculate_energy(rows, phase_type)
            
            if is_error(energy_result):
                await repo.update_report(
                    report_id,
                    status="failed",
                    error_code=energy_result.get("error_code", "ENERGY_ERROR"),
                    error_message=energy_result.get("message", "Energy calculation failed")
                )
                return
            
            await repo.update_report(report_id, progress=50)
            
            demand_result = calculate_demand(rows, settings.DEMAND_WINDOW_MINUTES)
            
            await repo.update_report(report_id, progress=60)
            
            duration_hours = energy_result.get("duration_hours", 0)
            peak_demand_kw = demand_result.get("peak_demand_kw", 0) if not is_error(demand_result) else 0
            
            load_factor_result = calculate_load_factor(
                energy_result.get("total_kwh", 0),
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
            
            total_kvarh = reactive_result.get("total_kvarh") if not is_error(reactive_result) else None
            duration_days = (end_date - start_date).days
            
            cost_result = calculate_cost(
                energy_result.get("total_kwh", 0),
                peak_demand_kw,
                total_kvarh,
                tariff_dict,
                duration_days
            )
            
            cost_error = None
            if is_error(cost_result):
                cost_error = cost_result.get("message", "Cost calculation failed")
                cost_result = None
            
            await repo.update_report(report_id, progress=80)
            
            insights = generate_insights(
                energy_result,
                demand_result if not is_error(demand_result) else None,
                load_factor_result,
                reactive_result,
                cost_result,
                device_name,
                duration_days
            )
            
            await repo.update_report(report_id, progress=85)
            
            daily_kwh_dict = energy_result.get("daily_kwh", {})
            daily_series = [{"date": k, "kwh": round(v, 2)} for k, v in sorted(daily_kwh_dict.items())]
            
            total_from_daily = sum(d["kwh"] for d in daily_series)
            
            await repo.update_report(report_id, progress=90)
            
            pdf_data = {
                "report_id": report_id,
                "device_name": device_name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_kwh": energy_result.get("total_kwh", 0),
                "avg_power_w": energy_result.get("avg_power_w", 0),
                "min_power_w": energy_result.get("min_power_w", 0),
                "peak_power_w": energy_result.get("peak_power_w", 0),
                "peak_demand_kw": demand_result.get("peak_demand_kw", None) if not is_error(demand_result) else None,
                "demand_error": demand_result.get("message") if is_error(demand_result) else None,
                "load_factor": None if is_error(load_factor_result) else load_factor_result,
                "load_factor_error": load_factor_result.get("message") if is_error(load_factor_result) else None,
                "total_cost": cost_result.get("total_cost", None) if cost_result else None,
                "currency": tariff_dict.get("currency", "INR"),
                "daily_series": daily_series,
                "demand": None if is_error(demand_result) else demand_result,
                "demand_windows": demand_result.get("all_window_averages", []) if not is_error(demand_result) else [],
                "load_factor_data": None if is_error(load_factor_result) else load_factor_result,
                "reactive": None if is_error(reactive_result) else reactive_result,
                "pf_distribution": reactive_result.get("pf_distribution", {}) if not is_error(reactive_result) else {},
                "power_quality": None if is_error(power_quality_result) else power_quality_result,
                "power_quality_error": power_quality_result.get("message") if is_error(power_quality_result) else None,
                "cost": cost_result,
                "cost_error": cost_error,
                "insights": insights
            }
            
            def clean_for_json(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, date):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: clean_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [clean_for_json(item) for item in obj]
                return obj
            
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
                    "cost": cost_result,
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
