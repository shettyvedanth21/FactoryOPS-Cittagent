from typing import Optional
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import ReportStatus
from src.repositories.report_repository import ReportRepository
from src.repositories.scheduled_repository import ScheduledRepository
from src.storage.minio_client import minio_client, StorageError

router = APIRouter(tags=["reports"])


@router.get("/history")
async def list_reports(
    tenant_id: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    report_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    reports = await repo.list_reports(tenant_id, limit, offset, report_type)
    
    return {
        "reports": [
            {
                "report_id": r.report_id,
                "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
                "report_type": r.report_type.value if hasattr(r.report_type, 'value') else str(r.report_type),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None
            }
            for r in reports
        ]
    }


@router.post("/schedules")
async def create_schedule(
    data: dict,
    tenant_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    data["tenant_id"] = tenant_id
    repo = ScheduledRepository(db)
    schedule = await repo.create_schedule(data)
    
    return {
        "schedule_id": schedule.schedule_id,
        "tenant_id": schedule.tenant_id,
        "report_type": schedule.report_type.value if hasattr(schedule.report_type, 'value') else str(schedule.report_type),
        "frequency": schedule.frequency.value if hasattr(schedule.frequency, 'value') else str(schedule.frequency),
        "is_active": schedule.is_active,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "created_at": schedule.created_at.isoformat()
    }


@router.get("/schedules")
async def list_schedules(
    tenant_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    repo = ScheduledRepository(db)
    schedules = await repo.list_schedules(tenant_id)
    
    return {
        "schedules": [
            {
                "schedule_id": s.schedule_id,
                "tenant_id": s.tenant_id,
                "report_type": s.report_type.value if hasattr(s.report_type, 'value') else str(s.report_type),
                "frequency": s.frequency.value if hasattr(s.frequency, 'value') else str(s.frequency),
                "is_active": s.is_active,
                "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
                "last_status": s.last_status,
                "last_result_url": s.last_result_url,
                "params_template": s.params_template
            }
            for s in schedules
        ]
    }


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    tenant_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    repo = ScheduledRepository(db)
    schedule = await repo.get_schedule(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if schedule.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await repo.update_schedule(schedule_id, is_active=False)
    
    return {"message": "Schedule deactivated"}


@router.get("/{report_id}/status")
async def get_report_status(
    report_id: str,
    tenant_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    report = await repo.get_report(report_id, tenant_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "report_id": report.report_id,
        "status": report.status.value if hasattr(report.status, 'value') else str(report.status),
        "progress": getattr(report, 'progress', 0),
        "error_code": report.error_code,
        "error_message": report.error_message
    }


@router.get("/{report_id}/result")
async def get_report_result(
    report_id: str,
    tenant_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    report = await repo.get_report(report_id, tenant_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != ReportStatus.completed:
        raise HTTPException(status_code=404, detail="Report not completed yet")
    
    return report.result_json


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    tenant_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    report = await repo.get_report(report_id, tenant_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not report.s3_key:
        raise HTTPException(status_code=404, detail="PDF not available")
    
    try:
        pdf_bytes = minio_client.download_pdf(report.s3_key)
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=energy_report_{report_id}.pdf",
                "Content-Length": str(len(pdf_bytes))
            }
        )
    except StorageError as e:
        raise HTTPException(status_code=404, detail=str(e))
