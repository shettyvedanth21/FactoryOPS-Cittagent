from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.requests import ComparisonReportRequest
from src.schemas.responses import ReportResponse
from src.repositories.report_repository import ReportRepository

router = APIRouter(tags=["comparison-reports"])


@router.post("/", response_model=ReportResponse)
async def create_comparison_report(
    request: ComparisonReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    repo = ReportRepository(db)
    
    report_id = str(uuid4())
    
    await repo.create_report(
        report_id=report_id,
        tenant_id=request.tenant_id,
        report_type="comparison",
        params=request.model_dump()
    )
    
    return ReportResponse(
        report_id=report_id,
        status="pending",
        created_at=datetime.utcnow().isoformat()
    )
