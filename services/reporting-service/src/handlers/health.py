"""Health check handler."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from src.models.report import HealthResponse
from src.repositories.analytics_repository import AnalyticsRepository
from src.utils.logging_config import get_logger
from src.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Global repository instance for health checks
_analytics_repo: AnalyticsRepository = None


def set_analytics_repository(repo: AnalyticsRepository) -> None:
    """Set the analytics repository for health checks."""
    global _analytics_repo
    _analytics_repo = repo


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.
    
    Returns:
        HealthResponse with service status and component checks
    """
    checks = {}
    
    # Check database connectivity
    if _analytics_repo:
        checks["database"] = await _analytics_repo.health_check()
    else:
        checks["database"] = False
    
    # Overall health
    is_healthy = all(checks.values())
    
    if not is_healthy:
        logger.warning("Health check failed", checks=checks)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "service": settings.service_name,
                "checks": checks
            }
        )
    
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.utcnow(),
        checks=checks
    )


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes.
    
    Returns:
        200 if service is ready to accept traffic
    """
    if _analytics_repo and await _analytics_repo.health_check():
        return {"status": "ready"}
    
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"status": "not ready"}
    )