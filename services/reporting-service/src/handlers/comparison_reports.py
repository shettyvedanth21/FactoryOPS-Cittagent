from datetime import datetime, date
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.schemas.requests import ComparisonReportRequest
from src.schemas.responses import ReportResponse
from src.repositories.report_repository import ReportRepository
from src.tasks.report_task import run_comparison_report
from src.handlers.energy_reports import (
    resolve_all_devices,
    normalize_dates_to_utc,
    validate_date_duration_seconds
)

router = APIRouter(tags=["comparison-reports"])

import logging
logger = logging.getLogger(__name__)


async def validate_device_for_comparison(device_id: str) -> dict:
    """
    Validate device exists for comparison.
    Returns device data if valid.
    Raises HTTPException if invalid.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.DEVICE_SERVICE_URL}/api/v1/devices/{device_id}"
            )
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to device service: {e}")
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "DEVICE_SERVICE_UNAVAILABLE",
                    "message": f"Cannot connect to device service: {str(e)}"
                }
            )
        
        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "DEVICE_NOT_FOUND",
                    "message": f"Device '{device_id}' not found. Please verify the device ID."
                }
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "DEVICE_SERVICE_ERROR",
                    "message": f"Device service returned status {response.status_code}"
                }
            )
        
        data = response.json()
        if isinstance(data, dict) and "data" in data:
            device_data = data["data"]
        else:
            device_data = data
        
        return device_data


def convert_dates_to_str(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_dates_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_dates_to_str(item) for item in obj]
    return obj


@router.post("", response_model=ReportResponse)
@router.post("/", response_model=ReportResponse)
async def create_comparison_report(
    request: ComparisonReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    
    if request.comparison_type == "machine_vs_machine":
        machine_a_id = request.machine_a_id
        machine_b_id = request.machine_b_id
        
        if machine_a_id == "all" or machine_b_id == "all":
            resolved_a = await resolve_all_devices(request.tenant_id)
            resolved_b = await resolve_all_devices(request.tenant_id)
            
            if not resolved_a or not resolved_b:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "NO_VALID_DEVICES",
                        "message": "No energy-capable devices found for this tenant."
                    }
                )
            
            machine_a_id = resolved_a[0] if resolved_a else None
            machine_b_id = resolved_b[0] if resolved_b else None
        
        if machine_a_id:
            await validate_device_for_comparison(machine_a_id)
        if machine_b_id:
            await validate_device_for_comparison(machine_b_id)
        
        if request.start_date and request.end_date:
            start_dt, end_dt = normalize_dates_to_utc(request.start_date, request.end_date)
            if not validate_date_duration_seconds(start_dt, end_dt):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "INVALID_DATE_RANGE",
                        "message": "Date range must be at least 24 hours apart."
                    }
                )
    
    report_id = str(uuid4())
    
    params = request.model_dump()
    params = convert_dates_to_str(params)
    
    await repo.create_report(
        report_id=report_id,
        tenant_id=request.tenant_id,
        report_type="comparison",
        params=params
    )
    
    task_params = {
        "tenant_id": request.tenant_id,
        "comparison_type": request.comparison_type,
        "machine_a_id": request.machine_a_id,
        "machine_b_id": request.machine_b_id,
        "start_date": str(request.start_date) if request.start_date else None,
        "end_date": str(request.end_date) if request.end_date else None,
        "device_id": request.device_id,
        "period_a_start": str(request.period_a_start) if request.period_a_start else None,
        "period_a_end": str(request.period_a_end) if request.period_a_end else None,
        "period_b_start": str(request.period_b_start) if request.period_b_start else None,
        "period_b_end": str(request.period_b_end) if request.period_b_end else None,
    }
    background_tasks.add_task(run_comparison_report, report_id, task_params)
    
    return ReportResponse(
        report_id=report_id,
        status="pending",
        created_at=datetime.utcnow().isoformat()
    )
