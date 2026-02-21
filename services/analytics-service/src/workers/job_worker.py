"""Job worker for processing analytics jobs."""

import asyncio
import re
from datetime import datetime
from typing import Optional, Any
import structlog

from src.infrastructure.database import async_session_maker
from src.infrastructure.mysql_repository import MySQLResultRepository
from src.infrastructure.s3_client import S3Client
from src.services.dataset_service import DatasetService
from src.services.job_runner import JobRunner
from src.utils.exceptions import AnalyticsError, DatasetNotFoundError
from src.workers.job_queue import JobQueue

logger = structlog.get_logger()


class JobWorker:
    """Worker that processes analytics jobs from the queue."""

    def __init__(
        self,
        job_queue: JobQueue,
        max_concurrent: int = 3,
    ):
        self._queue = job_queue
        self._max_concurrent = max_concurrent
        self._running = False
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._logger = logger.bind(worker="JobWorker")
        self._current_tasks: set = set()

    async def start(self) -> None:
        """Start the job worker."""
        self._running = True
        self._semaphore = asyncio.Semaphore(self._max_concurrent)

        self._logger.info(
            "worker_started",
            max_concurrent=self._max_concurrent,
        )

        while self._running:
            try:
                job = await self._queue.get_job()
                if job is None:
                    break

                task = asyncio.create_task(
                    self._process_job_with_semaphore(job)
                )
                self._current_tasks.add(task)
                task.add_done_callback(self._current_tasks.discard)

            except asyncio.CancelledError:
                self._logger.info("worker_cancelled")
                break
            except Exception as e:
                self._logger.error("worker_error", error=str(e))
                await asyncio.sleep(1)

    async def _process_job_with_semaphore(self, job: Any) -> None:
        if self._semaphore:
            async with self._semaphore:
                await self._process_job(job)

    # ---------------------------------------------------------
    # NEW: extract dates from dataset key
    # ---------------------------------------------------------
    def _extract_dates_from_dataset_key(self, dataset_key: str):
        """
        Expected:
          datasets/D1/20260210_20260210.parquet
        """

        m = re.search(r"(\d{8})_(\d{8})", dataset_key)
        if not m:
            raise AnalyticsError(
                f"Invalid dataset key format: {dataset_key}"
            )

        start = datetime.strptime(m.group(1), "%Y%m%d")
        end = datetime.strptime(m.group(2), "%Y%m%d")

        return start, end

    async def _process_job(self, job: Any) -> None:
        job_id = job.job_id
        request = job.request

        self._logger.info(
            "processing_job",
            job_id=job_id,
            analysis_type=request.analysis_type.value,
        )

        async with async_session_maker() as session:
            try:
                result_repo = MySQLResultRepository(session)

                # ---------------------------------------------------------
                # PERMANENT FIX:
                # Fill date_range_* when dataset_key is used
                # ---------------------------------------------------------
                if request.dataset_key:
                    date_range_start, date_range_end = (
                        self._extract_dates_from_dataset_key(
                            request.dataset_key
                        )
                    )
                else:
                    date_range_start = request.start_time
                    date_range_end = request.end_time

                await result_repo.create_job(
                    job_id=job_id,
                    device_id=request.device_id,
                    analysis_type=request.analysis_type.value,
                    model_name=request.model_name,
                    date_range_start=date_range_start,
                    date_range_end=date_range_end,
                    parameters=request.parameters,
                )

                s3_client = S3Client()
                dataset_service = DatasetService(s3_client)

                runner = JobRunner(dataset_service, result_repo)
                await runner.run_job(job_id, request)

                self._logger.info("job_completed", job_id=job_id)

            except DatasetNotFoundError as e:
                self._logger.error(
                    "job_failed_dataset_not_found",
                    job_id=job_id,
                    error=str(e),
                )
                await self._mark_job_failed(job_id, str(e))

            except AnalyticsError as e:
                self._logger.error(
                    "job_failed_analytics_error",
                    job_id=job_id,
                    error=str(e),
                )
                await self._mark_job_failed(job_id, str(e))

            except Exception as e:
                self._logger.error(
                    "job_failed_unexpected",
                    job_id=job_id,
                    error=str(e),
                    exc_info=True,
                )
                await self._mark_job_failed(job_id, f"Unexpected error: {e}")

            finally:
                self._queue.task_done()

    async def _mark_job_failed(self, job_id: str, error_message: str) -> None:
        try:
            async with async_session_maker() as session:
                result_repo = MySQLResultRepository(session)
                from src.models.schemas import JobStatus

                await result_repo.update_job_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    completed_at=datetime.utcnow(),
                    error_message=error_message,
                )
        except Exception as e:
            self._logger.error(
                "failed_to_mark_job_failed",
                job_id=job_id,
                error=str(e),
            )

    async def stop(self) -> None:
        self._logger.info("stopping_worker")
        self._running = False

        if self._current_tasks:
            self._logger.info(
                "waiting_for_tasks",
                task_count=len(self._current_tasks),
            )
            await asyncio.gather(*self._current_tasks, return_exceptions=True)

        self._logger.info("worker_stopped")