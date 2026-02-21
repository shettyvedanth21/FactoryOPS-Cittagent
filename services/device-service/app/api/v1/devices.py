"""Device API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
    DeviceSingleResponse,
    ErrorResponse,
)
from app.services.device import DeviceService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{device_id}",
    response_model=DeviceSingleResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Device not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_device(
    device_id: str,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> DeviceSingleResponse:
    """Get a device by ID.
    
    - **device_id**: Unique device identifier
    - **tenant_id**: Optional tenant ID for multi-tenant filtering
    """
    service = DeviceService(db)
    device = await service.get_device(device_id, tenant_id)
    
    if not device:
        logger.warning("Device not found", extra={"device_id": device_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return DeviceSingleResponse(data=device)


@router.get(
    "",
    response_model=DeviceListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_devices(
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by device status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> DeviceListResponse:
    """List all devices with optional filtering and pagination.
    
    - **tenant_id**: Optional tenant ID for multi-tenant filtering
    - **device_type**: Filter by device type (e.g., 'bulb', 'compressor')
    - **status**: Filter by status ('active', 'inactive', 'maintenance', 'error')
    - **page**: Page number (1-based)
    - **page_size**: Number of items per page (max 100)
    """
    service = DeviceService(db)
    devices, total = await service.list_devices(
        tenant_id=tenant_id,
        device_type=device_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return DeviceListResponse(
        data=devices,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=DeviceSingleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Device already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
) -> DeviceSingleResponse:
    """Create a new device.
    
    - **device_id**: Unique identifier (required)
    - **device_name**: Human-readable name (required)
    - **device_type**: Device category (required)
    - **manufacturer**: Device manufacturer (optional)
    - **model**: Device model (optional)
    - **location**: Physical location (optional)
    - **status**: Device status (default: 'active')
    """
    service = DeviceService(db)
    
    try:
        device = await service.create_device(device_data)
        return DeviceSingleResponse(data=device)
    except ValueError as e:
        logger.warning(
            "Device creation failed",
            extra={
                "device_id": device_data.device_id,
                "error": str(e),
            }
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "error": {
                    "code": "DEVICE_ALREADY_EXISTS",
                    "message": str(e),
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@router.put(
    "/{device_id}",
    response_model=DeviceSingleResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Device not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> DeviceSingleResponse:
    """Update an existing device.
    
    Only provided fields will be updated. All fields are optional.
    
    - **device_id**: Device identifier in path
    - **device_name**: Updated name (optional)
    - **device_type**: Updated type (optional)
    - **manufacturer**: Updated manufacturer (optional)
    - **model**: Updated model (optional)
    - **location**: Updated location (optional)
    - **status**: Updated status (optional)
    """
    service = DeviceService(db)
    device = await service.update_device(device_id, device_data, tenant_id)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return DeviceSingleResponse(data=device)


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Device not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_device(
    device_id: str,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    soft: bool = Query(True, description="Perform soft delete"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a device.
    
    - **device_id**: Device identifier
    - **tenant_id**: Optional tenant ID
    - **soft**: If True, marks device as deleted; if False, permanently removes
    """
    service = DeviceService(db)
    deleted = await service.delete_device(device_id, tenant_id, soft=soft)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return None
