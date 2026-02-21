"""Reports API handler."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, status

from src.models.report import (
    GenerateReportRequest,
    ReportJobResponse,
    ReportStatusResponse,
    ReportDownloadResponse,
    ReportStatus,
    ReportFormat
)
from src.services.report_builder import ReportBuilder
from src.utils.exceptions import ReportGenerationError, ReportNotFoundError
from src.utils.logging_config import get_logger
from src.config import settings

logger = get_logger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])

# Global report builder instance
_report_builder: Optional[ReportBuilder] = None


def set_report_builder(builder: ReportBuilder) -> None:
    """Set the report builder instance."""
    global _report_builder
    _report_builder = builder


@router.post("/generate", response_model=ReportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks
):
    """Generate a new report.
    
    Accepts report generation parameters and queues the job for async processing.
    
    Args:
        request: Report generation parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        ReportJobResponse with job ID and status
        
    Raises:
        HTTPException: If report builder is not initialized
    """
    if not _report_builder:
        logger.error("Report builder not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not fully initialized"
        )
    
    # Validate time range
    if request.end_time <= request.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be after start_time"
        )
    
    # Create job
    job = await _report_builder.create_job(request)
    
    # Queue background task
    background_tasks.add_task(_report_builder.generate_report, job.job_id)
    
    logger.info(
        "Report generation queued",
        job_id=job.job_id,
        device_count=len(request.device_ids),
        format=request.format.value
    )
    
    return ReportJobResponse(
        job_id=job.job_id,
        status=job.status,
        message="Report generation queued",
        created_at=job.created_at,
        estimated_completion=datetime.utcnow() + timedelta(minutes=2)
    )


@router.get("/status/{job_id}", response_model=ReportStatusResponse)
async def get_report_status(job_id: str):
    """Get the status of a report generation job.
    
    Args:
        job_id: Report job identifier
        
    Returns:
        ReportStatusResponse with current status and progress
        
    Raises:
        HTTPException: If job not found
    """
    if not _report_builder:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not fully initialized"
        )
    
    job = await _report_builder.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report job not found: {job_id}"
        )
    
    return ReportStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress_percent=job.progress_percent,
        message=job.message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message
    )


@router.get("/download/{job_id}", response_model=ReportDownloadResponse)
async def download_report(job_id: str):
    """Get download URL for a completed report.
    
    Args:
        job_id: Report job identifier
        
    Returns:
        ReportDownloadResponse with presigned download URL
        
    Raises:
        HTTPException: If job not found or not completed
    """
    if not _report_builder:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not fully initialized"
        )
    
    job = await _report_builder.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report job not found: {job_id}"
        )
    
    if job.status != ReportStatus.COMPLETED:
        return ReportDownloadResponse(
            job_id=job_id,
            status=job.status,
            format=job.request.format,
            file_size_bytes=None,
            download_url=None,
            expires_at=None
        )
    
    # Generate presigned URL
    download_url = await _report_builder.get_download_url(job_id)
    
    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )
    
    return ReportDownloadResponse(
        job_id=job_id,
        status=job.status,
        format=job.request.format,
        file_size_bytes=job.file_size_bytes,
        download_url=download_url,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )