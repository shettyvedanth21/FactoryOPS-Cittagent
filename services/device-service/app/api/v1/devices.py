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
    ShiftCreate,
    ShiftUpdate,
    ShiftResponse,
    ShiftListResponse,
    ShiftSingleResponse,
    ShiftDeleteResponse,
    UptimeResponse,
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


# =====================================================
# Shift Configuration Endpoints
# =====================================================

@router.post(
    "/{device_id}/shifts",
    response_model=ShiftSingleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Device not found"},
    },
)
async def create_shift(
    device_id: str,
    shift_data: ShiftCreate,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> ShiftSingleResponse:
    """Create a new shift for a device."""
    from app.services.shift import ShiftService
    
    shift_dict = shift_data.model_dump()
    shift_dict["device_id"] = device_id
    shift_dict["tenant_id"] = tenant_id
    
    shift_create = ShiftCreate(**shift_dict)
    
    service = ShiftService(db)
    shift = await service.create_shift(shift_create)
    
    return ShiftSingleResponse(data=shift)


@router.get(
    "/{device_id}/shifts",
    response_model=ShiftListResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Device not found"},
    },
)
async def list_shifts(
    device_id: str,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> ShiftListResponse:
    """List all shifts for a device."""
    from app.services.shift import ShiftService
    
    service = ShiftService(db)
    shifts = await service.get_shifts_by_device(device_id, tenant_id)
    
    return ShiftListResponse(data=shifts, total=len(shifts))


@router.get(
    "/{device_id}/shifts/{shift_id}",
    response_model=ShiftSingleResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Shift not found"},
    },
)
async def get_shift(
    device_id: str,
    shift_id: int,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> ShiftSingleResponse:
    """Get a specific shift by ID."""
    from app.services.shift import ShiftService
    
    service = ShiftService(db)
    shift = await service.get_shift(shift_id, device_id, tenant_id)
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "SHIFT_NOT_FOUND",
                    "message": f"Shift with ID '{shift_id}' not found for device '{device_id}'",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return ShiftSingleResponse(data=shift)


@router.put(
    "/{device_id}/shifts/{shift_id}",
    response_model=ShiftSingleResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Shift not found"},
    },
)
async def update_shift(
    device_id: str,
    shift_id: int,
    shift_data: ShiftUpdate,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> ShiftSingleResponse:
    """Update an existing shift."""
    from app.services.shift import ShiftService
    
    service = ShiftService(db)
    shift = await service.update_shift(shift_id, device_id, tenant_id, shift_data)
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "SHIFT_NOT_FOUND",
                    "message": f"Shift with ID '{shift_id}' not found for device '{device_id}'",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return ShiftSingleResponse(data=shift)


@router.delete(
    "/{device_id}/shifts/{shift_id}",
    response_model=ShiftDeleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Shift not found"},
    },
)
async def delete_shift(
    device_id: str,
    shift_id: int,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> ShiftDeleteResponse:
    """Delete a shift."""
    from app.services.shift import ShiftService
    
    service = ShiftService(db)
    success = await service.delete_shift(shift_id, device_id, tenant_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "SHIFT_NOT_FOUND",
                    "message": f"Shift with ID '{shift_id}' not found for device '{device_id}'",
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    
    return ShiftDeleteResponse(
        success=True,
        message=f"Shift {shift_id} deleted successfully",
        shift_id=shift_id
    )


@router.get(
    "/{device_id}/uptime",
    response_model=UptimeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Device not found"},
    },
)
async def get_uptime(
    device_id: str,
    tenant_id: Optional[str] = Query(None, description="Tenant ID for multi-tenancy"),
    db: AsyncSession = Depends(get_db),
) -> UptimeResponse:
    """Calculate uptime for a device based on configured shifts."""
    from app.services.shift import ShiftService
    
    service = ShiftService(db)
    uptime = await service.calculate_uptime(device_id, tenant_id)
    
    return UptimeResponse(**uptime)
