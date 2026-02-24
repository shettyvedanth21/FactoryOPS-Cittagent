from datetime import datetime
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

VALID_ENERGY_DEVICE_TYPES = ("meter", "power_meter", "energy_meter")


async def validate_device_for_reporting(device_id: str) -> dict:
    """
    Validate device exists and is a power meter type.
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
        
        device_type = device_data.get("device_type", "")
        
        if device_type not in VALID_ENERGY_DEVICE_TYPES:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_DEVICE_TYPE",
                    "message": f"Device '{device_id}' is a '{device_type}' type. "
                              f"Energy reports require a power meter device (types: meter, power_meter, energy_meter). "
                              f"Use device IDs like D2, METER-001 for power meters."
                }
            )
        
        return device_data


@router.post("/consumption", response_model=ReportResponse)
async def create_energy_consumption_report(
    request: ConsumptionReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # Validate each device before creating report
    for device_id in request.device_ids:
        await validate_device_for_reporting(device_id)
    
    repo = ReportRepository(db)
    
    report_id = str(uuid4())
    
    params = request.model_dump()
    params["start_date"] = str(params["start_date"])
    params["end_date"] = str(params["end_date"])
    
    await repo.create_report(
        report_id=report_id,
        tenant_id=request.tenant_id,
        report_type="consumption",
        params=params
    )

    task_params = {
        "tenant_id": request.tenant_id,
        "device_ids": request.device_ids,
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
