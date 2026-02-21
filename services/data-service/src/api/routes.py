"""API routes for REST endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import BaseModel, Field

from src.config import settings
from src.models import TelemetryPoint, TelemetryQuery
from src.services import TelemetryService
from src.utils import get_logger

logger = get_logger(__name__)


# -------------------------
# Dependency (PERMANENT FIX)
# -------------------------

def get_telemetry_service() -> TelemetryService:
    from src.main import app_state

    if app_state.telemetry_service is None:
        raise RuntimeError("TelemetryService not initialized")

    return app_state.telemetry_service


# -------------------------
# Response models
# -------------------------

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: str


class TelemetryListResponse(BaseModel):
    items: List[TelemetryPoint]
    total: int
    page: int = 1
    page_size: int = 1000


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    checks: Dict[str, Any] = Field(default_factory=dict)


# -------------------------
# Router factory
# -------------------------

def create_router() -> APIRouter:
    router = APIRouter(prefix=settings.api_prefix)

    # -------------------------
    # Health
    # -------------------------

    @router.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
    )
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            timestamp=datetime.utcnow().isoformat(),
            checks={
                "influxdb": "connected",
                "mqtt": "connected",
            },
        )

    # -------------------------
    # Telemetry
    # -------------------------

    @router.get(
        "/telemetry/{device_id}",
        response_model=ApiResponse,
        tags=["Telemetry"],
    )
    async def get_telemetry(
        device_id: str,
        start_time: Optional[datetime] = Query(None),
        end_time: Optional[datetime] = Query(None),
        fields: Optional[str] = Query(None),
        aggregate: Optional[str] = Query(None),
        interval: Optional[str] = Query(None),
        limit: int = Query(default=1000, ge=1, le=10000),
        telemetry_service: TelemetryService = Depends(get_telemetry_service),
    ) -> ApiResponse:
        try:
            field_list = fields.split(",") if fields else None

            points = await telemetry_service.get_telemetry(
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                fields=field_list,
                aggregate=aggregate,
                interval=interval,
                limit=limit,
            )

            return ApiResponse(
                success=True,
                data={
                    "items": [p.model_dump() for p in points],
                    "total": len(points),
                    "device_id": device_id,
                },
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            logger.exception("Failed to get telemetry", extra={"device_id": device_id})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": {
                        "code": "QUERY_ERROR",
                        "message": str(e),
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    # -------------------------
    # Stats
    # -------------------------

    @router.get(
        "/stats/{device_id}",
        response_model=ApiResponse,
        tags=["Telemetry"],
    )
    async def get_stats(
        device_id: str,
        start_time: Optional[datetime] = Query(None),
        end_time: Optional[datetime] = Query(None),
        telemetry_service: TelemetryService = Depends(get_telemetry_service),
    ) -> ApiResponse:
        try:
            stats = await telemetry_service.get_stats(
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
            )

            if stats is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "success": False,
                        "error": {
                            "code": "NO_DATA",
                            "message": f"No data found for device {device_id}",
                        },
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            return ApiResponse(
                success=True,
                data=stats if isinstance(stats, dict) else stats.model_dump(),
                timestamp=datetime.utcnow().isoformat(),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to get stats", extra={"device_id": device_id})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": {
                        "code": "STATS_ERROR",
                        "message": str(e),
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    # -------------------------
    # Custom query
    # -------------------------

    @router.post(
        "/query",
        response_model=ApiResponse,
        tags=["Telemetry"],
    )
    async def custom_query(
        query: TelemetryQuery,
        telemetry_service: TelemetryService = Depends(get_telemetry_service),
    ) -> ApiResponse:
        try:
            points = await telemetry_service.get_telemetry(
                device_id=query.device_id,
                start_time=query.start_time,
                end_time=query.end_time,
                fields=query.fields,
                aggregate=query.aggregate,
                interval=query.interval,
                limit=query.limit,
            )

            return ApiResponse(
                success=True,
                data={
                    "items": [p.model_dump() for p in points],
                    "total": len(points),
                },
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            logger.exception("Custom query failed", extra={"device_id": query.device_id})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": {
                        "code": "QUERY_ERROR",
                        "message": str(e),
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    return router