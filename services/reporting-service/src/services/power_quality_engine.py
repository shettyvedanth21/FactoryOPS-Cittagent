import math
from typing import Any


def calculate_power_quality(rows: list[dict]) -> dict:
    if not rows:
        return {
            "success": False,
            "error_code": "NO_POWER_QUALITY_DATA",
            "message": "No quality metrics in telemetry."
        }
    
    result = {}
    first_row = rows[0]
    
    if "voltage" in first_row:
        voltages = [r["voltage"] for r in rows if "voltage" in r]
        if voltages:
            mean_voltage = sum(voltages) / len(voltages)
            variance = sum((v - mean_voltage) ** 2 for v in voltages) / len(voltages)
            std_voltage = math.sqrt(variance)
            nominal = mean_voltage
            outside_count = sum(1 for v in voltages if abs(v - nominal) / nominal > 0.10)
            outside_pct = (outside_count / len(voltages) * 100) if voltages else 0
            
            result["voltage"] = {
                "mean": round(mean_voltage, 2),
                "std": round(std_voltage, 2),
                "outside_10pct_count": outside_count,
                "outside_10pct_pct": round(outside_pct, 2)
            }
    
    if "frequency" in first_row:
        frequencies = [r["frequency"] for r in rows if "frequency" in r]
        if frequencies:
            mean_frequency = sum(frequencies) / len(frequencies)
            outside_count = sum(1 for f in frequencies if abs(f - 50.0) > 0.5)
            outside_pct = (outside_count / len(frequencies) * 100) if frequencies else 0
            
            result["frequency"] = {
                "mean": round(mean_frequency, 2),
                "outside_half_hz_pct": round(outside_pct, 2)
            }
    
    if "thd" in first_row:
        thds = [r["thd"] for r in rows if "thd" in r]
        if thds:
            mean_thd = sum(thds) / len(thds)
            above_count = sum(1 for t in thds if t > 5.0)
            above_pct = (above_count / len(thds) * 100) if thds else 0
            
            result["thd"] = {
                "mean": round(mean_thd, 2),
                "above_5pct_pct": round(above_pct, 2)
            }
    
    if not result:
        return {
            "success": False,
            "error_code": "NO_POWER_QUALITY_DATA",
            "message": "No quality metrics in telemetry."
        }
    
    return {
        "success": True,
        **result
    }
