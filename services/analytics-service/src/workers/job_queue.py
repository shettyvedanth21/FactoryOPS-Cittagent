"""Job queue for managing analytics jobs."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

import structlog

from src.models.schemas import AnalyticsRequest

logger = structlog.get_logger()


@dataclass
class Job:
    """Job container."""
    job_id: str
    request: AnalyticsRequest


class JobQueue:
    """Queue for managing pending analytics jobs."""
    
    def __init__(self, maxsize: int = 100):
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=maxsize)
        self._logger = logger.bind(worker="JobQueue")
    
    async def submit_job(self, job_id: str, request: AnalyticsRequest) -> None:
        """Submit a job to the queue."""
        job = Job(job_id=job_id, request=request)
        await self._queue.put(job)
        self._logger.info("job_queued", job_id=job_id)
    
    async def get_job(self) -> Optional[Job]:
        """Get next job from queue."""
        try:
            job = await self._queue.get()
            self._logger.debug("job_dequeued", job_id=job.job_id)
            return job
        except asyncio.CancelledError:
            return None
    
    def task_done(self) -> None:
        """Mark current task as done."""
        self._queue.task_done()
    
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
