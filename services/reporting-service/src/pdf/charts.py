import base64
from io import BytesIO
from typing import Any, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def daily_energy_bar_chart(daily_series: list[dict], device_names: Optional[dict] = None) -> str:
    if not daily_series:
        return ""
    
    dates = [d.get("date", "") for d in daily_series]
    values = [d.get("kwh", 0) for d in daily_series]
    
    plt.figure(figsize=(12, 5))
    bars = plt.bar(dates, values, color="#1E3A5F", edgecolor="#1E3A5F", alpha=0.8)
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=8)
    
    plt.xlabel("Date", fontsize=10)
    plt.ylabel("Energy (kWh)", fontsize=10)
    plt.title("Daily Energy Consumption", fontsize=12, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"


def demand_curve_chart(window_averages: list[float], window_minutes: int = 15) -> str:
    if not window_averages:
        return ""
    
    plt.figure(figsize=(12, 5))
    x_values = list(range(1, len(window_averages) + 1))
    plt.plot(x_values, window_averages, marker='o', linewidth=2, color="#1E3A5F", markersize=4)
    
    max_idx = window_averages.index(max(window_averages))
    plt.axhline(y=window_averages[max_idx], color='red', linestyle='--', alpha=0.5, label=f'Peak: {max(window_averages):.2f} kW')
    
    plt.xlabel(f"Demand Window ({window_minutes} min intervals)", fontsize=10)
    plt.ylabel("Average Power (kW)", fontsize=10)
    plt.title("Demand Curve Over Time", fontsize=12, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"


def power_factor_distribution_chart(pf_distribution: dict) -> str:
    if not pf_distribution:
        return ""
    
    labels = ["Good (≥0.95)", "Acceptable (0.85-0.95)", "Poor (<0.85)"]
    values = [
        pf_distribution.get("good", 0),
        pf_distribution.get("acceptable", 0),
        pf_distribution.get("poor", 0)
    ]
    
    if sum(values) == 0:
        return ""
    
    colors = ["#2E7D32", "#FFC107", "#D32F2F"]
    
    plt.figure(figsize=(8, 6))
    plt.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.title("Power Factor Distribution", fontsize=12, fontweight="bold")
    plt.axis('equal')
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"


def comparison_bar_chart(metrics: dict) -> str:
    labels = list(metrics.keys())
    values_a = [metrics[k].get("a", 0) for k in labels]
    values_b = [metrics[k].get("b", 0) for k in labels]
    
    x = np.arange(len(labels))
    width = 0.35
    
    plt.figure(figsize=(12, 5))
    plt.bar(x - width/2, values_a, width, label='A', color="#1E3A5F")
    plt.bar(x + width/2, values_b, width, label='B', color="#4CAF50")
    
    plt.xlabel("Metrics", fontsize=10)
    plt.ylabel("Value", fontsize=10)
    plt.title("Comparison: Device A vs Device B", fontsize=12, fontweight="bold")
    plt.xticks(x, labels, rotation=45, ha="right")
    plt.legend()
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"


chart_generator = type('ChartGenerator', (), {
    'daily_energy_bar_chart': staticmethod(daily_energy_bar_chart),
    'demand_curve_chart': staticmethod(demand_curve_chart),
    'power_factor_distribution_chart': staticmethod(power_factor_distribution_chart),
    'comparison_bar_chart': staticmethod(comparison_bar_chart)
})()
