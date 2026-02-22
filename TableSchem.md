# Database & Table Schema - Complete Reference

## Overview

The Energy Intelligence Platform uses two databases:

1. **MySQL** - Relational data (devices, rules, shifts, health configs, alerts)
2. **InfluxDB** - Time-series data (telemetry)

---

## MySQL Databases

| Database Name | Service | Purpose |
|--------------|---------|---------|
| `energy_device_db` | device-service | Devices, shifts, health configs, properties |
| `energy_rule_db` | rule-engine-service | Rules, alerts |
| `energy_analytics_db` | analytics-service | Analytics jobs |
| `energy_reporting_db` | reporting-service | Report jobs |
| `energy_export_db` | data-export-service | Export checkpoints |

---

## Table Schemas

### 1. devices

Master table for all IoT devices in the platform.

```sql
CREATE TABLE devices (
    -- ============================================================
    -- PRIMARY KEY: Unique device identifier
    -- ============================================================
    -- Example: 'D1', 'D2', 'COMPRESSOR-001', 'MOTOR-A1'
    -- Format: Alphanumeric with hyphens/underscores allowed
    -- Max length: 50 characters
    device_id VARCHAR(50) NOT NULL PRIMARY KEY,
    
    -- ============================================================
    -- TENANT ID: Multi-tenant support (nullable for single-tenant)
    -- ============================================================
    -- Example: 'tenant-001', 'acme-corp', NULL (for single-tenant)
    -- Used for separating data between different organizations
    tenant_id VARCHAR(50),
    
    -- ============================================================
    -- DEVICE NAME: Human-readable name for display
    -- ============================================================
    -- Example: 'Device 1 - Pressure Sensor', 'Main Compressor'
    -- Max length: 255 characters
    device_name VARCHAR(255) NOT NULL,
    
    -- ============================================================
    -- DEVICE TYPE: Category of industrial equipment
    -- ============================================================
    -- Examples: 'sensor', 'motor', 'compressor', 'pump', 'meter', 'actuator'
    -- Used for filtering and grouping devices
    device_type VARCHAR(100) NOT NULL,
    
    -- ============================================================
    -- MANUFACTURER: Device manufacturer name
    -- ============================================================
    -- Example: 'Siemens', 'ABB', 'Schneider Electric', NULL
    manufacturer VARCHAR(255),
    
    -- ============================================================
    -- MODEL: Device model number
    -- ============================================================
    -- Example: 'SIMATIC S7-1500', 'PM8000', NULL
    model VARCHAR(255),
    
    -- ============================================================
    -- LOCATION: Physical location of the device
    -- ============================================================
    -- Example: 'Building A', 'Floor 2 - Room 201', 'Warehouse 1'
    -- Used for asset tracking and maintenance planning
    location VARCHAR(500),
    
    -- ============================================================
    -- LEGACY STATUS: (DEPRECATED - kept for backward compatibility)
    -- ============================================================
    -- Originally used for manual status setting
    -- Now only stores 'active' by default
    -- Runtime status is now computed from last_seen_timestamp
    legacy_status VARCHAR(50) NOT NULL DEFAULT 'active',
    
    -- ============================================================
    -- LAST SEEN TIMESTAMP: When telemetry was last received (UTC)
    -- ============================================================
    -- This is the SOURCE OF TRUTH for runtime status
    -- Updated automatically when telemetry is received
    -- NULL = device has never sent telemetry
    -- Format: UTC datetime (e.g., '2026-02-22 15:30:45.123456')
    last_seen_timestamp DATETIME(6) NULL,
    
    -- ============================================================
    -- METADATA JSON: Additional custom metadata
    -- ============================================================
    -- Store arbitrary key-value pairs as JSON
    -- Example: '{"firmware_version": "1.2.3", "serial_number": "SN12345"}'
    metadata_json TEXT,
    
    -- ============================================================
    -- TIMESTAMPS: Record creation and modification times
    -- ============================================================
    -- created_at: When device was onboarded
    -- updated_at: Last modification time (auto-updated)
    -- deleted_at: Soft delete timestamp (NULL = not deleted)
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    
    -- ============================================================
    -- INDEXES: For faster queries
    -- ============================================================
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_device_type (device_type),
    INDEX idx_last_seen (last_seen_timestamp)
);
```

