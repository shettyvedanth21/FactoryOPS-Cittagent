from datetime import datetime, date
from typing import Any


def clean_for_json(obj: Any) -> Any:
    """Recursively clean objects for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [clean_for_json(item) for item in obj]
    return obj


def extract_engine_data(result: dict) -> dict:
    """Extract data from standardized engine response.
    
    Args:
        result: Engine response with "success" and optional "data" keys
        
    Returns:
        The data dict if success, empty dict if failure
    """
    if isinstance(result, dict) and result.get("success") is True:
        return result.get("data", {})
    return {}
