"""Pydantic schemas for Device Service API."""

from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator


class DeviceBase(BaseModel):
    """Base schema with common device fields.
    
    Note: status field is DEPRECATED. Use runtime_status instead.
    Runtime status is computed dynamically based on telemetry activity.
    """
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    device_name: str = Field(..., min_length=1, max_length=255, description="Human-readable device name")
    device_type: str = Field(..., min_length=1, max_length=100, description="Device type (e.g., bulb, compressor)")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Device manufacturer")
    model: Optional[str] = Field(None, max_length=255, description="Device model")
    location: Optional[str] = Field(None, max_length=500, description="Physical location of device")
    phase_type: Optional[str] = Field(None, description="Electrical phase type: 'single' or 'three'")
    
    @model_validator(mode='after')
    def validate_phase_type(self) -> 'DeviceBase':
        """Validate phase_type field."""
        if self.phase_type is not None and self.phase_type not in ('single', 'three'):
            raise ValueError("phase_type must be 'single', 'three', or null")
        return self


class DeviceCreate(DeviceBase):
    """Schema for creating a new device.
    
    Note: status field is DEPRECATED and ignored. Runtime status is computed
    automatically based on telemetry activity (RUNNING/STOPPED).
    """
    
    device_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Unique device identifier (business key)"
    )
    tenant_id: Optional[str] = Field(None, max_length=50, description="Tenant ID for multi-tenancy")
    metadata_json: Optional[str] = Field(None, description="Additional metadata as JSON string")
    
    # DEPRECATED: Status is now computed dynamically from telemetry
    # This field is kept for backward compatibility but ignored
    status: Optional[str] = Field(None, description="DEPRECATED: Ignored. Use runtime_status instead.")


class DeviceUpdate(BaseModel):
    """Schema for updating an existing device.
    
    Note: status field is DEPRECATED and ignored. Runtime status is computed
    automatically based on telemetry activity.
    """
    
    device_name: Optional[str] = Field(None, min_length=1, max_length=255)
    device_type: Optional[str] = Field(None, min_length=1, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    # DEPRECATED: Status is now computed dynamically
    status: Optional[str] = Field(None, description="DEPRECATED: Ignored.")
    metadata_json: Optional[str] = Field(None, description="Additional metadata as JSON string")


class DeviceResponse(DeviceBase):
    """Schema for device response.
    
    Includes both legacy status (deprecated) and runtime_status (computed).
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    device_id: str
    tenant_id: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    # Legacy status - DEPRECATED but included for backward compatibility
    legacy_status: str = "active"
    
    # Runtime status - computed dynamically based on telemetry
    runtime_status: str = "stopped"
    last_seen_timestamp: Optional[datetime] = None


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


# =====================================================
# Health Configuration Schemas
# =====================================================

class ParameterHealthConfigBase(BaseModel):
    """Base schema for parameter health configuration."""
    
    parameter_name: str = Field(..., min_length=1, max_length=100, description="Parameter name (e.g., pressure, temperature)")
    normal_min: Optional[float] = Field(None, description="Normal range minimum")
    normal_max: Optional[float] = Field(None, description="Normal range maximum")
    max_min: Optional[float] = Field(None, description="Maximum range minimum")
    max_max: Optional[float] = Field(None, description="Maximum range maximum")
    weight: float = Field(default=0.0, ge=0, le=100, description="Weight percentage (0-100)")
    ignore_zero_value: bool = Field(default=False, description="Ignore zero values for this parameter")
    is_active: bool = Field(default=True, description="Whether this parameter is active for health scoring")


class ParameterHealthConfigCreate(ParameterHealthConfigBase):
    """Schema for creating parameter health configuration."""
    
    device_id: Optional[str] = Field(None, description="Device ID (set automatically from URL)")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (set automatically from header)")


class ParameterHealthConfigUpdate(BaseModel):
    """Schema for updating parameter health configuration."""
    
    parameter_name: Optional[str] = Field(None, min_length=1, max_length=100)
    normal_min: Optional[float] = None
    normal_max: Optional[float] = None
    max_min: Optional[float] = None
    max_max: Optional[float] = None
    weight: Optional[float] = Field(None, ge=0, le=100)
    ignore_zero_value: Optional[bool] = None
    is_active: Optional[bool] = None


class ParameterHealthConfigResponse(ParameterHealthConfigBase):
    """Schema for parameter health configuration response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    device_id: str
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ParameterHealthConfigListResponse(BaseModel):
    """Schema for health configuration list response."""
    
    success: bool = True
    data: list[ParameterHealthConfigResponse]
    total: int


class ParameterHealthConfigSingleResponse(BaseModel):
    """Schema for single health configuration response."""
    
    success: bool = True
    data: ParameterHealthConfigResponse


class WeightValidationResponse(BaseModel):
    """Schema for weight validation response."""
    
    is_valid: bool
    total_weight: float
    message: str
    parameters: list[dict]


# =====================================================
# Health Score Calculation Schemas
# =====================================================

class TelemetryValues(BaseModel):
    """Schema for telemetry values for health calculation."""
    
    values: dict[str, float] = Field(..., description="Dictionary of parameter names to values")
    machine_state: Optional[str] = Field("RUNNING", description="Machine operational state")


class ParameterScore(BaseModel):
    """Schema for individual parameter score."""
    
    parameter_name: str
    value: float
    raw_score: float
    weighted_score: float
    weight: float
    status: str
    status_color: str


class HealthScoreResponse(BaseModel):
    """Schema for health score response."""
    
    device_id: str
    health_score: Optional[float] = None
    status: str
    status_color: str
    message: str
    machine_state: str
    parameter_scores: list[ParameterScore]
    total_weight_configured: float
    parameters_included: int
    parameters_skipped: int


# =====================================================
# Device Property Schemas (Dynamic Schema Discovery)
# =====================================================

class DevicePropertyResponse(BaseModel):
    """Schema for device property response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    device_id: str
    property_name: str
    data_type: str
    is_numeric: bool
    discovered_at: datetime
    last_seen_at: datetime


class DevicePropertyListResponse(BaseModel):
    """Schema for device property list response."""
    
    success: bool = True
    data: list[DevicePropertyResponse]
    total: int


class DevicePropertiesRequest(BaseModel):
    """Request schema for getting properties for specific devices."""
    
    device_ids: list[str] = Field(..., description="List of device IDs to get properties for")


class CommonPropertiesResponse(BaseModel):
    """Response schema for common properties across devices."""
    
    success: bool = True
    properties: list[str] = Field(..., description="List of common property names")
    device_count: int = Field(..., description="Number of devices considered")
    message: str


class AllDevicesPropertiesResponse(BaseModel):
    """Response for all devices properties (for dropdown population)."""
    
    success: bool = True
    devices: dict[str, list[str]] = Field(..., description="Device ID to properties mapping")
    all_properties: list[str] = Field(..., description="All unique properties across devices")
