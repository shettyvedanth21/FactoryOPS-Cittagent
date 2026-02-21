"""API endpoints for alert management."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.rule import AlertRepository
from app.schemas.rule import AlertResponse, ErrorResponse

router = APIRouter()


class AlertListResponse(BaseModel):
    """Schema for paginated alert list response."""

    success: bool = True
    data: List[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AlertSingleResponse(BaseModel):
    success: bool = True
    data: AlertResponse


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: Optional[str] = None


# ---------------------------------------------------------------------
# List alerts
# ---------------------------------------------------------------------
@router.get(
    "",
    response_model=AlertListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_alerts(
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    rule_id: Optional[UUID] = Query(None, description="Filter by rule ID"),
    status: Optional[str] = Query(None, description="Filter by alert status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """List all alerts with optional filtering and pagination."""

    repository = AlertRepository(db)

    alerts, total = await repository.list_alerts(
        tenant_id=tenant_id,
        device_id=device_id,
        rule_id=rule_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return AlertListResponse(
        data=alerts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------
# Acknowledge alert
# ---------------------------------------------------------------------
@router.patch(
    "/{alert_id}/acknowledge",
    response_model=AlertSingleResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Alert not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def acknowledge_alert(
    alert_id: UUID,
    payload: AlertAcknowledgeRequest,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> AlertSingleResponse:
    """
    Acknowledge an alert.
    """

    repository = AlertRepository(db)

    # Reuse existing repository lookup logic
    alert = await repository.get_by_id(
        alert_id=alert_id,
        tenant_id=tenant_id,
    )

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "ALERT_NOT_FOUND",
                    "message": f"Alert with ID '{alert_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    alert = await repository.acknowledge_alert(
        alert_id=alert_id,
        acknowledged_by=payload.acknowledged_by,
    )

    return AlertSingleResponse(data=alert)


# ---------------------------------------------------------------------
# Resolve alert
# ---------------------------------------------------------------------
@router.patch(
    "/{alert_id}/resolve",
    response_model=AlertSingleResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Alert not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def resolve_alert(
    alert_id: UUID,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> AlertSingleResponse:
    """
    Mark an alert as resolved.
    """

    repository = AlertRepository(db)

    alert = await repository.get_by_id(
        alert_id=alert_id,
        tenant_id=tenant_id,
    )

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "ALERT_NOT_FOUND",
                    "message": f"Alert with ID '{alert_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    alert = await repository.resolve_alert(
        alert_id=alert_id,
    )

    return AlertSingleResponse(data=alert)