# Energy Consumption Reports - Implementation Plan

**Document Version:** 1.0  
**Date:** 2026-02-23  
**Purpose:** Product-level design & implementation plan for Energy Consumption & Comparative Analysis features

---

## 1. Current State Analysis

### 1.1 Existing Reporting Service

| Component | Status | Purpose |
|-----------|--------|---------|
| `/api/reports/generate` | ✅ Exists | Generic report generation |
| `/api/reports/status/{job_id}` | ✅ Exists | Job status tracking |
| `/api/reports/download/{job_id}` | ✅ Exists | PDF download |
| InfluxDB (Telemetry) | ✅ Exists | Raw time-series data |
| S3/MinIO | ✅ Exists | File storage |

### 1.2 Current Limitations

- No pre-aggregated daily summaries
- No energy-specific calculations (kWh)
- No comparative analysis
- No machine-wise breakdown
- PDF generation is basic

---

## 2. Feature Requirements

### 2.1 Energy Consumption Breakdown

| Feature | Description |
|---------|-------------|
| Date Range Selection | Start date, End date |
| Machine Selection | Single or All machines |
| Grouping | Daily / Weekly / Shift-wise |
| Summary | Total kWh, Average, Peak, Lowest |
| Breakdown Table | Machine-wise kWh, % contribution |
| Charts | Bar, Line, Pie |
| PDF Export | Executive-ready format |

### 2.2 Comparative Analysis

| Mode | Description |
|------|-------------|
| Machine vs Machine | Compare two machines |
| Period vs Period | Week vs Week, Month vs Month |

---

## 3. Architecture Design

### 3.1 Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   InfluxDB  │────▶│  Aggregation │────▶│  Daily Summary │
│  (Raw Data) │     │    Service   │     │     Table      │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │ Reporting API   │
                                        │ (New Endpoints) │
                                        └─────────────────┘
                                                 │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    ▼                             ▼                             ▼
           ┌──────────────┐            ┌──────────────┐            ┌──────────────┐
           │ Energy JSON  │            │ Comparison   │            │ PDF Generator│
           │   Response   │            │   Response   │            │              │
           └──────────────┘            └──────────────┘            └──────────────┘
```

### 3.2 New Components Needed

| Component | Purpose |
|-----------|---------|
| Aggregation Service | Pre-compute daily/hourly summaries |
| Energy Calculator | Convert power (W) → energy (kWh) |
| Report Models | New Pydantic models |
| New API Endpoints | `/api/reports/energy` & `/api/reports/comparison` |
| PDF Template | Executive-ready layout |

---

## 4. Data Model

### 4.1 Daily Energy Summary Table (New)

```sql
CREATE TABLE daily_energy_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    total_energy_kwh DECIMAL(15, 4) NOT NULL,
    avg_power_w DECIMAL(15, 4),
    max_power_w DECIMAL(15, 4),
    min_power_w DECIMAL(15, 4),
    operating_hours DECIMAL(10, 2),
    idle_hours DECIMAL(10, 2),
    peak_hour TIME,
    data_points INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_device_date (device_id, date),
    INDEX idx_date (date),
    INDEX idx_device (device_id)
);
```

### 4.2 API Request Models

```python
# Energy Consumption Request
class EnergyReportRequest:
    start_date: date
    end_date: date
    device_ids: List[str]  # ["D1"] or ["all"]
    group_by: str  # "daily", "weekly", "shift"
    include_charts: bool = True

# Comparative Analysis Request
class ComparisonReportRequest:
    comparison_type: str  # "machine_vs_machine", "period_vs_period"
    machine_a: str  # For machine comparison
    machine_b: str  # For machine comparison
    machine: str  # For period comparison
    period_a_start: date
    period_a_end: date
    period_b_start: date
    period_b_end: date
```

---

## 5. API Endpoints Design

### 5.1 Energy Consumption Breakdown

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reports/energy/consumption` | POST | Generate energy report |
| `/api/reports/energy/summary` | GET | Quick summary |
| `/api/reports/energy/machine/{device_id}` | GET | Single machine breakdown |

### 5.2 Comparative Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reports/compare/machines` | POST | Machine vs Machine |
| `/api/reports/compare/periods` | POST | Period vs Period |

