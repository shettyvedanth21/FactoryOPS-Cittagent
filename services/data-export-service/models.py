"""Pydantic models for Data Export Service."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    """Supported export formats."""
    PARQUET = "parquet"
    CSV = "csv"


class ExportStatus(str, Enum):
    """Export job status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TelemetryData(BaseModel):
    """Telemetry data point from InfluxDB."""
    timestamp: datetime
    device_id: str
    device_type: str
    location: str
    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    temperature: float | None = None


class ExportBatch(BaseModel):
    """Batch of telemetry data for export."""
    device_id: str
    start_time: datetime
    end_time: datetime
    records: list[TelemetryData]
    record_count: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Checkpoint(BaseModel):
    """Export checkpoint for tracking progress."""
    id: str | None = None
    device_id: str = Field(..., description="Device identifier")
    last_exported_at: datetime = Field(
        ..., 
        description="Timestamp of last successfully exported record"
    )
    last_sequence: int = Field(
        default=0,
        description="Sequence number for idempotency"
    )
    status: ExportStatus = ExportStatus.PENDING
    s3_key: str | None = None
    record_count: int = 0
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExportResult(BaseModel):
    """Result of an export operation."""
    success: bool
    device_id: str
    start_time: datetime
    end_time: datetime
    record_count: int
    s3_key: str | None = None
    format: ExportFormat
    file_size_bytes: int | None = None
    error_message: str | None = None
    duration_seconds: float = 0.0


class DatasetMetadata(BaseModel):
    """Metadata for exported dataset."""
    device_id: str
    date_partition: str  # YYYY-MM-DD format
    format: ExportFormat
    record_count: int
    start_time: datetime
    end_time: datetime
    columns: list[str]
    file_size_bytes: int
    checksum: str | None = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
