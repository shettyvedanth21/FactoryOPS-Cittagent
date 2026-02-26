from typing import Any


def generate_insights(
    energy: dict,
    demand: dict | None,
    load_factor: dict,
    reactive: dict,
    cost: dict | None,
    device_name: str,
    date_range_days: int
) -> list[str]:
    insights = []
    
    if not energy or energy.get("success") is False:
        return ["Unable to generate insights due to insufficient energy data."]
    
    energy_data = energy.get("data", {}) if isinstance(energy.get("data"), dict) else {}
    total_kwh = energy_data.get("total_kwh", 0)
    avg_daily = total_kwh / date_range_days if date_range_days > 0 else 0
    insights.append(f"{device_name} consumed {total_kwh:.1f} kWh over {date_range_days} days, averaging {avg_daily:.1f} kWh/day.")
    
    peak_kw = 0
    if demand and demand.get("success") is not False:
        demand_data = demand.get("data", {}) if isinstance(demand.get("data"), dict) else {}
        peak_kw = demand_data.get("peak_demand_kw", 0)
        peak_ts = demand_data.get("peak_demand_timestamp", "")
        if peak_ts:
            insights.append(f"Peak demand of {peak_kw} kW recorded at {peak_ts}.")
    
    if load_factor and load_factor.get("success") is not False:
        lf_data = load_factor.get("data", {}) if isinstance(load_factor.get("data"), dict) else {}
        lf = lf_data.get("load_factor", 0)
        classification = lf_data.get("classification", "unknown")
        avg_kw = lf_data.get("avg_load_kw", 0)
        if classification == "good":
            insights.append(f"Load factor of {lf:.2f} indicates efficient continuous operation.")
        elif classification == "moderate":
            if peak_kw > 0 and avg_kw > 0:
                ratio = peak_kw / avg_kw
                insights.append(f"Load factor of {lf:.2f} is moderate - demand peaks are {ratio:.1f}x the average load.")
        else:
            insights.append(f"Load factor of {lf:.2f} is poor - significant demand peaks detected.")
    
    if reactive and reactive.get("success") is not False:
        reactive_data = reactive.get("data", {}) if isinstance(reactive.get("data"), dict) else {}
        avg_pf = reactive_data.get("avg_power_factor", 0)
        min_pf = reactive_data.get("min_power_factor", 0)
        below_threshold_pct = reactive_data.get("pf_below_threshold_pct", 0)
        
        if avg_pf < 0.90:
            insights.append(f"Average power factor {avg_pf:.2f} is below 0.90 threshold - reactive penalty applies ({below_threshold_pct:.1f}% readings below threshold).")
        else:
            insights.append(f"Power factor maintained at {avg_pf:.2f} average, meeting quality standards.")
    
    if cost and cost.get("success") is not False:
        cost_data = cost.get("data", {}) if isinstance(cost.get("data"), dict) else {}
        total = cost_data.get("total_cost", 0)
        currency = cost_data.get("currency", "INR")
        rate = cost_data.get("rate_used", {}).get("energy_rate_per_kwh", 0)
        insights.append(f"Estimated energy cost {currency} {total:,.2f} based on {currency} {rate:.2f}/kWh tariff.")
    
    return insights[:7]
