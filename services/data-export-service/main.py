
"""Data Export Service - Main FastAPI Application.

Provides minimal health/readiness endpoints and manages the continuous
export worker lifecycle.
"""

import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel

from config import get_settings
from logging_config import get_logger, setup_logging
from worker import ExportWorker


# Setup structured logging
setup_logging()
logger = get_logger(__name__)

# Global worker instance
_worker: ExportWorker | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class ReadyResponse(BaseModel):
    ready: bool
    checks: dict


# -------------------------------
# NEW – export trigger request
# -------------------------------

class ExportRequest(BaseModel):
    device_id: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker

    settings = get_settings()

    logger.info(
        "Starting Data Export Service",
        extra={
            "version": settings.service_version,
            "environment": settings.environment,
        },
    )

    _worker = ExportWorker(settings)
    await _worker.start()

    logger.info("Export worker started successfully")

    try:
        yield
    finally:
        logger.info("Shutting down Data Export Service...")

        if _worker:
            await _worker.stop()

        logger.info("Data Export Service shutdown complete")


app = FastAPI(
    title="Data Export Service",
    description="Continuous telemetry data export to S3 for analytics",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        version=settings.service_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/ready", response_model=ReadyResponse)
async def readiness_check() -> ReadyResponse:
    checks = {
        "worker_running": _worker is not None and _worker.is_running(),
        "checkpoint_store_connected": await _check_checkpoint_store(),
        "s3_accessible": await _check_s3_access(),
    }

    ready = all(checks.values())

    if not ready:
        raise HTTPException(
            status_code=503,
            detail={"ready": False, "checks": checks},
        )

    return ReadyResponse(ready=True, checks=checks)


# -------------------------------------------------
# NEW – on-demand export trigger
# -------------------------------------------------

@app.post("/api/v1/exports/run")
async def run_export(req: ExportRequest = Body(...)):
    if not _worker or not _worker.is_running():
        raise HTTPException(
            status_code=503,
            detail="Export worker is not running",
        )

    try:
        await _worker.force_export(device_id=req.device_id)

        return {
            "status": "accepted",
            "device_id": req.device_id,
        }

    except Exception as e:
        logger.exception("On-demand export failed")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# -------------------------------------------------
# NEW – export status
# -------------------------------------------------

@app.get("/api/v1/exports/status/{device_id}")
async def get_export_status(device_id: str):
    if not _worker:
        raise HTTPException(
            status_code=503,
            detail="Export worker is not running",
        )

    return await _worker.exporter.get_export_status(device_id)


async def _check_checkpoint_store() -> bool:
    if not _worker:
        return False

    try:
        await _worker.checkpoint_store.health_check()
        return True
    except Exception as e:
        logger.warning(f"Checkpoint store health check failed: {e}")
        return False


async def _check_s3_access() -> bool:
    if not _worker:
        return False

    try:
        await _worker.s3_writer.health_check()
        return True
    except Exception as e:
        logger.warning(f"S3 health check failed: {e}")
        return False


def _signal_handler(sig: int, frame) -> None:
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    sys.exit(0)


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=False,
    )