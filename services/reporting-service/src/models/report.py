"""Pydantic models for Reporting Service."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ReportFormat(str, Enum):
    """Supported report output formats."""
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"


class AnalysisType(str, Enum):
    """Types of analysis to include in reports."""
    ANOMALY = "anomaly"
    PREDICTION = "prediction"
    FORECAST = "forecast"
    ALL = "all"


class ReportStatus(str, Enum):
    """Status of report generation job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateReportRequest(BaseModel):
    """Request model for generating a report."""
    
    device_ids: List[str] = Field(
        ...,
        description="List of device IDs to include in report. Use ['all'] for all devices.",
        min_length=1
    )
    start_time: datetime = Field(
        ...,
        description="Start of time range for report data"
    )
    end_time: datetime = Field(
        ...,
        description="End of time range for report data"
    )
    analysis_types: List[AnalysisType] = Field(
        default=[AnalysisType.ALL],
        description="Types of analysis to include"
    )
    format: ReportFormat = Field(
        default=ReportFormat.PDF,
        description="Output format for the report"
    )
    include_raw_data: bool = Field(
        default=True,
        description="Include raw telemetry data in report"
    )
    include_summary: bool = Field(
        default=True,
        description="Include summary statistics"
    )
    
    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, end_time: datetime, info) -> datetime:
        """Validate that end_time is after start_time."""
        if "start_time" in info.data and end_time <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return end_time


class ReportJobResponse(BaseModel):
    """Response model for report generation request."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: ReportStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )


class ReportStatusResponse(BaseModel):
    """Response model for report status check."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: ReportStatus = Field(..., description="Current job status")
    progress_percent: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Generation progress percentage"
    )
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(..., description="Job creation time")
    started_at: Optional[datetime] = Field(
        default=None,
        description="When generation started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When generation completed"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )


class ReportDownloadResponse(BaseModel):
    """Response model for report download."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: ReportStatus = Field(..., description="Job status")
    download_url: Optional[str] = Field(
        default=None,
        description="Presigned URL for download (if completed)"
    )
    format: ReportFormat = Field(..., description="Report format")
    file_size_bytes: Optional[int] = Field(
        default=None,
        description="Size of generated report in bytes"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When download URL expires"
    )


class ReportSummary(BaseModel):
    """Summary statistics for a report."""
    
    total_devices: int = Field(..., description="Number of devices in report")
    total_records: int = Field(..., description="Total data records")
    time_range_start: datetime = Field(..., description="Start of time range")
    time_range_end: datetime = Field(..., description="End of time range")
    analysis_types_included: List[AnalysisType] = Field(
        ...,
        description="Analysis types included"
    )


class TelemetryDataPoint(BaseModel):
    """Single telemetry data point."""
    
    timestamp: datetime
    device_id: str
    voltage: Optional[float] = None
    current: Optional[float] = None
    power: Optional[float] = None
    temperature: Optional[float] = None


class AnomalyResult(BaseModel):
    """Anomaly detection result."""
    
    timestamp: datetime
    device_id: str
    is_anomaly: bool
    anomaly_score: float
    affected_metrics: List[str]
    severity: str


class PredictionResult(BaseModel):
    """Failure prediction result."""
    
    timestamp: datetime
    device_id: str
    failure_probability: float
    predicted_failure: bool
    time_to_failure_hours: Optional[float] = None
    confidence_score: float


class ForecastResult(BaseModel):
    """Energy forecasting result."""
    
    timestamp: datetime
    device_id: str
    predicted_power: float
    lower_bound: float
    upper_bound: float
    horizon_hours: int


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed health checks"
    )