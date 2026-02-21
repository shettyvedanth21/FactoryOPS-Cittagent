"""Health check endpoints."""

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    status: str
    checks: dict


@router.get("/live", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def liveness_probe() -> HealthResponse:
    """Liveness probe for Kubernetes."""
    return HealthResponse(
        status="healthy",
        service="analytics-service",
        version="1.0.0",
    )


@router.get("/ready", response_model=ReadinessResponse, status_code=status.HTTP_200_OK)
async def readiness_probe() -> ReadinessResponse:
    """Readiness probe for Kubernetes."""
    checks = {
        "database": "ok",
        "s3": "ok",
        "worker": "ok",
    }
    
    return ReadinessResponse(
        status="ready",
        checks=checks,
    )