**Purpose:** Master table for all IoT devices

**Runtime Status Logic:**
```python
# Status is computed dynamically based on last_seen_timestamp
# TELEMETRY_TIMEOUT_SECONDS = 60 (configurable)

IF last_seen_timestamp IS NULL:
    runtime_status = 'stopped'
ELSE IF (current_utc_time - last_seen_timestamp) <= 60 seconds:
    runtime_status = 'running'
ELSE:
    runtime_status = 'stopped'
```

---

### 2. device_shifts

Shift configuration for calculating device uptime.

```sql
CREATE TABLE device_shifts (
    -- ============================================================
    -- ID: Auto-increment primary key
    -- ============================================================
    id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    
    -- ============================================================
    -- DEVICE ID: Reference to parent device
    -- ============================================================
    -- Foreign key to devices.device_id
    -- CASCADE DELETE: Removes shifts when device is deleted
    device_id VARCHAR(50) NOT NULL,
    
    -- ============================================================
    -- TENANT ID: For multi-tenant support
    -- ============================================================
    tenant_id VARCHAR(50),
    
    -- ============================================================
    -- SHIFT NAME: Human-readable shift identifier
    -- ============================================================
    -- Example: 'Morning Shift', 'Night Shift', 'Weekend Shift'
    shift_name VARCHAR(100) NOT NULL,
    
    -- ============================================================
    -- SHIFT START: Time when shift begins
    -- ============================================================
    -- Example: '09:00:00' (9 AM)
    shift_start TIME NOT NULL,
    
    -- ============================================================
    -- SHIFT END: Time when shift ends
    -- ============================================================
    -- Example: '17:00:00' (5 PM)
    shift_end TIME NOT NULL,
    
    -- ============================================================
    -- MAINTENANCE BREAK: Break time in minutes
    -- ============================================================
    -- Example: 30 (30 minute break during shift)
    -- Subtracted from total shift duration for uptime calculation
    maintenance_break_minutes INT DEFAULT 0,
    
    -- ============================================================
    -- DAY OF WEEK: Which day this shift applies
    -- ============================================================
    -- NULL = applies to all days
    -- 0 = Monday, 1 = Tuesday, ..., 6 = Sunday
    -- Example: 0 (Monday only)
    day_of_week INT,
    
    -- ============================================================
    -- IS ACTIVE: Enable/disable this shift configuration
    -- ============================================================
    is_active TINYINT(1) DEFAULT 1,
    
    -- ============================================================
    -- TIMESTAMPS
    -- ============================================================
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- ============================================================
    -- FOREIGN KEYS & INDEXES
    -- ============================================================
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_id (device_id),
    INDEX idx_tenant_id (tenant_id)
);
```

**Purpose:** Define operating shifts for each device to calculate accurate uptime

**Uptime Calculation:**
```
Uptime = (Total Shift Hours - Downtime Hours) / Total Shift Hours × 100%
```

---

### 3. parameter_health_config

Health configuration for each telemetry parameter.

