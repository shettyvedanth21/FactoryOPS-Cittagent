"""Input validators."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.schemas import AnalyticsType


def validate_date_range(
    start_time: datetime,
    end_time: datetime,
    max_days: int = 30,
) -> None:
    """Validate date range parameters."""
    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")
    
    duration = (end_time - start_time).days
    if duration > max_days:
        raise ValueError(f"Date range cannot exceed {max_days} days")
    
    if duration < 1:
        raise ValueError("Date range must be at least 1 day")


def validate_model_for_analysis(
    model_name: str,
    analysis_type: AnalyticsType,
) -> None:
    """Validate that model is supported for analysis type."""
    valid_models = {
        AnalyticsType.ANOMALY: ["isolation_forest", "autoencoder"],
        AnalyticsType.PREDICTION: ["random_forest", "gradient_boosting"],
        AnalyticsType.FORECAST: ["prophet", "arima"],
    }
    
    allowed = valid_models.get(analysis_type, [])
    if model_name not in allowed:
        raise ValueError(
            f"Model '{model_name}' not supported for {analysis_type.value}. "
            f"Supported models: {allowed}"
        )


def validate_parameters(
    parameters: Optional[Dict[str, Any]],
    allowed_keys: Optional[List[str]] = None,
) -> None:
    """Validate model parameters."""
    if parameters is None:
        return
    
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary")
    
    if allowed_keys:
        invalid_keys = set(parameters.keys()) - set(allowed_keys)
        if invalid_keys:
            raise ValueError(f"Invalid parameter keys: {invalid_keys}")
