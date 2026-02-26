from typing import Any, List
from collections import defaultdict
from datetime import datetime

SQRT3 = 1.73205080757


def calculate_energy(
    rows: List[dict],
    phase_type: str
) -> dict:
    if not rows:
        return {
            "success": False,
            "error_code": "NO_TELEMETRY_DATA",
            "error_message": "No telemetry data in selected range."
        }
    
    first_row = rows[0]
    
    power_series: List[dict] = []
    
    if "power" in first_row:
        mode = "direct_power"
        total_wh = 0.0
        daily_wh = defaultdict(float)
        powers = []
        first_ts = None
        last_ts = None
        
        for i in range(len(rows)):
            row = rows[i]
            ts = row["timestamp"]
            power = row.get("power")
            
            if first_ts is None:
                first_ts = ts
            last_ts = ts
            
            if power is not None:
                powers.append(power)
                power_series.append({
                    "timestamp": ts,
                    "power_w": power
                })
            
            if i > 0:
                prev_row = rows[i - 1]
                prev_ts = prev_row["timestamp"]
                prev_power = prev_row.get("power", 0) or 0
                
                delta_seconds = (ts - prev_ts).total_seconds()
                if delta_seconds > 0 and power is not None and prev_power is not None:
                    avg_power_w = (prev_power + power) / 2
                    energy_wh = avg_power_w * delta_seconds / 3600
                    
                    total_wh += energy_wh
                    
                    day = prev_ts.date().isoformat()
                    daily_wh[day] += energy_wh
        
        total_kwh = total_wh / 1000
        daily_kwh = {day: round(wh / 1000, 2) for day, wh in daily_wh.items()}
        
        return {
            "success": True,
            "data": {
                "total_kwh": round(total_kwh, 2),
                "total_wh": round(total_wh, 2),
                "avg_power_w": round(sum(powers) / len(powers), 2) if powers else 0,
                "peak_power_w": round(max(powers), 2) if powers else 0,
                "min_power_w": round(min(powers), 2) if powers else 0,
                "data_points": len(rows),
                "computation_mode": mode,
                "phase_type_used": phase_type,
                "duration_hours": round((last_ts - first_ts).total_seconds() / 3600, 2) if first_ts and last_ts else 0,
                "daily_kwh": daily_kwh,
                "power_series": power_series
            }
        }
    
    has_voltage = "voltage" in first_row
    has_current = "current" in first_row
    has_pf = "power_factor" in first_row
    
    if has_voltage and has_current and has_pf:
        mode = "derived_single" if phase_type == "single" else "derived_three"
        
        total_wh = 0.0
        daily_wh = defaultdict(float)
        powers = []
        derived_rows = []
        first_ts = None
        last_ts = None
        
        for i in range(len(rows)):
            row = rows[i]
            ts = row["timestamp"]
            
            if first_ts is None:
                first_ts = ts
            last_ts = ts
            
            if phase_type == "single":
                power_w = row["voltage"] * row["current"] * row["power_factor"]
            elif phase_type == "three":
                power_w = SQRT3 * row["voltage"] * row["current"] * row["power_factor"]
            else:
                power_w = row["voltage"] * row["current"] * row["power_factor"]
            
            powers.append(power_w)
            power_series.append({
                "timestamp": ts,
                "power_w": power_w
            })
            derived_rows.append({
                "timestamp": ts,
                "power": power_w
            })
            
            if i > 0:
                prev_row = derived_rows[i - 1]
                prev_ts = prev_row["timestamp"]
                prev_power = prev_row["power"]
                
                delta_seconds = (ts - prev_ts).total_seconds()
                if delta_seconds > 0:
                    avg_power_w = (prev_power + power_w) / 2
                    energy_wh = avg_power_w * delta_seconds / 3600
                    
                    total_wh += energy_wh
                    
                    day = prev_ts.date().isoformat()
                    daily_wh[day] += energy_wh
        
        total_kwh = total_wh / 1000
        daily_kwh = {day: round(wh / 1000, 2) for day, wh in daily_wh.items()}
        
        return {
            "success": True,
            "data": {
                "total_kwh": round(total_kwh, 2),
                "total_wh": round(total_wh, 2),
                "avg_power_w": round(sum(powers) / len(powers), 2) if powers else 0,
                "peak_power_w": round(max(powers), 2) if powers else 0,
                "min_power_w": round(min(powers), 2) if powers else 0,
                "data_points": len(derived_rows),
                "computation_mode": mode,
                "phase_type_used": phase_type,
                "duration_hours": round((last_ts - first_ts).total_seconds() / 3600, 2) if first_ts and last_ts else 0,
                "daily_kwh": daily_kwh,
                "power_series": power_series
            }
        }
    
    return {
        "success": False,
        "error_code": "INSUFFICIENT_TELEMETRY_DATA",
        "error_message": "Required parameters (power OR voltage/current/power_factor) not available."
    }