```sql
CREATE TABLE parameter_health_config (
    -- ============================================================
    -- ID: Auto-increment primary key
    -- ============================================================
    id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    
    -- ============================================================
    -- DEVICE ID: Reference to parent device
    -- ============================================================
    device_id VARCHAR(50) NOT NULL,
    
    -- ============================================================
    -- TENANT ID: For multi-tenant support
    -- ============================================================
    tenant_id VARCHAR(50),
    
    -- ============================================================
    -- PARAMETER NAME: Telemetry field to monitor
    -- ============================================================
    -- Must match a field in the telemetry data
    -- Examples: 'temperature', 'pressure', 'vibration', 'power', 'voltage'
    parameter_name VARCHAR(100) NOT NULL,
    
    -- ============================================================
    -- NORMAL MIN: Normal operating range minimum
    -- ============================================================
    -- Device is healthy when above this value
    -- Example: 20.0 (temperature in °C)
    normal_min FLOAT,
    
    -- ============================================================
    -- NORMAL MAX: Normal operating range maximum
    -- ============================================================
    -- Device is healthy when below this value
    -- Example: 60.0 (temperature in °C)
    normal_max FLOAT,
    
    -- ============================================================
    -- MAX MIN: Absolute minimum (failure threshold)
    -- ============================================================
    -- Below this = complete failure
    -- Example: 0.0
    max_min FLOAT,
    
    -- ============================================================
    -- MAX MAX: Absolute maximum (failure threshold)
    -- ============================================================
    -- Above this = complete failure
    -- Example: 100.0
    max_max FLOAT,
    
    -- ============================================================
    -- WEIGHT: Contribution to overall health score
    -- ============================================================
    -- MUST sum to 100 for all parameters of a device
    -- Example: 25.0 (25% of total health score)
    weight FLOAT NOT NULL,
    
    -- ============================================================
    -- IGNORE ZERO VALUE: Skip zero values in calculation
    -- ============================================================
    -- Useful for parameters that can legitimately be zero
    -- Example: true for 'power' when device is standby
    ignore_zero_value TINYINT(1) NOT NULL DEFAULT 0,
    
    -- ============================================================
    -- IS ACTIVE: Enable/disable this parameter
    -- ============================================================
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    
    -- ============================================================
    -- TIMESTAMPS
    -- ============================================================
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    
    -- ============================================================
    -- FOREIGN KEYS & INDEXES
    -- ============================================================
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_id (device_id),
    INDEX idx_tenant_id (tenant_id),
    UNIQUE KEY uk_device_param (device_id, parameter_name)
);
```

**Health Score Calculation Example:**
```python
# Example: Temperature parameter
normal_min = 20.0
normal_max = 60.0
max_min = 0.0
max_max = 100.0
weight = 25.0

# Current telemetry value
current_value = 45.0

# Calculate parameter score (linear interpolation)
if current_value < max_min:
    score = 0
elif current_value > max_max:
    score = 0
elif current_value < normal_min:
    # Between max_min and normal_min
    score = (current_value - max_min) / (normal_min - max_min) * 100
elif current_value > normal_max:
    # Between normal_max and max_max
    score = (max_max - current_value) / (max_max - normal_max) * 100
else:
    # Within normal range
    score = 100

# Overall health score = weighted average
health_score = Σ(parameter_score × weight) / Σ(weights)
```

---

### 4. device_properties

Dynamically discovered properties from telemetry.

```sql
CREATE TABLE device_properties (
    -- ============================================================
    -- ID: Auto-increment primary key
    -- ============================================================
    id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    
    -- ============================================================
    -- DEVICE ID: Reference to parent device
    -- ============================================================
    device_id VARCHAR(50) NOT NULL,
    
    -- ============================================================
    -- PROPERTY NAME: Telemetry field name
    -- ============================================================
    -- Examples: 'temperature', 'pressure', 'voltage', 'power'
    property_name VARCHAR(100) NOT NULL,
    
    -- ============================================================
    -- DATA TYPE: Type of the property value
    -- ============================================================
    -- Examples: 'float', 'integer', 'string', 'boolean'
    data_type VARCHAR(20) NOT NULL,
    
    -- ============================================================
    -- IS NUMERIC: Whether property is numeric (for rules)
    -- ============================================================
    is_numeric TINYINT(1) NOT NULL,
    
    -- ============================================================
    -- DISCOVERED AT: When property was first seen
    -- ============================================================
    discovered_at DATETIME NOT NULL,
    
    -- ============================================================
    -- LAST SEEN AT: When property was last received
    -- ============================================================
    last_seen_at DATETIME NOT NULL,
    
    -- ============================================================
    -- FOREIGN KEYS & INDEXES
    -- ============================================================
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    INDEX idx_device_id (device_id)
);
```