### 5.3 PDF Export

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reports/energy/pdf` | POST | Generate PDF (async) |
| `/api/reports/compare/pdf` | POST | Generate comparison PDF (async) |

---

## 6. Business Intelligence Calculations

### 6.1 Energy Calculations

| Metric | Formula | Unit |
|--------|---------|------|
| Total Energy | Σ(power × time) | kWh |
| Average Power | Σpower / n | W |
| Load Factor | Avg Power / Peak Power | % |
| Energy per Hour | Total kWh / Operating Hours | kWh/h |

### 6.2 Intelligence Metrics

| Metric | Description | Formula |
|--------|-------------|---------|
| Load Factor | How efficiently machine runs | (Avg/Peak) × 100 |
| Energy per Operating Hour | Efficiency metric | kWh / Operating Hours |
| Idle Energy Waste | Energy during idle | (Idle Power × Idle Hours) |
| Trend Deviation | vs historical average | (Current - Average) / Average × 100 |

---

## 7. PDF Structure Design

### 7.1 Energy Consumption Report

```
╔══════════════════════════════════════════════════════════════╗
║                    ENERGY CONSUMPTION REPORT               ║
╠══════════════════════════════════════════════════════════════╣
║  Company: [Company Name]                                   ║
║  Period: [Start Date] - [End Date]                        ║
║  Generated: [Timestamp]                                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. EXECUTIVE SUMMARY                                      ║
║  ─────────────────────────────────                         ║
║  • Total Energy Consumed: X,XXX kWh                       ║
║  • Average Daily Consumption: XXX kWh                      ║
║  • Peak Consumption: XXX kWh on [Date]                     ║
║  • Lowest Consumption: XXX kWh on [Date]                   ║
║                                                              ║
║  2. MACHINE-WISE BREAKDOWN                                 ║
║  ─────────────────────────────────                         ║
║  Machine    |  Total kWh  |  %  |  Avg/Day  |  Status    ║
║  ──────────────────────────────────────────────────────── ║
║  D1         |  1,250     | 45% |  178      |  ●        ║
║  D2         |  950       | 34% |  135      |  ●        ║
║  D3         |  600       | 21% |  85       |  ○        ║
║                                                              ║
║  3. TREND ANALYSIS (Graph)                                 ║
║  ─────────────────────────────────                         ║
║  [Bar Chart: Daily Consumption]                            ║
║  [Line Chart: Trend Over Time]                            ║
║                                                              ║
║  4. KEY INSIGHTS                                           ║
║  ─────────────────────────────────                         ║
║  • Machine D1 consumed 18% more than last period          ║
║  • Peak usage observed on weekdays                         ║
║  • Weekend consumption 30% lower                           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  Generated by Energy Intelligence Platform v1.0             ║
╚══════════════════════════════════════════════════════════════╝
```

### 7.2 Comparative Analysis Report

```
╔══════════════════════════════════════════════════════════════╗
║                 COMPARATIVE ANALYSIS REPORT                 ║
╠══════════════════════════════════════════════════════════════╣
║  Comparison Type: Machine vs Machine                         ║
║  Period: [Start] - [End]                                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  METRIC              |  MACHINE A  |  MACHINE B  | DIFF  ║
║  ─────────────────────────────────────────────────────────── ║
║  Total Energy        |  1,200 kWh |  950 kWh   | +250  ║
║  Average Daily       |  171 kWh   |  135 kWh   | +36   ║
║  Peak Load           |  22 kW     |  18 kW     | +4    ║
║  Load Factor        |  78%       |  85%       | -7%   ║
║                                                              ║
║  [Comparison Bar Chart]                                     ║
║                                                              ║
║  INSIGHTS:                                                  ║
║  • Machine B is 21% more efficient                         ║
║  • Machine A has 18% higher energy consumption             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  Generated by Energy Intelligence Platform v1.0             ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 8. Implementation Phases

### Phase 1: Data Aggregation (Foundation)
- [ ] Create daily_energy_summary table
- [ ] Build aggregation service (cron job)
- [ ] Calculate kWh from power readings
- [ ] Populate historical data

### Phase 2: Energy Report API
- [ ] New endpoint: `/api/reports/energy/consumption`
- [ ] Implement date range filtering
- [ ] Machine-wise grouping
- [ ] Summary calculations

