from datetime import datetime, timedelta
from typing import Any


def calculate_demand(
    rows: list[dict],
    window_minutes: int = 15
) -> dict:
    if not rows:
        return {
            "success": False,
            "error_code": "INSUFFICIENT_DEMAND_DATA",
            "message": "Not enough data for demand window calculation."
        }
    
    sorted_rows = sorted(rows, key=lambda r: r["timestamp"])
    
    if "power" not in sorted_rows[0]:
        return {
            "success": False,
            "error_code": "INSUFFICIENT_DEMAND_DATA",
            "message": "Power field required for demand calculation."
        }
    
    start_time = sorted_rows[0]["timestamp"]
    end_time = sorted_rows[-1]["timestamp"]
    
    window_seconds = window_minutes * 60
    window_averages = []
    window_starts = []
    
    current_window_start = start_time
    while current_window_start < end_time:
        current_window_end = current_window_start + timedelta(minutes=window_minutes)
        
        window_rows = [
            r for r in sorted_rows
            if current_window_start <= r["timestamp"] < current_window_end
        ]
        
        if len(window_rows) >= 2:
            window_energy_wh = 0.0
            for i in range(len(window_rows) - 1):
                delta_seconds = (window_rows[i + 1]["timestamp"] - window_rows[i]["timestamp"]).total_seconds()
                avg_power_w = (window_rows[i]["power"] + window_rows[i + 1]["power"]) / 2
                window_energy_wh += avg_power_w * delta_seconds / 3600
            
            avg_kw = window_energy_wh / (window_minutes / 60)
            window_averages.append(avg_kw)
            window_starts.append(current_window_start)
        
        current_window_start = current_window_end
    
    if not window_averages:
        return {
            "success": False,
            "error_code": "INSUFFICIENT_DEMAND_DATA",
            "message": "Not enough data for demand window calculation."
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
        "peak_demand_kw": round(peak_demand_kw, 2),
        "peak_demand_timestamp": peak_demand_timestamp.isoformat(),
        "demand_window_minutes": window_minutes,
        "top_5_windows": top_5_windows,
        "all_window_averages": [round(wa, 2) for wa in window_averages]
    }
