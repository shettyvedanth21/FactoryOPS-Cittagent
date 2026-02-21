"""API dependencies."""

from typing import AsyncGenerator

import structlog
from fastapi import Request

from src.infrastructure.database import get_db_session
from src.infrastructure.mysql_repository import MySQLResultRepository
from src.services.result_repository import ResultRepository
from src.workers.job_queue import JobQueue

logger = structlog.get_logger()


async def get_job_queue(request: Request) -> JobQueue:
    """Get job queue from app state."""
    return request.app.state.job_queue


async def get_result_repository() -> AsyncGenerator[ResultRepository, None]:
    """Get result repository instance."""
    session = await get_db_session()
    try:
        yield MySQLResultRepository(session)
    finally:
        await session.close()