**Purpose:** Track which properties each device has sent. Used for:
- Dynamic property dropdown in rule creation
- Finding common properties across multiple devices

---

### 5. rules

Rule definitions for alerting.

```sql
CREATE TABLE rules (
    -- ============================================================
    -- RULE ID: Unique identifier (UUID format)
    -- ============================================================
    -- Example: '3db07cb9-54f3-4fc8-b863-2ab8fb797a78'
    -- Format: UUID v4
    rule_id VARCHAR(36) NOT NULL PRIMARY KEY,
    
    -- ============================================================
    -- TENANT ID: For multi-tenant support
    -- ============================================================
    tenant_id VARCHAR(50),
    
    -- ============================================================
    -- RULE NAME: Human-readable name
    -- ============================================================
    -- Example: 'High Temperature Alert', 'Pressure Warning'
    rule_name VARCHAR(255) NOT NULL,
    
    -- ============================================================
    -- DESCRIPTION: Optional rule description
    -- ============================================================
    description TEXT,
    
    -- ============================================================
    -- SCOPE: Rule application scope
    -- ============================================================
    -- 'all_devices' = apply to all active devices
    -- 'selected_devices' = apply only to specified devices
    scope VARCHAR(50) NOT NULL,
    
    -- ============================================================
    -- PROPERTY: Telemetry field to evaluate
    -- ============================================================
    -- Must match a property in device_properties
    -- Example: 'temperature', 'pressure', 'power'
    property VARCHAR(100) NOT NULL,
    
    -- ============================================================
    -- CONDITION: Comparison operator
    -- ============================================================
    -- Examples: '>', '<', '>=', '<=', '==', '!='
    condition VARCHAR(20) NOT NULL,
    
    -- ============================================================
    -- THRESHOLD: Value to compare against
    -- ============================================================
    -- Example: 80.0 (alert when temperature > 80)
    threshold FLOAT NOT NULL,
    
    -- ============================================================
    -- STATUS: Rule active state
    -- ============================================================
    -- 'active' = rule is being evaluated
    -- 'paused' = rule is temporarily disabled
    status VARCHAR(50) NOT NULL,
    
    -- ============================================================
    -- NOTIFICATION CHANNELS: Where to send alerts
    -- ============================================================
    -- JSON array of channels
    -- Example: ['email', 'webhook', 'sms']
    notification_channels JSON NOT NULL,
    
    -- ============================================================
    -- COOLDOWN MINUTES: Minimum time between alerts
    -- ============================================================
    -- Prevents alert spam
    -- Example: 5 (only alert once per 5 minutes)
    cooldown_minutes INT NOT NULL,
    
    -- ============================================================
    -- LAST TRIGGERED AT: When rule last fired
    -- ============================================================
    -- Used for cooldown calculation
    -- NULL = never triggered
    last_triggered_at DATETIME,
    
    -- ============================================================
    -- DEVICE IDS: Which devices to apply rule to
    -- ============================================================
    -- JSON array of device IDs (for 'selected_devices' scope)
    -- Example: ['D1', 'D2', 'D3']
    device_ids JSON NOT NULL,
    
    -- ============================================================
    -- TIMESTAMPS
    -- ============================================================
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME,
    
    -- ============================================================
    -- INDEXES
    -- ============================================================
    INDEX idx_property (property),
    INDEX idx_status (status),
    INDEX idx_tenant_id (tenant_id)
);
```

**Rule Evaluation Logic:**
```python
# Example rule
rule = {
    "property": "temperature",
    "condition": ">",
    "threshold": 80.0,
    "cooldown_minutes": 5,
    "device_ids": ["D1", "D2"]
}

# For each device in device_ids:
# 1. Get latest telemetry value for property
# 2. Compare using condition
# 3. If true AND not in cooldown → trigger alert
# 4. Update last_triggered_at
```

