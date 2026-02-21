"""Telemetry input schemas for rule evaluation."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TelemetryIn(BaseModel):
    """Input schema for telemetry evaluation.
    
    Accepts any metric fields dynamically via the values dict,
    plus required device identification.
    """
    
    device_id: str = Field(..., description="Device identifier")
    metric: str = Field(..., description="Metric name to evaluate (e.g., temperature, voltage)")
    value: float = Field(..., description="Metric value to evaluate")
    
    # Optional additional fields
    values: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metric values for multi-metric evaluation"
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="Optional timestamp of the telemetry reading"
    )
