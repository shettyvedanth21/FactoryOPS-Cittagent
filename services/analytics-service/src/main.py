"""Analytics Service entry point."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from src.api.routes import analytics, health
from src.config.logging_config import configure_logging
from src.config.settings import Settings, get_settings
from src.infrastructure.database import init_db
from src.workers.job_queue import JobQueue
from src.workers.job_worker import JobWorker

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    settings = get_settings()
    
    configure_logging(settings.log_level)
    logger.info("analytics_service_starting", version="1.0.0")
    
    await init_db()
    
    job_queue = JobQueue()
    job_worker = JobWorker(job_queue)
    
    worker_task = asyncio.create_task(job_worker.start())
    app.state.job_queue = job_queue
    app.state.job_worker = job_worker
    
    logger.info("analytics_service_ready")
    
    yield
    
    logger.info("analytics_service_shutting_down")
    await job_worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("analytics_service_stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Analytics Service",
        description="ML Analytics Service for Energy Intelligence Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    
    return app


app = create_app()
