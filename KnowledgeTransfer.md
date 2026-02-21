# Energy Enterprise Platform - Knowledge Transfer Document

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Services](#services)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [Features](#features)
7. [Running the Project](#running-the-project)
8. [Key Concepts](#key-concepts)

---

## Project Overview

**Energy Enterprise** is a comprehensive IoT platform for monitoring and managing industrial devices. It provides real-time telemetry collection, rule-based alerting, analytics, reporting, and a modern web UI.

### Technology Stack
- **Backend**: Python (FastAPI), Node.js
- **Database**: MySQL 8.0 (relational), InfluxDB (time-series)
- **Message Broker**: MQTT (EMQX)
- **Object Storage**: MinIO (S3-compatible)
- **Frontend**: Next.js 14 (React)
- **Containerization**: Docker Compose

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           UI Web (Next.js)                             │
│                         http://localhost:3000                           │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌───▼────┐
   │ Device  │   │  Data   │   │  Rule  │
   │ Service │   │ Service │   │ Engine │
   │  :8000  │   │  :8081  │   │ :8002  │
   └────┬────┘   └────┬────┘   └───┬────┘
        │             │             │
        │      ┌──────▼──────┐      │
        │      │   InfluxDB  │      │
        │      │    :8086    │      │
        │      └─────────────┘      │
        │                           │
        │      ┌────────────────┐    │
        │      │  MySQL :3306   │◄───┘
        │      └────────────────┘
        │
   ┌────▼────────────────────────┐
   │    MQTT Broker (EMQX)       │
   │         :1883               │
   └─────────────────────────────┘
```

---

## Services

### 1. Device Service (:8000)
Manages devices, shifts, and health configuration.

**Features:**
- Device CRUD operations
- Shift configuration for uptime calculation
- Parameter health configuration
- Health score calculation

**Database:** `energy_device_db`

---

### 2. Data Service (:8081)
Handles telemetry ingestion and storage.

**Features:**
- MQTT ingestion from devices
- InfluxDB storage for time-series data
- Real-time enrichment with device metadata
- WebSocket support for live data

**Database:** MySQL (device metadata cache)

---

### 3. Rule Engine Service (:8002)
Evaluates rules and generates alerts.

**Features:**
- Rule CRUD operations
- Real-time threshold monitoring
- Alert generation and management
- Cooldown management

**Database:** `energy_rule_db`

---

### 4. Analytics Service (:8003)
Runs analytics jobs on telemetry data.

**Features:**
- Anomaly detection
- Failure prediction
- Energy forecasting

**Database:** `energy_analytics_db`

---

### 5. Data Export Service (:8080)
Exports telemetry data to S3.

**Features:**
- CSV/JSON export
- Scheduled exports
- Checkpoint-based exports

---

### 6. Reporting Service (:8085)
Generates PDF/Excel reports.

**Features:**
- Report generation
- Multiple output formats
- Async job processing

---

### 7. UI Web (:3000)
Next.js web application.

**Pages:**
- `/machines` - Device list
- `/machines/[deviceId]` - Device dashboard
- `/rules` - Rule management
- `/analytics` - Analytics dashboard

---

## Database Schema

### MySQL Tables

#### 1. `devices` (device-service)
| Column | Type | Description |
|--------|------|-------------|
| device_id | VARCHAR(50) PK | Unique device identifier |
| tenant_id | VARCHAR(50) | Multi-tenant support |
| device_name | VARCHAR(255) | Human-readable name |
| device_type | VARCHAR(100) | Device type |
| manufacturer | VARCHAR(255) | Manufacturer name |
| model | VARCHAR(255) | Model number |
| location | VARCHAR(500) | Physical location |
| status | VARCHAR(50) | active/inactive/maintenance/error |
| metadata_json | TEXT | Additional metadata |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update |
| deleted_at | DATETIME | Soft delete timestamp |

---

#### 2. `device_shifts` (device-service)
| Column | Type | Description |
|--------|------|-------------|
| id | INT PK | Auto-increment ID |
| device_id | VARCHAR(50) FK | References devices.device_id |
| tenant_id | VARCHAR(50) | Multi-tenant support |
| shift_name | VARCHAR(100) | Shift name |
| shift_start | TIME | Shift start time |
| shift_end | TIME | Shift end time |
| maintenance_break_minutes | INT | Break duration |
| day_of_week | INT | 0=Monday, 6=Sunday |
| is_active | BOOLEAN | Active flag |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update |

**Uptime Formula:**
```
Uptime % = ((Total Planned Minutes - Maintenance Break) / Total Planned Minutes) × 100
```

---

#### 3. `parameter_health_config` (device-service)
| Column | Type | Description |
|--------|------|-------------|
| id | INT PK | Auto-increment ID |
| device_id | VARCHAR(50) FK | References devices.device_id |
| tenant_id | VARCHAR(50) | Multi-tenant support |
| parameter_name | VARCHAR(100) | Parameter name (e.g., pressure) |
| normal_min | FLOAT | Normal range minimum |
| normal_max | FLOAT | Normal range maximum |
| max_min | FLOAT | Maximum range minimum |
| max_max | FLOAT | Maximum range maximum |
| weight | FLOAT | Weight percentage (0-100) |
| ignore_zero_value | BOOLEAN | Ignore zero values |
| is_active | BOOLEAN | Active flag |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update |

**Health Score Logic:**
- Machine must be RUNNING for health calculation
- Normal Range: Score 70-100%
- Max Range: Score 25-69%
- Beyond Max: Score 0-25%
- Weight must sum to 100%

---

#### 4. `rules` (rule-engine-service)
| Column | Type | Description |
|--------|------|-------------|
| rule_id | VARCHAR(36) PK | UUID |
| tenant_id | VARCHAR(50) | Multi-tenant support |
| rule_name | VARCHAR(255) | Rule name |
| description | TEXT | Description |
| scope | VARCHAR(50) | all_devices / selected_devices |
| property | VARCHAR(100) | Metric to evaluate |
| condition | VARCHAR(20) | >, <, =, !=, >=, <= |
| threshold | FLOAT | Threshold value |
| status | VARCHAR(50) | active/paused/archived |
| notification_channels | JSON | List of channels |
| cooldown_minutes | INT | Cooldown period |
| last_triggered_at | DATETIME | Last trigger time |
| device_ids | JSON | List of device IDs |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update |

---

#### 5. `alerts` (rule-engine-service)
| Column | Type | Description |
|--------|------|-------------|
| alert_id | VARCHAR(36) PK | UUID |
| tenant_id | VARCHAR(50) | Multi-tenant support |
| rule_id | VARCHAR(36) FK | References rules.rule_id |
| device_id | VARCHAR(50) | Device identifier |
| severity | VARCHAR(50) | Alert severity |
| message | TEXT | Alert message |
| actual_value | FLOAT | Actual metric value |
| threshold_value | FLOAT | Threshold that was crossed |
| status | VARCHAR(50) | open/acknowledged/resolved |
| acknowledged_by | VARCHAR(255) | Who acknowledged |
| acknowledged_at | DATETIME | Ack timestamp |
| resolved_at | DATETIME | Resolution timestamp |
| created_at | DATETIME | Creation timestamp |

---

#### 6. `analytics_jobs` (analytics-service)
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) PK | UUID |
| job_id | VARCHAR(100) | Job identifier |
| device_id | VARCHAR(50) | Device ID |
| analysis_type | VARCHAR(50) | Type of analysis |
| model_name | VARCHAR(100) | Model used |
| date_range_start | DATETIME | Start of range |
| date_range_end | DATETIME | End of range |
| parameters | JSON | Analysis parameters |
| status | VARCHAR(50) | Job status |
| progress | FLOAT | Progress percentage |
| results | JSON | Analysis results |
| created_at | DATETIME | Creation timestamp |

---

### InfluxDB Buckets

#### `telemetry`
Time-series data storage for device telemetry.

**Measurement:** `telemetry`

**Tags:**
- device_id
- schema_version
- enrichment_status

**Fields:**
- Dynamic - any numeric fields (pressure, temperature, voltage, etc.)

---

## API Endpoints

### Device Service (Port 8000)

#### Devices
```
GET    /api/v1/devices              - List all devices
POST   /api/v1/devices              - Create device
GET    /api/v1/devices/{device_id}  - Get device
PUT    /api/v1/devices/{device_id}  - Update device
DELETE /api/v1/devices/{device_id}  - Delete device
```

#### Shifts
```
POST   /api/v1/devices/{device_id}/shifts              - Create shift
GET    /api/v1/devices/{device_id}/shifts              - List shifts
GET    /api/v1/devices/{device_id}/shifts/{id}         - Get shift
PUT    /api/v1/devices/{device_id}/shifts/{id}         - Update shift
DELETE /api/v1/devices/{device_id}/shifts/{id}         - Delete shift
GET    /api/v1/devices/{device_id}/uptime              - Get uptime
```

#### Health Configuration
```
POST   /api/v1/devices/{device_id}/health-config                                      - Create config
GET    /api/v1/devices/{device_id}/health-config                                      - List configs
GET    /api/v1/devices/{device_id}/health-config/{id}                                 - Get config
PUT    /api/v1/devices/{device_id}/health-config/{id}                                 - Update config
DELETE /api/v1/devices/{device_id}/health-config/{id}                                 - Delete config
GET    /api/v1/devices/{device_id}/health-config/validate-weights                    - Validate weights
POST   /api/v1/devices/{device_id}/health-config/bulk                                - Bulk create/update
POST   /api/v1/devices/{device_id}/health-score                                      - Calculate health score
```

---

### Data Service (Port 8081)

```
GET  /api/telemetry/{device_id}     - Get telemetry
WS   /ws/telemetry                 - WebSocket for live data
```

---

### Rule Engine Service (Port 8002)

```
GET    /api/v1/rules              - List rules
POST   /api/v1/rules              - Create rule
GET    /api/v1/rules/{rule_id}   - Get rule
PUT    /api/v1/rules/{rule_id}   - Update rule
DELETE /api/v1/rules/{rule_id}   - Delete rule

GET    /api/v1/alerts             - List alerts
PUT    /api/v1/alerts/{id}/ack   - Acknowledge alert
```

---

## Features

### 1. Dynamic Telemetry
- Accepts any numeric parameters without hardcoding
- Stores in InfluxDB with device metadata
- Real-time WebSocket streaming

### 2. Device Health Scoring
- Configurable parameter ranges (Normal + Max)
- Configurable weights (must total 100%)
- Per-parameter efficiency calculation
- Machine state awareness (RUNNING vs Standby)
- Zero value handling

### 3. Uptime Calculation
- Multiple shift support
- Maintenance break handling
- Day-of-week scheduling

### 4. Rule-Based Alerting
- Threshold-based rules
- Multiple conditions (>, <, =, !=, >=, <=)
- Cooldown management
- Multiple notification channels

### 5. Analytics
- Anomaly detection
- Failure prediction
- Energy forecasting

---

## Running the Project

### Prerequisites
- Docker & Docker Compose
- Port availability: 3000, 8000, 8002, 8003, 8080, 8081, 8085, 1883, 3306, 8086, 9000, 9001

### Start Services
```bash
cd /Users/vedanthshetty/Desktop/END-END-PIPLINE/Energy-Enterprise-main
docker-compose up -d
```

### Verify Services
```bash
docker-compose ps
```

### Access Points
| Service | URL |
|---------|-----|
| UI Web | http://localhost:3000 |
| Device Service | http://localhost:8000/docs |
| Data Service | http://localhost:8081/docs |
| Rule Engine | http://localhost:8002/docs |
| InfluxDB | http://localhost:8086 |
| MinIO Console | http://localhost:9001 |
| EMQX Dashboard | http://localhost:18083 |

### Create Test Devices
```bash
curl -s -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{"device_id": "D1", "device_name": "Device 1", "device_type": "sensor", "location": "Building A", "status": "active"}'
```

### Run Simulators
```bash
cd tools/device-simulator
python main.py --device-id D1 --metrics "pressure,temperature,vibration" --interval 3 &
python main.py --device-id D2 --metrics "humidity,voltage,current,frequency,power_factor" --interval 3 &
```

---

## Key Concepts

### Machine States
Health scoring is only active when machine_state = RUNNING. Other states (OFF, IDLE, UNLOAD, POWER CUT) show as "Standby".

### Weight Validation
- All active parameter weights must sum to 100%
- Health score only calculates when total = 100%
- Partial configurations are saved but don't calculate score

### Health Score Formula
```
Raw Score (Normal Range) = 100 - (|value - ideal_center| / half_range) × 30
Raw Score (Warning Range) = 70 - (overshoot / tolerance) × 45
Weighted Score = Raw Score × (Weight / 100)
Health Score = Sum of all Weighted Scores
```

### Telemetry Flow
1. Device publishes to MQTT
2. Data Service receives via MQTT handler
3. Enriches with device metadata from Device Service
4. Stores in InfluxDB
5. Sends to Rule Engine for evaluation
6. WebSocket broadcasts to UI

---

## Default Configurations

### Metric Ranges (for health scoring)
| Parameter | Normal Min | Normal Max | Max Min | Max Max |
|-----------|------------|------------|---------|---------|
| pressure | 2 | 6 | 0 | 10 |
| temperature | 20 | 60 | 0 | 100 |
| vibration | 0 | 3 | 0 | 8 |
| power | 100 | 400 | 0 | 500 |
| voltage | 210 | 240 | 180 | 260 |
| current | 2 | 15 | 0 | 20 |
| frequency | 48 | 52 | 40 | 60 |
| power_factor | 0.85 | 1.0 | 0.5 | 1.0 |
| speed | 1200 | 1800 | 800 | 2200 |
| torque | 50 | 300 | 0 | 500 |
| oil_pressure | 1 | 4 | 0 | 5 |
| humidity | 30 | 70 | 0 | 100 |

---

## Troubleshooting

### Services not starting
```bash
docker-compose logs <service-name>
```

### View all logs
```bash
docker-compose logs -f
```

### Reset everything
```bash
docker-compose down -v
docker-compose up -d
```

---

## Version History

| Date | Changes |
|------|---------|
| 2026-02-22 | Added dynamic health scoring system with configurable weights and ranges |
| 2026-02-22 | Added shift-based uptime calculation |
| 2026-02-22 | Dynamic telemetry support (no hardcoded fields) |
