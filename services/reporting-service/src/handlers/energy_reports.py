from datetime import datetime, timedelta, date
from uuid import uuid4
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models import EnergyReport, ReportType, ReportStatus
from src.schemas.requests import ConsumptionReportRequest
from src.schemas.responses import ReportResponse
from src.repositories.report_repository import ReportRepository
from src.tasks.report_task import run_consumption_report

router = APIRouter(tags=["energy-reports"])


async def resolve_all_devices(tenant_id: str) -> list[str]:
    """
    Resolve 'all' device selection to actual device IDs.
    Returns ALL devices - let the engine decide if telemetry exists.
    No filtering by device type at this layer.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Resolving 'all' devices for tenant: {tenant_id}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{settings.DEVICE_SERVICE_URL}/api/v1/devices"
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
        
        if response.status_code != 200:
            logger.error(f"Device service returned {response.status_code}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "DEVICE_SERVICE_ERROR",
                    "message": f"Device service returned status {response.status_code}"
                }
            )
        
        data = response.json()
        devices = data if isinstance(data, list) else data.get("data", [])
        
        logger.info(f"Device service returned {len(devices)} total devices")
        
        all_device_ids = [d.get("device_id") for d in devices if d.get("device_id")]
        
        logger.info(f"Resolved {len(all_device_ids)} devices for tenant {tenant_id}")
        
        return all_device_ids


def normalize_dates_to_utc(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """
    Normalize dates to UTC with day-boundary alignment.
    - Floor start to 00:00:00 UTC
    - Ceil end to 23:59:59.999999 UTC
    Returns tuple of (start_datetime, end_datetime)
    """
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    return start_dt, end_dt


def validate_date_duration_seconds(start_dt: datetime, end_dt: datetime, min_seconds: int = 86400) -> bool:
    """
    Validate duration using seconds instead of days to avoid timezone drift.
    min_seconds defaults to 86400 (24 hours).
    """
    duration_seconds = (end_dt - start_dt).total_seconds()
    return duration_seconds >= min_seconds


async def validate_device_for_reporting(device_id: str) -> dict:
    """
    Validate device exists.
    Returns device data if valid.
    Raises HTTPException if invalid.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.DEVICE_SERVICE_URL}/api/v1/devices/{device_id}"
            )
        except httpx.RequestError as e:
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


@router.post("/consumption", response_model=ReportResponse)
async def create_energy_consumption_report(
    request: ConsumptionReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("ENERGY REPORT REQUEST RECEIVED")
    logger.info(f"  start_date: {request.start_date}")
    logger.info(f"  end_date: {request.end_date}")
    logger.info(f"  device_ids: {request.device_ids}")
    logger.info(f"  tenant_id: {request.tenant_id}")
    logger.info("="*60)
    
    device_ids = list(request.device_ids)
    
    if "all" in device_ids:
        logger.info("Received 'all' device selection, resolving to actual device IDs")
        resolved_ids = await resolve_all_devices(request.tenant_id)
        
        if not resolved_ids:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "NO_VALID_DEVICES",
                    "message": "No energy-capable devices found for this tenant."
                }
            )
        
        device_ids = resolved_ids
        logger.info(f"Resolved device IDs: {device_ids}")
    
    start_dt, end_dt = normalize_dates_to_utc(request.start_date, request.end_date)
    duration_seconds = (end_dt - start_dt).total_seconds()
    
    logger.info("="*60)
    logger.info("DATE NORMALIZATION RESULTS")
    logger.info(f"  Original start: {request.start_date}")
    logger.info(f"  Original end: {request.end_date}")
    logger.info(f"  UTC start_dt: {start_dt}")
    logger.info(f"  UTC end_dt: {end_dt}")
    logger.info(f"  Duration seconds: {duration_seconds}")
    logger.info(f"  Duration days: {duration_seconds / 86400}")
    logger.info("="*60)
    
    if not validate_date_duration_seconds(start_dt, end_dt):
        logger.error(f"Date validation FAILED: duration {duration_seconds} seconds < 86400")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_DATE_RANGE",
                "message": f"Date range must be at least 24 hours apart. Current: {duration_seconds/86400:.1f} days"
            }
        )
    
    for device_id in device_ids:
        await validate_device_for_reporting(device_id)
    
    repo = ReportRepository(db)
    
    report_id = str(uuid4())
    
    params = request.model_dump()
    params["start_date"] = str(params["start_date"])
    params["end_date"] = str(params["end_date"])
    params["device_ids"] = device_ids
    
    await repo.create_report(
        report_id=report_id,
        tenant_id=request.tenant_id,
        report_type="consumption",
        params=params
    )

    task_params = {
        "tenant_id": request.tenant_id,
        "device_ids": device_ids,
        "start_date": str(request.start_date),
        "end_date": str(request.end_date),
        "group_by": request.group_by,
    }
    background_tasks.add_task(run_consumption_report, report_id, task_params)
    
    return ReportResponse(
        report_id=report_id,
        status="pending",
        created_at=datetime.utcnow().isoformat()
    )
