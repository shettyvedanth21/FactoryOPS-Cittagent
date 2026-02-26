from datetime import datetime
from io import BytesIO
from typing import Any

from weasyprint import HTML
from jinja2 import Template

from src.pdf import charts


def generate_consumption_pdf(data: dict) -> bytes:
    daily_series = data.get("daily_series", [])
    demand_windows = data.get("demand_windows", [])
    pf_dist = data.get("pf_distribution", {})
    
    charts_dict = {}
    if daily_series:
        charts_dict["daily_energy"] = charts.daily_energy_bar_chart(daily_series)
    if demand_windows:
        charts_dict["demand_curve"] = charts.demand_curve_chart(demand_windows)
    if pf_dist:
        charts_dict["pf_distribution"] = charts.power_factor_distribution_chart(pf_dist)
    
    data["charts"] = charts_dict
    data["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    template = Template(get_consumption_report_template())
    html_content = template.render(**data)
    
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


def generate_comparison_pdf(data: dict) -> bytes:
    comparison = data.get("comparison", {})
    metrics = comparison.get("metrics", {})
    
    if metrics:
        data["comparison_chart"] = charts.comparison_bar_chart(metrics)
    
    data["generated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    template = Template(get_comparison_report_template())
    html_content = template.render(**data)
    
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


def get_consumption_report_template():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Energy Consumption Report</title>
    <style>
        @page { size: A4; margin: 2cm; }
        body { font-family: Arial, sans-serif; font-size: 11px; color: #333; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #1E3A5F; padding-bottom: 10px; }
        .header h1 { color: #1E3A5F; margin: 0; font-size: 24px; }
        .header p { margin: 5px 0; color: #666; }
        .section { margin-bottom: 25px; }
        .section h2 { color: #1E3A5F; font-size: 14px; border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 10px; }
        th { background-color: #f5f5f5; font-weight: bold; }
        tr:nth-child(even) { background-color: #fafafa; }
        .kpi-grid { display: flex; justify-content: space-between; margin-bottom: 20px; }
        .kpi-box { flex: 1; background: #f5f5f5; padding: 15px; margin: 0 5px; text-align: center; border-radius: 5px; }
        .kpi-box:first-child { margin-left: 0; }
        .kpi-box:last-child { margin-right: 0; }
        .kpi-label { font-size: 10px; color: #666; text-transform: uppercase; }
        .kpi-value { font-size: 20px; color: #1E3A5F; font-weight: bold; margin-top: 5px; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 10px; font-weight: bold; }
        .badge-good { background: #d4edda; color: #155724; }
        .badge-moderate { background: #fff3cd; color: #856404; }
        .badge-poor { background: #f8d7da; color: #721c24; }
        .insight { background-color: #e8f4f8; padding: 10px; margin: 5px 0; border-left: 3px solid #1E3A5F; font-size: 10px; }
        .error-box { background-color: #fff3cd; padding: 10px; border-left: 3px solid #ffc107; color: #856404; }
        .footer { text-align: center; margin-top: 30px; font-size: 9px; color: #999; border-top: 1px solid #ddd; padding-top: 10px; }
        .chart-container { text-align: center; margin: 15px 0; }
        .chart-container img { max-width: 100%; height: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Energy Consumption Report</h1>
        <p><strong>Device:</strong> {{ device_name }}</p>
        <p><strong>Period:</strong> {{ start_date }} to {{ end_date }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
    </div>
    
    <div class="section">
        <h2>Executive Summary</h2>
        <div class="kpi-grid">
            <div class="kpi-box">
                <div class="kpi-label">Total Energy</div>
                <div class="kpi-value">{{ total_kwh }} kWh</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Peak Demand</div>
                <div class="kpi-value">{% if peak_demand_kw is not none %}{{ peak_demand_kw }} kW{% else %}N/A{% endif %}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Load Factor</div>
                <div class="kpi-value">{% if load_factor and load_factor.load_factor is defined %}{{ load_factor.load_factor }}{% elif load_factor_error %}N/A{% else %}N/A{% endif %}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-label">Total Cost</div>
                <div class="kpi-value">{% if total_cost is not none %}{{ currency }} {{ total_cost }}{% else %}N/A{% endif %}</div>
            </div>
        </div>
    </div>
    
    {% if daily_series %}
    <div class="section">
        <h2>Energy Breakdown</h2>
        <table>
            <tr><th>Date</th><th>kWh</th></tr>
            {% for day in daily_series %}
            <tr><td>{{ day.date }}</td><td>{{ day.kwh }}</td></tr>
            {% endfor %}
        </table>
        {% if charts.daily_energy %}
        <div class="chart-container">
            <img src="{{ charts.daily_energy }}" alt="Daily Energy Chart" />
        </div>
        {% endif %}
    </div>
    {% endif %}
    
    {% if demand and demand.peak_demand_kw is defined %}
    <div class="section">
        <h2>Demand Analysis</h2>
        <p><strong>Peak Demand:</strong> {{ demand.peak_demand_kw }} kW at {{ demand.peak_demand_timestamp }}</p>
        <p><strong>Window:</strong> {{ demand.demand_window_minutes }} minutes</p>
        {% if demand.top_5_windows %}
        <table>
            <tr><th>Rank</th><th>Start Time</th><th>Avg kW</th></tr>
            {% for w in demand.top_5_windows %}
            <tr><td>{{ loop.index }}</td><td>{{ w.start }}</td><td>{{ w.avg_kw }}</td></tr>
            {% endfor %}
        </table>
        {% endif %}
        {% if charts.demand_curve %}
        <div class="chart-container">
            <img src="{{ charts.demand_curve }}" alt="Demand Curve Chart" />
        </div>
        {% endif %}
    </div>
    {% elif demand_error %}
    <div class="section">
        <h2>Demand Analysis</h2>
        <div class="error-box">{{ demand_error }}</div>
    </div>
    {% endif %}
    
    {% if load_factor_data and load_factor_data.load_factor is defined %}
    <div class="section">
        <h2>Load Factor</h2>
        <p><strong>Load Factor:</strong> {{ load_factor_data.load_factor }}</p>
        <p><strong>Classification:</strong> <span class="badge badge-{{ load_factor_data.classification }}">{{ load_factor_data.classification }}</span></p>
        <p><strong>Recommendation:</strong> {{ load_factor_data.recommendation }}</p>
    </div>
    {% elif load_factor_error %}
    <div class="section">
        <h2>Load Factor</h2>
        <div class="error-box">{{ load_factor_error }}</div>
    </div>
    {% endif %}
    
    {% if reactive %}
    <div class="section">
        <h2>Reactive Power</h2>
        <p><strong>Total kVARh:</strong> {{ reactive.total_kvarh }}</p>
        <p><strong>Average PF:</strong> {{ reactive.avg_power_factor }}</p>
        <p><strong>Below Threshold:</strong> {{ reactive.pf_below_threshold_pct }}%</p>
        {% if charts.pf_distribution %}
        <div class="chart-container">
            <img src="{{ charts.pf_distribution }}" alt="PF Distribution Chart" />
        </div>
        {% endif %}
    </div>
    {% endif %}
    
    {% if power_quality %}
    <div class="section">
        <h2>Power Quality</h2>
        {% if power_quality.voltage %}
        <p><strong>Voltage:</strong> Mean {{ power_quality.voltage.mean }}V, Std {{ power_quality.voltage.std }}V</p>
        <p><strong>Outside 10%:</strong> {{ power_quality.voltage.outside_10pct_pct }}%</p>
        {% endif %}
        {% if power_quality.frequency %}
        <p><strong>Frequency:</strong> Mean {{ power_quality.frequency.mean }}Hz</p>
        {% endif %}
        {% if power_quality.thd %}
        <p><strong>THD:</strong> Mean {{ power_quality.thd.mean }}%</p>
        {% endif %}
    </div>
    {% endif %}
    
    {% if cost %}
    <div class="section">
        <h2>Cost Estimation</h2>
        <table>
            <tr><th>Component</th><th>Amount</th></tr>
            <tr><td>Energy Cost</td><td>{{ currency }} {{ cost.energy_cost }}</td></tr>
            <tr><td>Demand Cost</td><td>{{ currency }} {{ cost.demand_cost }}</td></tr>
            {% if cost.reactive_penalty > 0 %}
            <tr><td>Reactive Penalty</td><td>{{ currency }} {{ cost.reactive_penalty }}</td></tr>
            {% endif %}
            <tr><td>Fixed Charge</td><td>{{ currency }} {{ cost.fixed_charge }}</td></tr>
            <tr><td><strong>Total</strong></td><td><strong>{{ currency }} {{ cost.total_cost }}</strong></td></tr>
        </table>
    </div>
    {% elif cost_error %}
    <div class="section">
        <div class="error-box">Tariff not configured - cost estimation not available</div>
    </div>
    {% endif %}
    
    {% if insights %}
    <div class="section">
        <h2>Key Insights</h2>
        {% for insight in insights %}
        <div class="insight">{{ insight }}</div>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="footer">
        <p>Page <span class="page-num"></span> | Generated by Energy Intelligence Platform | Report ID: {{ report_id }}</p>
    </div>
</body>
</html>
"""


def get_comparison_report_template():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Energy Comparison Report</title>
    <style>
        @page { size: A4; margin: 2cm; }
        body { font-family: Arial, sans-serif; font-size: 11px; color: #333; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #1E3A5F; padding-bottom: 10px; }
        .header h1 { color: #1E3A5F; margin: 0; font-size: 24px; }
        .section { margin-bottom: 25px; }
        .section h2 { color: #1E3A5F; font-size: 14px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f5f5f5; }
        .winner { background: #d4edda; padding: 15px; text-align: center; border-radius: 5px; margin: 20px 0; }
        .winner h3 { color: #155724; margin: 0; }
        .chart-container { text-align: center; margin: 15px 0; }
        .chart-container img { max-width: 100%; }
        .insight { background-color: #e8f4f8; padding: 10px; margin: 5px 0; border-left: 3px solid #1E3A5F; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Energy Comparison Report</h1>
        <p><strong>Comparing:</strong> {{ device_a_name }} vs {{ device_b_name }}</p>
        <p><strong>Period:</strong> {{ start_date }} to {{ end_date }}</p>
        <p><strong>Generated:</strong> {{ generated_at }}</p>
    </div>
    
    {% if comparison.energy_comparison %}
    <div class="section">
        <h2>Energy Comparison</h2>
        <table>
            <tr><th>Device</th><th>Energy (kWh)</th></tr>
            <tr><td>{{ device_a_name }}</td><td>{{ comparison.energy_comparison.device_a_kwh }}</td></tr>
            <tr><td>{{ device_b_name }}</td><td>{{ comparison.energy_comparison.device_b_kwh }}</td></tr>
        </table>
        <p><strong>Difference:</strong> {{ comparison.energy_comparison.difference_kwh }} kWh ({{ comparison.energy_comparison.difference_percent }}%)</p>
        <p><strong>Higher Consumer:</strong> {{ comparison.energy_comparison.higher_consumer }}</p>
    </div>
    {% endif %}
    
    {% if comparison.demand_comparison %}
    <div class="section">
        <h2>Demand Comparison</h2>
        <table>
            <tr><th>Device</th><th>Peak Demand (kW)</th></tr>
            <tr><td>{{ device_a_name }}</td><td>{{ comparison.demand_comparison.device_a_peak_kw }}</td></tr>
            <tr><td>{{ device_b_name }}</td><td>{{ comparison.demand_comparison.device_b_peak_kw }}</td></tr>
        </table>
        <p><strong>Difference:</strong> {{ comparison.demand_comparison.difference_kw }} kW ({{ comparison.demand_comparison.difference_percent }}%)</p>
        <p><strong>Higher Demand:</strong> {{ comparison.demand_comparison.higher_demand }}</p>
    </div>
    {% endif %}
    
    {% if insights %}
    <div class="section">
        <h2>Key Insights</h2>
        {% for insight in insights %}
        <div class="insight">{{ insight }}</div>
        {% endfor %}
    </div>
    {% endif %}
    
    {% if winner %}
    <div class="winner">
        <h3>Winner: {{ winner }}</h3>
        <p>{{ winner }} is the more efficient choice based on the analysis.</p>
    </div>
    {% endif %}
</body>
</html>
"""


pdf_builder = type('PDFBuilder', (), {
    'generate_consumption_pdf': staticmethod(generate_consumption_pdf),
    'generate_comparison_pdf': staticmethod(generate_comparison_pdf)
})()