### Phase 3: Comparative Analysis
- [ ] New endpoint: `/api/reports/compare/machines`
- [ ] New endpoint: `/api/reports/compare/periods`
- [ ] Difference calculations
- [ ] Trend analysis

### Phase 4: PDF Generation
- [ ] Executive PDF template
- [ ] Charts integration
- [ ] Company branding
- [ ] Async generation

### Phase 5: Business Intelligence
- [ ] Load factor calculation
- [ ] Energy per operating hour
- [ ] Idle energy detection
- [ ] Auto-generated insights

---

## 9. Database Queries

### 9.1 Energy Consumption Query

```sql
SELECT 
    device_id,
    DATE(timestamp) as date,
    AVG(power) as avg_power,
    MAX(power) as max_power,
    MIN(power) as min_power,
    SUM(power * (interval_seconds/3600.0)) as energy_kwh
FROM telemetry
WHERE 
    device_id IN ('D1', 'D2', 'D3')
    AND timestamp BETWEEN '2026-02-01' AND '2026-02-07'
GROUP BY device_id, DATE(timestamp)
ORDER BY date;
```

### 9.2 Machine Comparison Query

```sql
SELECT 
    device_id,
    SUM(energy_kwh) as total_energy,
    AVG(daily_avg) as avg_daily,
    MAX(daily_max) as peak_load
FROM daily_energy_summary
WHERE 
    device_id IN ('D1', 'D2')
    AND date BETWEEN '2026-02-01' AND '2026-02-07'
GROUP BY device_id;
```

---

## 10. Performance Considerations

### 10.1 Pre-Aggregation Strategy

| Strategy | When | Why |
|----------|------|-----|
| Hourly summary | Real-time | Fast queries |
| Daily summary | Nightly cron | Historical reports |
| Monthly summary | Monthly cron | Long-term trends |

### 10.2 Caching

| Data | Cache TTL | Reason |
|------|----------|--------|
| Daily summaries | 1 hour | Recent data stable |
| Monthly summaries | 24 hours | Rarely changes |
| Comparison results | 30 minutes | Can vary |

### 10.3 Async Processing

- PDF generation → Background task (existing)
- Large date ranges → Async with progress
- Multiple machines → Parallel processing

---

## 11. UI Integration Points

### 11.1 New Pages Required

| Page | Features |
|------|----------|
| `/reports/energy` | Energy consumption breakdown |
| `/reports/compare` | Comparative analysis |
| `/reports/download` | Download history |

### 11.2 API Calls from UI

```javascript
// Energy Consumption
POST /api/reports/energy/consumption
{
  start_date: "2026-02-01",
  end_date: "2026-02-07",
  device_ids: ["all"],
  group_by: "daily"
}

// Machine Comparison
POST /api/reports/compare/machines
{
  machine_a: "D1",
  machine_b: "D2",
  start_date: "2026-02-01",
  end_date: "2026-02-07"
}
```

---

## 12. Estimated Effort

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 1 | Data aggregation | 2 days |
| Phase 2 | Energy API | 3 days |
| Phase 3 | Comparison API | 2 days |
| Phase 4 | PDF Generation | 3 days |
| Phase 5 | Business Intelligence | 2 days |
| **Total** | | **12 days** |

---

## 13. Dependencies

| Dependency | Purpose |
|------------|---------|
| InfluxDB | Raw telemetry data |
| MySQL | Aggregated summaries |
| S3/MinIO | PDF storage |
| Analytics Service | ML insights (optional) |

---

## 14. Success Metrics

| Metric | Target |
|--------|--------|
| Report generation time | < 30 seconds |
| PDF download size | < 5 MB |
| API response time | < 2 seconds |
| Data accuracy | > 99% |

---

## 15. Future Enhancements

- Cost estimation (kWh × tariff)
- Scheduled reports (daily/weekly email)
- Custom date presets
- Multi-company support
- Export to Excel
- White-label PDF

---

**Document Ready for Implementation**

This plan provides a complete blueprint for building the Energy Consumption and Comparative Analysis features. Each phase builds upon the previous, ensuring a solid foundation before adding advanced features.
