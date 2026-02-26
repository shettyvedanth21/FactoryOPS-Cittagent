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
    insights = []
    winner = None
    
    if energy_a.get("success") is not False and energy_b.get("success") is not False:
        kwh_a = energy_a.get("data", {}).get("total_kwh", 0) if isinstance(energy_a.get("data"), dict) else 0
        kwh_b = energy_b.get("data", {}).get("total_kwh", 0) if isinstance(energy_b.get("data"), dict) else 0
        diff_kwh = kwh_a - kwh_b
        pct_diff = (diff_kwh / kwh_b * 100) if kwh_b > 0 else 0
        
        result["energy_comparison"] = {
            "device_a_kwh": round(kwh_a, 2),
            "device_b_kwh": round(kwh_b, 2),
            "difference_kwh": round(diff_kwh, 2),
            "difference_percent": round(pct_diff, 2),
            "higher_consumer": device_name_a if diff_kwh > 0 else device_name_b
        }
        
        if diff_kwh > 0:
            insights.append(f"{device_name_a} consumed {abs(diff_kwh):.1f} kWh more than {device_name_b}")
            winner = device_name_b
        elif diff_kwh < 0:
            insights.append(f"{device_name_b} consumed {abs(diff_kwh):.1f} kWh more than {device_name_a}")
            winner = device_name_a
        else:
            insights.append(f"{device_name_a} and {device_name_b} consumed equal energy")
    
    if demand_a.get("success") is not False and demand_b.get("success") is not False:
        peak_a = demand_a.get("data", {}).get("peak_demand_kw", 0) if isinstance(demand_a.get("data"), dict) else 0
        peak_b = demand_b.get("data", {}).get("peak_demand_kw", 0) if isinstance(demand_b.get("data"), dict) else 0
        diff_peak = peak_a - peak_b
        pct_peak_diff = (diff_peak / peak_b * 100) if peak_b > 0 else 0
        
        result["demand_comparison"] = {
            "device_a_peak_kw": round(peak_a, 2),
            "device_b_peak_kw": round(peak_b, 2),
            "difference_kw": round(diff_peak, 2),
            "difference_percent": round(pct_peak_diff, 2),
            "higher_demand": device_name_a if diff_peak > 0 else device_name_b
        }
    
    if not result:
        return {
            "success": False,
            "error_code": "INSUFFICIENT_COMPARISON_DATA",
            "error_message": "No valid data for comparison. Both devices must have energy or demand data."
        }
    
    return {
        "success": True,
        "data": {
            "metrics": result,
            "winner": winner,
            "insights": insights
        }
    }
