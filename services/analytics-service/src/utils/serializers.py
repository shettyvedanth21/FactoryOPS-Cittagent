"""Data serializers."""

import json
from datetime import datetime
from typing import Any, Dict

import numpy as np
import pandas as pd


class AnalyticsJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for analytics data."""

    def default(self, obj: Any) -> Any:

        if isinstance(obj, np.ndarray):
            return obj.tolist()

        if isinstance(obj, (np.integer,)):
            return int(obj)

        if isinstance(obj, (np.floating,)):
            val = float(obj)
            if np.isnan(val) or np.isinf(val):
                return None
            return val

        if isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return obj

        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()

        if isinstance(obj, pd.Series):
            return obj.tolist()

        return super().default(obj)


def serialize_results(results: Dict[str, Any]) -> str:
    """Serialize results to JSON string."""
    return json.dumps(results, cls=AnalyticsJSONEncoder)


def deserialize_results(json_str: str) -> Dict[str, Any]:
    """Deserialize results from JSON string."""
    return json.loads(json_str)