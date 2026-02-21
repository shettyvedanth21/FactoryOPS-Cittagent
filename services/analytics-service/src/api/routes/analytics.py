"""Analytics API endpoints."""

from typing import List, Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query

from src.api.dependencies import get_job_queue, get_result_repository
from src.models.schemas import (
    AnalyticsJobResponse,
    AnalyticsRequest,
    AnalyticsResultsResponse,
    AnalyticsType,
    JobStatus,
    JobStatusResponse,
    SupportedModelsResponse,
)
from src.services.result_repository import ResultRepository
from src.utils.exceptions import JobNotFoundError
from src.workers.job_queue import JobQueue

# ✅ NEW imports for dataset listing
from src.infrastructure.s3_client import S3Client
from src.services.dataset_service import DatasetService

logger = structlog.get_logger()

router = APIRouter()


@router.post(
    "/run",
    response_model=AnalyticsJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_analytics(
    request: AnalyticsRequest,
    background_tasks: BackgroundTasks,
    job_queue: JobQueue = Depends(get_job_queue),
) -> AnalyticsJobResponse:
    """
    Submit a new analytics job.

    The job will be queued and processed asynchronously.
    Use the returned job_id to check status and retrieve results.
    """
    job_id = str(uuid4())

    logger.info(
        "analytics_job_submitted",
        job_id=job_id,
        analysis_type=request.analysis_type.value,
        model_name=request.model_name,
        device_id=request.device_id,
    )

    await job_queue.submit_job(
        job_id=job_id,
        request=request,
    )

    return AnalyticsJobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Job queued successfully",
    )


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
)
async def get_job_status(
    job_id: str,
    result_repo: ResultRepository = Depends(get_result_repository),
) -> JobStatusResponse:
    """Get the current status of an analytics job."""
    try:
        job = await result_repo.get_job(job_id)
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus(job.status),
            progress=job.progress,
            message=job.message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )


@router.get(
    "/results/{job_id}",
    response_model=AnalyticsResultsResponse,
)
async def get_analytics_results(
    job_id: str,
    result_repo: ResultRepository = Depends(get_result_repository),
) -> AnalyticsResultsResponse:
    """
    Retrieve results of a completed analytics job.

    Returns model outputs, accuracy metrics, and execution details.
    """
    try:
        job = await result_repo.get_job(job_id)

        if job.status != JobStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} is not completed (current status: {job.status})",
            )

        return AnalyticsResultsResponse(
            job_id=job_id,
            status=JobStatus(job.status),
            device_id=job.device_id,
            analysis_type=AnalyticsType(job.analysis_type),
            model_name=job.model_name,
            date_range_start=job.date_range_start,
            date_range_end=job.date_range_end,
            results=job.results,
            accuracy_metrics=job.accuracy_metrics,
            execution_time_seconds=job.execution_time_seconds,
            completed_at=job.completed_at,
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )


# ------------------------------------------------------------------
# ✅ PERMANENT FIX – advertise only runnable models
# ------------------------------------------------------------------
@router.get(
    "/models",
    response_model=SupportedModelsResponse,
)
async def get_supported_models() -> SupportedModelsResponse:
    """Get list of supported analytics models by type."""

    forecasting_models = ["prophet"]

    # Only expose ARIMA if statsmodels is actually installed
    try:
        import statsmodels  # noqa: F401
        forecasting_models.append("arima")
    except Exception:
        pass

    return SupportedModelsResponse(
        anomaly_detection=[
            "isolation_forest",
            "autoencoder",
        ],
        failure_prediction=[
            "random_forest",
            "gradient_boosting",
        ],
        forecasting=forecasting_models,
    )


@router.get(
    "/jobs",
    response_model=List[JobStatusResponse],
)
async def list_jobs(
    status: Optional[JobStatus] = None,
    device_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    result_repo: ResultRepository = Depends(get_result_repository),
) -> List[JobStatusResponse]:
    """List analytics jobs with optional filtering."""
    jobs = await result_repo.list_jobs(
        status=status.value if status else None,
        device_id=device_id,
        limit=limit,
        offset=offset,
    )

    return [
        JobStatusResponse(
            job_id=job.job_id,
            status=JobStatus(job.status),
            progress=job.progress,
            message=job.message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]


# ------------------------------------------------------------------
# ✅ STEP-1 – Dataset listing endpoint
# ------------------------------------------------------------------

@router.get("/datasets")
async def list_datasets(
    device_id: str = Query(..., description="Device ID"),
):
    """
    List available exported datasets for a device.

    This reads directly from S3/MinIO and returns available dataset objects.
    """

    s3_client = S3Client()
    dataset_service = DatasetService(s3_client)

    datasets = await dataset_service.list_available_datasets(
        device_id=device_id
    )

    return {
        "device_id": device_id,
        "datasets": datasets,
    }