---

## InfluxDB Schema

### Bucket: telemetry

**Measurement:** (default)

**Tags:**
- `device_id`: Device identifier
- `device_type`: Device type
- `location`: Device location

**Fields:** (dynamic based on device)
- `temperature`: float (°C)
- `pressure`: float (bar)
- `power`: float (W)
- `voltage`: float (V)
- `current`: float (A)
- etc.

**Example Query:**
```flux
from(bucket: "telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r.device_id == "D1")
  |> filter(fn: (r) => r._field == "temperature")
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                devices                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ device_id (PK)        │ tenant_id   │ device_name   │ device_type         │
│ legacy_status         │ location    │ last_seen_timestamp                │
│ created_at           │ updated_at   │ deleted_at    │ metadata_json        │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────────┐
│      device_shifts              │  │    parameter_health_config           │
├─────────────────────────────────┤  ├─────────────────────────────────────┤
│ id (PK)                         │  │ id (PK)                             │
│ device_id (FK) ────────────────┤  │ device_id (FK) ────────────────────┤
│ shift_name                     │  │ parameter_name                      │
│ shift_start                    │  │ normal_min / normal_max             │
│ shift_end                      │  │ max_min / max_max                   │
│ maintenance_break_minutes      │  │ weight                              │
│ day_of_week                    │  │ ignore_zero_value                   │
│ is_active                      │  │ is_active                           │
└─────────────────────────────────┘  └─────────────────────────────────────┘

┌─────────────────────────────────┐
│      device_properties          │
├─────────────────────────────────┤
│ id (PK)                         │
│ device_id (FK) ────────────────┤
│ property_name                   │
│ data_type                       │
│ is_numeric                      │
│ discovered_at                  │
│ last_seen_at                    │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│           rules                 │
├─────────────────────────────────┤
│ rule_id (PK)                    │
│ tenant_id                       │
│ rule_name                       │
│ description                     │
│ scope                           │
│ property                        │
│ condition                       │
│ threshold                       │
│ status                          │
│ notification_channels (JSON)     │
│ cooldown_minutes                │
│ last_triggered_at               │
│ device_ids (JSON)               │
│ created_at / updated_at         │
└─────────────────────────────────┘
```

---

## Index Summary

| Table | Index | Purpose |
|-------|-------|---------|
| devices | PRIMARY (device_id) | Primary key lookup |
| devices | idx_tenant_id | Filter by tenant |
| devices | idx_device_type | Filter by type |
| devices | idx_last_seen | Runtime status calculation |
| device_shifts | idx_device_id | Get shifts for device |
| device_shifts | idx_tenant_id | Filter by tenant |
| parameter_health_config | idx_device_id | Get configs for device |
| parameter_health_config | uk_device_param | Unique constraint |
| device_properties | idx_device_id | Get properties for device |
| rules | idx_property | Find rules by property |
| rules | idx_status | Filter active/paused rules |
| rules | idx_tenant_id | Filter by tenant |

---

## Data Flow Summary

```
┌──────────────┐    MQTT     ┌──────────────┐
│   Device     │ ─────────► │  EMQX Broker │
└──────────────┘             └───────┬───────┘
                                    │
                                    ▼
                           ┌──────────────┐
                           │ Data Service │
                           └───────┬───────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
           ▼                       ▼                       ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │  InfluxDB   │      │Device Service│      │Rule Engine  │
    │ (Telemetry) │      │(last_seen)  │      │(evaluate)   │
    └──────────────┘      └──────────────┘      └──────────────┘
                                    │               │
                                    ▼               ▼
                           ┌──────────────────┐
                           │    MySQL DB      │
                           │ - devices        │
                           │ - device_shifts  │
                           │ - parameter_health_config │
                           │ - device_properties │
                           │ - rules          │
                           └──────────────────┘
```

---

**End of Schema Documentation**
