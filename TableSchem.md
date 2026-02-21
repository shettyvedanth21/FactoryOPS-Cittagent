# Database & Table Schema

## Overview

The Energy Enterprise platform uses two databases:

1. **MySQL** - Relational data (devices, rules, shifts, health configs, alerts)
2. **InfluxDB** - Time-series data (telemetry)

---

## MySQL Databases

| Database Name | Service | Purpose |
|--------------|---------|---------|
| `energy_device_db` | device-service | Devices, shifts, health configs |
| `energy_rule_db` | rule-engine-service | Rules, alerts |
| `energy_analytics_db` | analytics-service | Analytics jobs |
| `energy_reporting_db` | reporting-service | Report jobs |
| `energy_export_db` | data-export-service | Export checkpoints |

---

## Table Creation Schemas

### 1. devices

```sql
CREATE TABLE devices (
    device_id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50),
    device_name VARCHAR(255) NOT NULL,
    device_type VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(255),
    model VARCHAR(255),
    location VARCHAR(500),
    status VARCHAR(50) DEFAULT 'active',
    metadata_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_device_type (device_type),
    INDEX idx_status (status)
);
```

**Purpose:** Master table for all IoT devices

---

### 2. device_shifts

```sql
CREATE TABLE device_shifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    tenant_id VARCHAR(50),
    shift_name VARCHAR(100) NOT NULL,
    shift_start TIME NOT NULL,
    shift_end TIME NOT NULL,
    maintenance_break_minutes INT DEFAULT 0,
    day_of_week INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_id (device_id),
    INDEX idx_tenant_id (tenant_id)
);
```

**Purpose:** Shift configuration for uptime calculation

---

### 3. parameter_health_config

```sql
CREATE TABLE parameter_health_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    tenant_id VARCHAR(50),
    parameter_name VARCHAR(100) NOT NULL,
    normal_min FLOAT,
    normal_max FLOAT,
    max_min FLOAT,
    max_max FLOAT,
    weight FLOAT DEFAULT 0,
    ignore_zero_value BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_id (device_id),
    INDEX idx_tenant_id (tenant_id),
    UNIQUE KEY uk_device_param (device_id, parameter_name)
);
```

**Purpose:** Health scoring configuration for each parameter

---

### 4. rules

```sql
CREATE TABLE rules (
    rule_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(50),
    rule_name VARCHAR(255) NOT NULL,
    description TEXT,
    scope VARCHAR(50) DEFAULT 'selected_devices',
    property VARCHAR(100) NOT NULL,
    condition VARCHAR(20) NOT NULL,
    threshold FLOAT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    notification_channels JSON,
    cooldown_minutes INT DEFAULT 15,
    last_triggered_at DATETIME,
    device_ids JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_property (property),
    INDEX idx_status (status)
);
```

**Purpose:** Alert rule definitions

---

### 5. alerts

```sql
CREATE TABLE alerts (
    alert_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(50),
    rule_id VARCHAR(36) NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    actual_value FLOAT NOT NULL,
    threshold_value FLOAT NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    acknowledged_by VARCHAR(255),
    acknowledged_at DATETIME,
    resolved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES rules(rule_id) ON DELETE CASCADE,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_device_id (device_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);
```

**Purpose:** Generated alerts from rule evaluations

---

### 6. analytics_jobs

```sql
CREATE TABLE analytics_jobs (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    date_range_start DATETIME NOT NULL,
    date_range_end DATETIME NOT NULL,
    parameters JSON,
    status VARCHAR(50) DEFAULT 'pending',
    progress FLOAT,
    message TEXT,
    error_message TEXT,
    results JSON,
    accuracy_metrics JSON,
    execution_time_seconds INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_job_id (job_id),
    INDEX idx_device_id (device_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);
```

**Purpose:** Analytics job tracking

---

## InfluxDB Schema

### Bucket: `telemetry`

**Measurement:** `telemetry`

```influx
tagset:
  - device_id (string)
  - schema_version (string) 
  - enrichment_status (string)

fieldset:
  - Dynamic numeric fields (any parameter name)
  - Examples: pressure, temperature, voltage, current, power, etc.
```

**Example Data Point:**
```
telemetry,device_id=D1,schema_version=v1,enrichment_status=success pressure=4.5,temperature=45.0,vibration=2.1 1705968000000000000
```

---

## Entity Relationships

```
┌─────────────────┐       ┌──────────────────────┐
│    devices      │       │  device_shifts       │
│─────────────────│       │──────────────────────│
│ device_id (PK) │──────<│ device_id (FK)      │
└─────────────────┘       └──────────────────────┘

┌─────────────────┐       ┌──────────────────────────┐
│    devices      │       │  parameter_health_config │
│─────────────────│       │──────────────────────────│
│ device_id (PK) │──────<│ device_id (FK)          │
└─────────────────┘       └──────────────────────────┘

┌─────────────────┐       ┌─────────────────┐
│     rules       │       │     alerts     │
│─────────────────│       │─────────────────│
│ rule_id (PK)   │──────<│ rule_id (FK)   │
└─────────────────┘       └─────────────────┘
```

---

## Indexes Summary

| Table | Index | Purpose |
|-------|-------|---------|
| devices | idx_tenant_id | Multi-tenant queries |
| devices | idx_device_type | Filter by type |
| devices | idx_status | Filter by status |
| device_shifts | idx_device_id | Get shifts for device |
| parameter_health_config | idx_device_id | Get configs for device |
| parameter_health_config | uk_device_param | Unique param per device |
| rules | idx_property | Find rules by property |
| rules | idx_status | Filter active rules |
| alerts | idx_device_id | Get alerts for device |
| alerts | idx_status | Filter open alerts |
| analytics_jobs | idx_status | Filter by job status |

---

## Auto-Generated Fields

| Field | Type | Trigger |
|-------|------|---------|
| id | AUTO_INCREMENT | On insert (integer PK) |
| rule_id | UUID v4 | On insert (string PK) |
| alert_id | UUID v4 | On insert (string PK) |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP |

---

## Foreign Key Constraints

All foreign keys use `ON DELETE CASCADE`:
- Deleting a device removes its shifts
- Deleting a device removes its health configs
- Deleting a rule removes its alerts

---

## JSON Fields

Some columns store JSON data:

| Table | Column | Content |
|-------|--------|---------|
| devices | metadata_json | Additional device metadata |
| rules | notification_channels | ["email", "sms", "webhook"] |
| rules | device_ids | ["D1", "D2", "D3"] |
| analytics_jobs | parameters | Analysis parameters |
| analytics_jobs | results | Analysis results |
| analytics_jobs | accuracy_metrics | Model accuracy data |
