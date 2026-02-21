"""Pydantic schemas for Device Service API."""

from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class DeviceBase(BaseModel):
    """Base schema with common device fields."""
    
    device_name: str = Field(..., min_length=1, max_length=255, description="Human-readable device name")
    device_type: str = Field(..., min_length=1, max_length=100, description="Device type (e.g., bulb, compressor)")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Device manufacturer")
    model: Optional[str] = Field(None, max_length=255, description="Device model")
    location: Optional[str] = Field(None, max_length=500, description="Physical location of device")
    status: str = Field(default="active", pattern="^(active|inactive|maintenance|error)$")


class DeviceCreate(DeviceBase):
    """Schema for creating a new device."""
    
    device_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Unique device identifier (business key)"
    )
    tenant_id: Optional[str] = Field(None, max_length=50, description="Tenant ID for multi-tenancy")
    metadata_json: Optional[str] = Field(None, description="Additional metadata as JSON string")


class DeviceUpdate(BaseModel):
    """Schema for updating an existing device."""
    
    device_name: Optional[str] = Field(None, min_length=1, max_length=255)
    device_type: Optional[str] = Field(None, min_length=1, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern="^(active|inactive|maintenance|error)$")
    metadata_json: Optional[str] = Field(None, description="Additional metadata as JSON string")


class DeviceResponse(DeviceBase):
    """Schema for device response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    device_id: str
    tenant_id: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class DeviceListResponse(BaseModel):
    """Schema for paginated device list response."""
    
    success: bool = True
    data: list[DeviceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DeviceSingleResponse(BaseModel):
    """Schema for single device response."""
    
    success: bool = True
    data: DeviceResponse


class DeviceDeleteResponse(BaseModel):
    """Schema for device deletion response."""
    
    success: bool = True
    message: str
    device_id: str


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    success: bool = False
    error: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =====================================================
# Shift Configuration Schemas
# =====================================================

class ShiftBase(BaseModel):
    """Base schema for shift configuration."""
    
    shift_name: str = Field(..., min_length=1, max_length=100, description="Shift name (e.g., Morning Shift)")
    shift_start: time = Field(..., description="Shift start time (HH:MM)")
    shift_end: time = Field(..., description="Shift end time (HH:MM)")
    maintenance_break_minutes: int = Field(default=0, ge=0, le=480, description="Maintenance break duration in minutes")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Monday, 6=Sunday). Null means all days.")
    is_active: bool = Field(default=True, description="Whether shift is active")


class ShiftCreate(ShiftBase):
    """Schema for creating a new shift."""
    
    device_id: Optional[str] = Field(None, description="Device ID (set automatically from URL)")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (set automatically from header)")


class ShiftUpdate(BaseModel):
    """Schema for updating an existing shift."""
    
    shift_name: Optional[str] = Field(None, min_length=1, max_length=100)
    shift_start: Optional[time] = None
    shift_end: Optional[time] = None
    maintenance_break_minutes: Optional[int] = Field(None, ge=0, le=480)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    is_active: Optional[bool] = None


class ShiftResponse(ShiftBase):
    """Schema for shift response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    device_id: str
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    @property
    def planned_duration_minutes(self) -> int:
        """Calculate total planned shift duration in minutes."""
        start_minutes = self.shift_start.hour * 60 + self.shift_start.minute
        end_minutes = self.shift_end.hour * 60 + self.shift_end.minute
        
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
            
        return end_minutes - start_minutes
    
    @property
    def effective_runtime_minutes(self) -> int:
        """Calculate effective runtime after maintenance break."""
        return self.planned_duration_minutes - self.maintenance_break_minutes


class ShiftListResponse(BaseModel):
    """Schema for shift list response."""
    
    success: bool = True
    data: list[ShiftResponse]
    total: int


class ShiftSingleResponse(BaseModel):
    """Schema for single shift response."""
    
    success: bool = True
    data: ShiftResponse


class ShiftDeleteResponse(BaseModel):
    """Schema for shift deletion response."""
    
    success: bool = True
    message: str
    shift_id: int


# =====================================================
# Uptime Calculation Schemas
# =====================================================

class UptimeResponse(BaseModel):
    """Schema for uptime response."""
    
    device_id: str
    uptime_percentage: Optional[float] = Field(None, description="Uptime percentage (0-100)")
    total_planned_minutes: int = Field(0, description="Total planned runtime in minutes")
    total_effective_minutes: int = Field(0, description="Total effective runtime (minus maintenance)")
    shifts_configured: int = Field(0, description="Number of shifts configured")
    message: str = Field(..., description="Status message")
    
    model_config = ConfigDict(from_attributes=True)
