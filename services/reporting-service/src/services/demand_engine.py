from datetime import datetime, timedelta
from typing import Any, List
import logging

logger = logging.getLogger(__name__)


def calculate_demand(
    power_series: List[dict],
    window_minutes: int = 15
) -> dict:
    if not power_series:
        return {
            "success": False,
            "error_code": "INSUFFICIENT_DEMAND_DATA",
            "error_message": "No power data available for demand calculation."
        }
    
    def parse_timestamp(ts):
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except Exception:
                return None
        return None
    
    logger.info(f"calculate_demand: received {len(power_series)} power_series items")
    
    sorted_rows = sorted(power_series, key=lambda r: r.get("timestamp"))
    
    for r in sorted_rows:
        if 'timestamp' in r:
            parsed = parse_timestamp(r['timestamp'])
            if parsed:
                r['_parsed_timestamp'] = parsed
    
    valid_rows = [r for r in sorted_rows if r.get('_parsed_timestamp')]
    logger.info(f"calculate_demand: {len(valid_rows)} valid rows after parsing timestamps")
    logger.info(f"First timestamp: {valid_rows[0].get('_parsed_timestamp') if valid_rows else 'N/A'}")
    logger.info(f"Last timestamp: {valid_rows[-1].get('_parsed_timestamp') if valid_rows else 'N/A'}")
    logger.info(f"Duration: {(valid_rows[-1].get('_parsed_timestamp') - valid_rows[0].get('_parsed_timestamp')).total_seconds() / 3600 if valid_rows else 'N/A'} hours")
    
    sorted_rows = valid_rows
    
    if not sorted_rows or "power_w" not in sorted_rows[0]:
        return {
            "success": False,
            "error_code": "INSUFFICIENT_DEMAND_DATA",
            "error_message": "Power series must contain power_w field for demand calculation."
        }
    
    start_time = sorted_rows[0].get("_parsed_timestamp")
    end_time = sorted_rows[-1].get("_parsed_timestamp")
    
    if not start_time or not end_time:
        return {
            "success": False,
            "error_code": "INSUFFICIENT_DEMAND_DATA",
            "error_message": "Power series must have valid timestamps."
        }
    
    window_seconds = window_minutes * 60
    window_averages = []
    window_starts = []
    
    current_window_start = start_time
    while current_window_start < end_time:
        current_window_end = current_window_start + timedelta(minutes=window_minutes)
        
        window_rows = [
            r for r in sorted_rows
            if current_window_start <= r.get("_parsed_timestamp") < current_window_end
        ]
        
        # With aggregated data, we may only have 1 point per window - use that single point as the average
        if len(window_rows) >= 1:
            # Use average power in the window as the demand
            avg_power_w = sum(r.get("power_w", 0) or 0 for r in window_rows) / len(window_rows)
            avg_kw = avg_power_w / 1000
            window_averages.append(avg_kw)
            window_starts.append(current_window_start)
        
        current_window_start = current_window_end
    
    logger.info(f"calculate_demand: {len(window_averages)} windows with >= 2 data points")
    
    if not window_averages:
        return {
            "success": False,
            "error_code": "INSUFFICIENT_DEMAND_DATA",
            "error_message": "Not enough data points for demand window calculation."
        }
    
    peak_index = window_averages.index(max(window_averages))
    peak_demand_kw = window_averages[peak_index]
    peak_demand_timestamp = window_starts[peak_index]
    
    sorted_windows = sorted(
        enumerate(zip(window_starts, window_averages)),
        key=lambda x: x[1][1],
        reverse=True
    )[:5]
    
    top_5_windows = [
        {
            "start": ws.isoformat(),
            "end": (ws + timedelta(minutes=window_minutes)).isoformat(),
            "avg_kw": round(aw, 2)
        }
        for _, (ws, aw) in sorted_windows
    ]
    
    return {
        "success": True,
        "data": {
            "peak_demand_kw": round(peak_demand_kw, 2),
            "peak_demand_timestamp": peak_demand_timestamp.isoformat(),
            "demand_window_minutes": window_minutes,
            "top_5_windows": top_5_windows,
            "all_window_averages": [round(wa, 2) for wa in window_averages]
        }
    }
