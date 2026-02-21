"""Data models for telemetry and related entities."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class EnrichmentStatus(str, Enum):
    """Device metadata enrichment status."""
    
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class DeviceMetadata(BaseModel):
    """Device metadata from device service."""
    
    id: str = Field(..., description="Device ID")
    name: str = Field(..., description="Device name")
    type: str = Field(..., description="Device type")
    location: Optional[str] = Field(None, description="Device location")
    status: str = Field(..., description="Device status")
    health_score: Optional[float] = Field(None, ge=0, le=100, description="Health score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class TelemetryPayload(BaseModel):
    """
    Dynamic telemetry payload from MQTT.
    
    Accepts any numeric metrics dynamically. The payload must include:
    - device_id: Device identifier
    - timestamp: ISO 8601 timestamp
    
    Any additional numeric fields are accepted dynamically.
    """
    
    model_config = ConfigDict(extra="allow")
    
    device_id: str = Field(..., description="Device identifier")
    timestamp: datetime = Field(..., description="Measurement timestamp")
    schema_version: Optional[str] = Field(default="v1", description="Schema version")
    
    enrichment_status: EnrichmentStatus = Field(
        default=EnrichmentStatus.PENDING,
        description="Metadata enrichment status"
    )
    device_metadata: Optional[DeviceMetadata] = Field(
        None, 
        description="Enriched device metadata"
    )
    enriched_at: Optional[datetime] = Field(
        None, 
        description="When enrichment was completed"
    )
    
    def get_dynamic_fields(self) -> Dict[str, float]:
        """Get all dynamic numeric fields from the payload."""
        dynamic_fields = {}
        for key, value in self.model_dump().items():
            if key not in ('device_id', 'timestamp', 'schema_version', 'enrichment_status', 
                          'device_metadata', 'enriched_at') and isinstance(value, (int, float)):
                dynamic_fields[key] = float(value)
        return dynamic_fields
    
    def get_field_value(self, field_name: str) -> Optional[float]:
        """Get a specific field value by name."""
        value = getattr(self, field_name, None)
        if isinstance(value, (int, float)):
            return float(value)
        return None


class TelemetryPoint(BaseModel):
    """Single telemetry data point for queries."""
    
    model_config = ConfigDict(extra="allow")
    
    timestamp: datetime = Field(..., description="Measurement timestamp")
    device_id: str = Field(..., description="Device ID")
    schema_version: str = Field(default="v1", description="Schema version")
    enrichment_status: EnrichmentStatus = Field(
        default=EnrichmentStatus.PENDING,
        description="Enrichment status"
    )


class TelemetryQuery(BaseModel):
    """Query parameters for telemetry data."""
    
    device_id: str = Field(..., description="Device ID")
    start_time: Optional[datetime] = Field(None, description="Start time")
    end_time: Optional[datetime] = Field(None, description="End time")
    fields: Optional[list[str]] = Field(None, description="Fields to retrieve")
    aggregate: Optional[str] = Field(None, description="Aggregation function")
    interval: Optional[str] = Field(None, description="Aggregation interval")
    limit: int = Field(default=1000, ge=1, le=10000, description="Max results")


class TelemetryStats(BaseModel):
    """Aggregated telemetry statistics."""
    
    device_id: str = Field(..., description="Device ID")
    start_time: datetime = Field(..., description="Stats start time")
    end_time: datetime = Field(..., description="Stats end time")
    
    data_points: int = Field(..., description="Number of data points")


class DLQEntry(BaseModel):
    """Dead Letter Queue entry."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Entry timestamp")
    original_payload: Dict[str, Any] = Field(..., description="Original message payload")
    error_type: str = Field(..., description="Error classification")
    error_message: str = Field(..., description="Error details")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
