# Energy Intelligence Platform - Complete Documentation

**Document Version:** 2.0  
**Date:** 2026-02-22  
**Classification:** Internal Handover

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Services Catalog](#services-catalog)
4. [Database Schema](#database-schema)
5. [API Reference](#api-reference)
6. [Device Management](#device-management)
7. [Telemetry System](#telemetry-system)
8. [Health & Rules Engine](#health--rules-engine)
9. [Frontend Integration](#frontend-integration)
10. [Operational Guide](#operational-guide)

---

## 1. System Overview

The **Energy Intelligence Platform** is a distributed microservices architecture for industrial IoT monitoring and analytics. It collects telemetry from devices, stores time-series data, performs health analysis, and provides alerting capabilities.

### Key Features
- Real-time telemetry ingestion via MQTT
- Dynamic device properties discovery
- Health score calculation with configurable parameters
- Rule-based alerting system
- Analytics and reporting
- Data export capabilities

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                                │
│                          Port: 3000 (Development)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        API Gateway / Reverse Proxy                          │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                    │                    │
                    ▼                    ▼                    ▼
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │  Device Service  │  │  Data Service   │  │ Rule Engine      │
        │  Port: 8000     │  │  Port: 8081     │  │ Port: 8002       │
        │  MySQL          │  │  InfluxDB       │  │ MySQL            │
        └──────────────────┘  │  MQTT           │  └──────────────────┘
                             └──────────────────┘
                    │                    │                    │
                    └────────────────────┼────────────────────┘
                                       ▼
        ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
        │Analytics Service │  │Data Export Svc   │  │Reporting Service │
        │  Port: 8003     │  │  Port: 8080     │  │  Port: 8085      │
        └──────────────────┘  └──────────────────┘  └──────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  S3/MinIO       │
                              │  Port: 9000     │
                              └──────────────────┘
```

---

## 3. Services Catalog

### 3.1 Device Service (Port: 8000)

**Purpose:** Manages device registry, metadata, health configurations, and runtime status.

**Technology:** FastAPI, SQLAlchemy (async), MySQL

**Database:** `energy_device_db`

**Configuration:**
```bash
DATABASE_URL=mysql+aiomysql://energy:energy@localhost:3306/energy_device_db
SERVICE_NAME=device-service
```

---

### 3.2 Data Service (Port: 8081)

**Purpose:** Ingests telemetry data from devices via MQTT, stores in InfluxDB.

**Technology:** FastAPI, asyncio, InfluxDB, Paho-MQTT

**Database:** InfluxDB (time-series), MySQL (device metadata cache)

**Configuration:**
```bash
INFLUX_URL=http://influxdb:8086
INFLUX_ORG=energy
INFLUX_BUCKET=telemetry
MQTT_BROKER_URL=mqtt://emqx:1883
DEVICE_SERVICE_URL=http://device-service:8000
```

---

### 3.3 Rule Engine Service (Port: 8002)

**Purpose:** Evaluates rules against incoming telemetry, triggers alerts.

**Technology:** FastAPI, SQLAlchemy, MySQL

**Database:** `energy_rule_db`

**Configuration:**
```bash
DATABASE_URL=mysql+aiomysql://energy:energy@localhost:3306/energy_rule_db
DEVICE_SERVICE_URL=http://device-service:8000
```

---

### 3.4 Analytics Service (Port: 8003)

**Purpose:** ML-based analytics, anomaly detection, predictions.

**Technology:** FastAPI, Scikit-learn, Pandas

**Database:** `energy_analytics_db`

---

### 3.5 Data Export Service (Port: 8080)

**Purpose:** Exports telemetry data to S3/MinIO in various formats.

**Technology:** FastAPI, Boto3

**Database:** `energy_export_db`

---

### 3.6 Reporting Service (Port: 8085)

**Purpose:** Generates scheduled reports.

**Technology:** FastAPI

**Database:** `energy_reporting_db`

---

## 4. Database Schema

### 4.1 MySQL Databases Overview

| Database Name | Service | Purpose |
|--------------|---------|---------|
| `energy_device_db` | device-service | Devices, shifts, health configs, properties |
| `energy_rule_db` | rule-engine-service | Rules, alerts |
| `energy_analytics_db` | analytics-service | Analytics jobs |
| `energy_reporting_db` | reporting-service | Report jobs |
| `energy_export_db` | data-export-service | Export checkpoints |

### 4.2 InfluxDB

| Bucket | Measurement | Purpose |
|--------|-------------|---------|
| `telemetry` | Raw telemetry data | Time-series device data |

---

## 5. API Reference

### 5.1 Device Service APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/devices` | GET | List all devices |
| `/api/v1/devices/{device_id}` | GET | Get device by ID |
| `/api/v1/devices` | POST | Create new device |
| `/api/v1/devices/{device_id}` | PUT | Update device |
| `/api/v1/devices/{device_id}` | DELETE | Delete device |
| `/api/v1/devices/{device_id}/properties` | GET | Get device properties |
| `/api/v1/devices/{device_id}/properties/sync` | POST | Sync properties from telemetry |
| `/api/v1/devices/{device_id}/heartbeat` | POST | Update last_seen_timestamp |
| `/api/v1/devices/{device_id}/health-config` | GET | Get health configurations |
| `/api/v1/devices/{device_id}/health-config` | POST | Create health config |
| `/api/v1/devices/{device_id}/health-config/{id}` | PUT | Update health config |
| `/api/v1/devices/{device_id}/health-config/{id}` | DELETE | Delete health config |
| `/api/v1/devices/{device_id}/shifts` | GET | Get shift configurations |
| `/api/v1/devices/{device_id}/shifts` | POST | Create shift |
| `/api/v1/devices/{device_id}/shifts/{id}` | DELETE | Delete shift |
| `/api/v1/devices/{device_id}/health-score` | POST | Calculate health score |
| `/api/v1/devices/{device_id}/uptime` | GET | Calculate uptime |
| `/api/v1/devices/properties` | GET | Get all devices properties |
| `/api/v1/devices/properties/common` | POST | Get common properties |

---

## 6. Device Management

### 6.1 Device Onboarding

To onboard a new device:

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "D1",
    "device_name": "Device 1 - Pressure Sensor",
    "device_type": "sensor",
    "location": "Building A"
  }'
```

**Device ID:** Unique identifier for the device (alphanumeric, max 50 chars)
- Example: `D1`, `D2`, `COMPRESSOR-001`, `MOTOR-A1`

**Device Type:** Type of industrial equipment
- Example: `sensor`, `motor`, `compressor`, `pump`, `meter`

**Location:** Physical location of the device
- Example: `Building A`, `Floor 2`, `Warehouse 1`

---

### 6.2 Runtime Status System

The platform uses **telemetry-driven runtime status**:

- **RUNNING**: Device has sent telemetry within the last 60 seconds
- **STOPPED**: No telemetry received for more than 60 seconds

**Last Seen Timestamp:** Server-side UTC timestamp when the most recent telemetry was received.

---

## 7. Telemetry System

### 7.1 Telemetry Flow

1. Device sends data via MQTT to EMQX broker
2. Data Service subscribes to MQTT topics
3. Data is enriched with device metadata
4. Stored in InfluxDB (time-series)
5. Device last_seen_timestamp is updated
6. Rule Engine evaluates rules
7. WebSocket pushes to UI (if enabled)

### 7.2 Telemetry Simulator

To simulate device telemetry:

```bash
cd tools/device-simulator
pip install -r requirements.txt
python main.py --device-id D1 --interval 5
```

Options:
- `--device-id`: Device identifier (required)
- `--interval`: Publish interval in seconds (default: 5)
- `--broker`: MQTT broker (default: localhost)
- `--port`: MQTT port (default: 1883)
- `--fault-mode`: Fault injection (none/spike/drop/overheating)

---

## 8. Health & Rules Engine

### 8.1 Health Configuration

Each device can have multiple parameter health configurations:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `parameter_name` | Telemetry field name | `temperature`, `pressure`, `vibration` |
| `normal_min` | Normal operating minimum | 20.0 |
| `normal_max` | Normal operating maximum | 60.0 |
| `max_min` | Absolute minimum | 0.0 |
| `max_max` | Absolute maximum | 100.0 |
| `weight` | Contribution to overall health (must total 100%) | 25.0 |
| `ignore_zero_value` | Skip zero values in calculation | false |
| `is_active` | Enable/disable this parameter | true |

### 8.2 Health Score Calculation

Health score is calculated as weighted average of parameter scores:

```
Parameter Score = (current_value - min) / (max - min) * 100
Health Score = Σ(parameter_score * weight) / Σ(weights)
```

### 8.3 Rules Engine

Rules evaluate telemetry against thresholds:

```json
{
  "rule_name": "High Temperature Alert",
  "property": "temperature",
  "condition": ">",
  "threshold": 80.0,
  "scope": "selected_devices",
  "device_ids": ["D1", "D2"],
  "notification_channels": ["email", "webhook"],
  "cooldown_minutes": 5
}
```

**Conditions:**
- `>` : Greater than
- `<` : Less than
- `>=` : Greater than or equal
- `<=` : Less than or equal
- `==` : Equal
- `!=` : Not equal

---

## 9. Frontend Integration

### 9.1 Pages

| Path | Description |
|------|-------------|
| `/machines` | Device list with status |
| `/machines/{deviceId}` | Device detail dashboard |
| `/rules` | Global rules management |
| `/rules/new` | Create new rule |
| `/analytics` | Analytics dashboard |
| `/settings` | System settings |

### 9.2 API Proxies

Frontend uses Next.js API routes to proxy to backend services:

```
/api/devices     → device-service:8000
/api/telemetry   → data-service:8081
/api/rules       → rule-engine-service:8002
```

---

## 10. Operational Guide

### 10.1 Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d device-service
```

### 10.2 Checking Status

```bash
# Check running containers
docker ps

# Check service logs
docker logs device-service
docker logs data-service
```

### 10.3 Testing

```bash
# Test device service
curl http://localhost:8000/api/v1/devices

# Test telemetry
curl 'http://localhost:8081/api/telemetry/D1?limit=10'

# Test rules
curl http://localhost:8002/api/v1/rules
```

### 10.4 Database Access

```bash
# Connect to MySQL
docker exec -it energy_mysql mysql -uroot -prootpassword

# Connect to InfluxDB
docker exec -it influxdb influx -org energy -bucket telemetry
```

---

## Appendix: Configuration Reference

### Environment Variables

| Service | Variable | Description | Default |
|---------|----------|-------------|---------|
| device-service | DATABASE_URL | MySQL connection | mysql+aiomysql://... |
| data-service | INFLUX_URL | InfluxDB URL | http://influxdb:8086 |
| data-service | MQTT_BROKER_URL | MQTT broker | mqtt://emqx:1883 |
| rule-engine-service | DATABASE_URL | MySQL connection | mysql+aiomysql://... |

### Port Mapping

| Service | Internal Port | External Port |
|---------|--------------|---------------|
| ui-web | 3000 | 3000 |
| device-service | 8000 | 8000 |
| data-service | 8081 | 8081 |
| rule-engine-service | 8002 | 8002 |
| analytics-service | 8003 | 8003 |
| data-export-service | 8080 | 8080 |
| reporting-service | 8085 | 8085 |
| MySQL | 3306 | 3306 |
| InfluxDB | 8086 | 8086 |
| EMQX | 1883 | 1883 |
| MinIO | 9000 | 9000 |

---

**End of Document**
