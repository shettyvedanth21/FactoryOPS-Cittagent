from typing import Any


def calculate_load_factor(
    total_kwh: float,
    duration_hours: float,
    peak_demand_kw: float
) -> dict:
    if peak_demand_kw == 0:
        return {
            "success": False,
            "error_code": "LOAD_FACTOR_NOT_APPLICABLE",
            "message": "Peak demand is zero, load factor cannot be computed."
        }
    
    if duration_hours <= 0:
        return {
            "success": False,
            "error_code": "INVALID_DURATION",
            "message": "Duration must be greater than zero."
        }
    
    avg_load_kw = total_kwh / duration_hours
    load_factor = avg_load_kw / peak_demand_kw
    
    if load_factor >= 0.75:
        classification = "good"
        recommendation = "Load factor is excellent - continuous efficient operation."
    elif load_factor >= 0.50:
        classification = "moderate"
        recommendation = "Load factor is moderate - consider load balancing to improve efficiency."
    else:
        classification = "poor"
        recommendation = "Load factor is poor - significant demand peaks relative to average load."
    
    return {
        "success": True,
        "avg_load_kw": round(avg_load_kw, 2),
        "load_factor": round(load_factor, 4),
        "classification": classification,
        "recommendation": recommendation
    }
