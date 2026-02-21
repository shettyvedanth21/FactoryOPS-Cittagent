"""API endpoints for rule management."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.rule import (
    RuleCreate,
    RuleUpdate,
    RuleStatusUpdate,
    RuleResponse,
    RuleListResponse,
    RuleSingleResponse,
    RuleStatusResponse,
    RuleDeleteResponse,
    ErrorResponse,
    RuleStatus,
    TelemetryPayload,   # ✅ CHANGED (was TelemetryIn)
)
from app.services.rule import RuleService
from app.services.evaluator import RuleEvaluator
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{rule_id}",
    response_model=RuleSingleResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Rule not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_rule(
    rule_id: UUID,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> RuleSingleResponse:
    """Get a rule by ID.
    
    - **rule_id**: Unique rule identifier (UUID)
    - **tenant_id**: Optional tenant ID for multi-tenant filtering
    """
    service = RuleService(db)
    rule = await service.get_rule(rule_id, tenant_id)
    
    if not rule:
        logger.warning("Rule not found", extra={"rule_id": str(rule_id)})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "RULE_NOT_FOUND",
                    "message": f"Rule with ID '{rule_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return RuleSingleResponse(data=rule)


@router.get(
    "",
    response_model=RuleListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_rules(
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    status: Optional[RuleStatus] = Query(None, description="Filter by rule status"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> RuleListResponse:
    """List all rules with optional filtering and pagination."""
    service = RuleService(db)
    rules, total = await service.list_rules(
        tenant_id=tenant_id,
        status=status,
        device_id=device_id,
        page=page,
        page_size=page_size,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return RuleListResponse(
        data=rules,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=RuleSingleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_rule(
    rule_data: RuleCreate,
    db: AsyncSession = Depends(get_db),
) -> RuleSingleResponse:
    """Create a new rule."""
    service = RuleService(db)
    
    try:
        rule = await service.create_rule(rule_data)
        return RuleSingleResponse(data=rule)
    except ValueError as e:
        logger.warning(
            "Rule creation failed",
            extra={
                "rule_name": rule_data.rule_name,
                "error": str(e),
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e),
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@router.put(
    "/{rule_id}",
    response_model=RuleSingleResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Rule not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_rule(
    rule_id: UUID,
    rule_data: RuleUpdate,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> RuleSingleResponse:
    """Update an existing rule."""
    service = RuleService(db)
    
    try:
        rule = await service.update_rule(rule_id, rule_data, tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e),
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "RULE_NOT_FOUND",
                    "message": f"Rule with ID '{rule_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return RuleSingleResponse(data=rule)


@router.patch(
    "/{rule_id}/status",
    response_model=RuleStatusResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Rule not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_rule_status(
    rule_id: UUID,
    status_update: RuleStatusUpdate,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> RuleStatusResponse:
    """Update rule status."""
    service = RuleService(db)
    rule = await service.update_rule_status(rule_id, status_update.status, tenant_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "RULE_NOT_FOUND",
                    "message": f"Rule with ID '{rule_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    status_messages = {
        RuleStatus.ACTIVE: "Rule activated successfully",
        RuleStatus.PAUSED: "Rule paused successfully",
        RuleStatus.ARCHIVED: "Rule archived successfully",
    }
    
    return RuleStatusResponse(
        message=status_messages.get(status_update.status, "Status updated"),
        rule_id=rule_id,
        status=status_update.status,
    )


@router.delete(
    "/{rule_id}",
    response_model=RuleDeleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Rule not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_rule(
    rule_id: UUID,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    soft: bool = Query(True, description="Perform soft delete"),
    db: AsyncSession = Depends(get_db),
) -> RuleDeleteResponse:
    """Delete a rule."""
    service = RuleService(db)
    deleted = await service.delete_rule(rule_id, tenant_id, soft=soft)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "RULE_NOT_FOUND",
                    "message": f"Rule with ID '{rule_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return RuleDeleteResponse(
        message="Rule deleted successfully" if soft else "Rule permanently deleted",
        rule_id=rule_id,
    )


# ----------------------------------------------------------------------
# ✅ FIXED evaluate endpoint (streaming / data-service entrypoint)
# ----------------------------------------------------------------------

@router.post(
    "/evaluate",
    status_code=200,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def evaluate_rules(
    payload: TelemetryPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluate full telemetry payload against active rules.

    This endpoint is used by the data-service and expects a complete
    telemetry payload (voltage, current, power, temperature, etc).
    """
    evaluator = RuleEvaluator(db)

    try:
        total, triggered, results = await evaluator.evaluate_telemetry(payload)

        logger.info(
            "Rule evaluation completed",
            extra={
                "device_id": payload.device_id,
                "rules_evaluated": total,
                "rules_triggered": triggered,
            },
        )

        return {
            "rules_evaluated": total,
            "rules_triggered": triggered,
            "results": results,
        }

    except ValueError as e:
        logger.warning(
            "Evaluation failed",
            extra={
                "device_id": payload.device_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "EVALUATION_ERROR",
                    "message": str(e),
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(
            "Unexpected error during rule evaluation",
            extra={
                "device_id": payload.device_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred during evaluation",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )