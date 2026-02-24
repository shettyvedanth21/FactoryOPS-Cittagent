from typing import Any


def calculate_comparison(
    energy_a: dict,
    energy_b: dict,
    demand_a: dict,
    demand_b: dict,
    device_name_a: str,
    device_name_b: str
) -> dict:
    result = {}
    
    if "error" not in energy_a and "error" not in energy_b:
        kwh_a = energy_a.get("total_kwh", 0)
        kwh_b = energy_b.get("total_kwh", 0)
        diff_kwh = kwh_a - kwh_b
        pct_diff = (diff_kwh / kwh_b * 100) if kwh_b > 0 else 0
        
        result["energy_comparison"] = {
            "device_a_kwh": round(kwh_a, 2),
            "device_b_kwh": round(kwh_b, 2),
            "difference_kwh": round(diff_kwh, 2),
            "difference_percent": round(pct_diff, 2),
            "higher_consumer": device_name_a if diff_kwh > 0 else device_name_b
        }
    
    if "error" not in demand_a and "error" not in demand_b:
        peak_a = demand_a.get("peak_demand_kw", 0)
        peak_b = demand_b.get("peak_demand_kw", 0)
        diff_peak = peak_a - peak_b
        pct_peak_diff = (diff_peak / peak_b * 100) if peak_b > 0 else 0
        
        result["demand_comparison"] = {
            "device_a_peak_kw": round(peak_a, 2),
            "device_b_peak_kw": round(peak_b, 2),
            "difference_kw": round(diff_peak, 2),
            "difference_percent": round(pct_peak_diff, 2),
            "higher_demand": device_name_a if diff_peak > 0 else device_name_b
        }
    
    return result
