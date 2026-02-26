from decimal import Decimal
from typing import Any


def calculate_cost(
    total_kwh: float,
    peak_demand_kw: float,
    total_kvarh: float | None,
    tariff: dict | None,
    duration_days: float
) -> dict:
    if tariff is None:
        return {
            "success": False,
            "error_code": "TARIFF_NOT_CONFIGURED",
            "error_message": "No tariff configured for this tenant. Set tariff via POST /api/reports/tariffs"
        }
    
    energy_rate = float(tariff.get("energy_rate_per_kwh", 0))
    demand_rate = float(tariff.get("demand_charge_per_kw", 0))
    reactive_rate = float(tariff.get("reactive_penalty_rate", 0))
    fixed_monthly = float(tariff.get("fixed_monthly_charge", 0))
    pf_threshold = float(tariff.get("power_factor_threshold", 0.90))
    currency = tariff.get("currency", "INR")
    
    energy_cost = total_kwh * energy_rate
    demand_cost = peak_demand_kw * demand_rate
    
    reactive_penalty = 0.0
    if total_kvarh and reactive_rate > 0:
        if total_kwh > 0:
            apparent_power_kva = total_kwh
            avg_pf = total_kwh / apparent_power_kva if apparent_power_kva > 0 else 1.0
            if avg_pf < pf_threshold:
                reactive_penalty = total_kvarh * reactive_rate
    
    prorated_fixed = fixed_monthly * (duration_days / 30)
    total_cost = energy_cost + demand_cost + reactive_penalty + prorated_fixed
    
    return {
        "success": True,
        "data": {
            "energy_cost": round(energy_cost, 2),
            "demand_cost": round(demand_cost, 2),
            "reactive_penalty": round(reactive_penalty, 2),
            "fixed_charge": round(prorated_fixed, 2),
            "total_cost": round(total_cost, 2),
            "currency": currency,
            "rate_used": {
                "energy_rate_per_kwh": energy_rate,
                "demand_charge_per_kw": demand_rate
            }
        }
    }
