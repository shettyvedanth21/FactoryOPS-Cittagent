# Energy Intelligence Platform – API, Database & Architecture Handover

**Document Version:** 1.0  
**Date:** 2026-02-12  
**Classification:** Internal Handover

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Service Catalog](#service-catalog)
3. [API Reference](#api-reference)
4. [Database Schemas](#database-schemas)
5. [Domain Concepts](#domain-concepts)
6. [Service Interaction Flow](#service-interaction-flow)
7. [Frontend to API Mapping](#frontend-to-api-mapping)
8. [Appendix: Configuration Reference](#appendix-configuration-reference)

---

## System Overview

The Energy Intelligence Platform is a distributed microservices architecture for industrial IoT monitoring and analytics. It collects telemetry from devices, stores time-series data, performs ML-based analytics, and provides alerting capabilities.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                              │
│                        Port: 3000 (Development)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY / Reverse Proxy                        │
│                      (Next.js Rewrites / Nginx)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  Device Service     │    │  Data Service       │    │  Rule Engine        │
│  Port: 8000         │    │  Port: 8081         │    │  Port: 8002         │
│  MySQL         │    │  InfluxDB (TS)      │    │  MySQL         │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                           │                           │
           │                           ▼                           │
           │                  ┌─────────────────────┐              │
           │                  │  MQTT Broker        │              │
           │                  │  Port: 1883         │              │
           │                  └─────────────────────┘              │
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  Analytics Service  │    │  Data Export Svc    │    │  Reporting Service  │
│  Port: 8003         │    │  Port: 8080         │    │  Port: 8085         │
│  MySQL         │    │  MySQL         │    │  MySQL + S3    │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       ▼
                              ┌─────────────────────┐
                              │  S3/MinIO Storage   │
                              │  Port: 9000         │
                              └─────────────────────┘
```

---

## Service Catalog

### 1. Device Service

**Source:** `/services/device-service/`

#### Purpose
The Device Service manages the device registry and metadata. It provides CRUD operations for industrial machines/devices and serves as the authoritative source for device information across the platform. Devices represent physical industrial equipment (compressors, motors, pumps, etc.) that emit telemetry data.

#### Runtime Details

| Property | Value |
|----------|-------|
| Port | 8000 |
| Framework | FastAPI 0.109.0 |
| Database | MySQL 15+ |
| ORM | SQLAlchemy 2.0.25 (async) |
| Python Version | 3.11+ |

#### Dependencies
- **MySQL**: Stores device metadata and configuration

#### Configuration
```bash
DATABASE_URL=mysql+aiomysql://energy:energy@localhost:3306/energy_device_db
SERVICE_NAME=device-service
```

---

### 2. Data Service

**Source:** `/services/data-service/`

#### Purpose
The Data Service is the primary telemetry ingestion and query service. It subscribes to MQTT topics for real-time telemetry, validates and enriches data with device metadata, persists to InfluxDB, and triggers rule evaluations. It also provides WebSocket support for live telemetry streaming.

#### Runtime Details

| Property | Value |
|----------|-------|
| Port | 8081 |
| Framework | FastAPI 0.104.1 |
| Time-Series DB | InfluxDB |
| MQTT Client | paho-mqtt 1.6.1 |
| Python Version | 3.11+ |

#### Dependencies
- **MQTT Broker**: Receives telemetry from devices (port 1883)
- **InfluxDB**: Stores time-series telemetry data (port 8086)
- **Device Service**: Enriches telemetry with device metadata (port 8000)
- **Rule Engine**: Triggers rule evaluation (port 8002)

#### Configuration
```bash
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_TOPIC=devices/+/telemetry
INFLUXDB_URL=http://localhost:8086
INFLUXDB_BUCKET=telemetry
DEVICE_SERVICE_URL=http://device-service:8080
RULE_ENGINE_URL=http://rule-engine:8082
```

---

### 3. Rule Engine Service

**Source:** `/services/rule-engine-service/`

#### Purpose
The Rule Engine Service manages monitoring rules and evaluates telemetry against thresholds. When a rule is triggered, it creates alerts and sends notifications. Rules can target specific devices or all devices, with support for cooldown periods to prevent alert spam.

#### Runtime Details

| Property | Value |
|----------|-------|
| Port | 8002 |
| Framework | FastAPI 0.109.0 |
| Database | MySQL 15+ |
| ORM | SQLAlchemy 2.0.25 (async) |
| Python Version | 3.11+ |

#### Dependencies
- **MySQL**: Stores rules and alerts

#### Configuration
```bash
DATABASE_URL=mysql+aiomysql://energy:energy@localhost:3306/energy_rule_db
RULE_EVALUATION_TIMEOUT=5
NOTIFICATION_COOLDOWN_MINUTES=15
MAX_RULES_PER_DEVICE=100
```

---

### 4. Analytics Service

**Source:** `/services/analytics-service/`

#### Purpose
The Analytics Service provides ML-based analytics capabilities including anomaly detection, failure prediction, and time-series forecasting. It operates as an asynchronous job processor, reading datasets from S3 and persisting results to MySQL.

#### Runtime Details

| Property | Value |
|----------|-------|
| Port | 8003 |
| Framework | FastAPI 0.109.0 |
| Database | MySQL 15+ |
| ML Libraries | scikit-learn, prophet, pandas, numpy |
| Python Version | 3.11+ |

#### Dependencies
- **MySQL**: Stores job metadata and results
- **S3/MinIO**: Reads datasets for analysis

#### Configuration
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=energy_analytics_db
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=energy-platform-datasets
MAX_CONCURRENT_JOBS=3
JOB_TIMEOUT_SECONDS=3600
```

---

### 5. Data Export Service

**Source:** `/services/data-export-service/`

#### Purpose
The Data Export Service continuously exports telemetry data from InfluxDB to S3 in Parquet format. It maintains checkpoint tracking to ensure idempotent exports and supports both scheduled and on-demand exports. The exported datasets are used by the Analytics Service for ML processing.

#### Runtime Details

| Property | Value |
|----------|-------|
| Port | 8080 |
| Framework | FastAPI 0.109.0 |
| Checkpoint DB | MySQL |
| Export Format | Parquet (Snappy compression) |
| Python Version | 3.11+ |

#### Dependencies
- **InfluxDB**: Source telemetry data
- **MySQL**: Checkpoint storage for export progress
- **S3/MinIO**: Destination for exported datasets

#### Configuration
```bash
INFLUXDB_URL=http://localhost:8086
INFLUXDB_BUCKET=telemetry
CHECKPOINT_DB_HOST=localhost
CHECKPOINT_DB_NAME=energy_export_db
S3_BUCKET=energy-platform-datasets
EXPORT_INTERVAL_SECONDS=60
EXPORT_BATCH_SIZE=1000
LOOKBACK_HOURS=1
MAX_EXPORT_WINDOW_HOURS=24
```

---

### 6. Reporting Service

**Source:** `/services/reporting-service/`

#### Purpose
The Reporting Service generates downloadable reports (PDF, Excel, JSON) from analytics results and telemetry datasets. It provides asynchronous report generation with status tracking and presigned URL downloads.

#### Runtime Details

| Property | Value |
|----------|-------|
| Port | 8085 |
| Framework | FastAPI 0.104.1 |
| Database | MySQL |
| Report Formats | PDF, Excel, JSON |
| Python Version | 3.11+ |

#### Dependencies
- **MySQL**: Reads analytics results
- **S3**: Reads datasets and stores generated reports

#### Configuration
```bash
MYSQL_HOST=localhost
MYSQL_DATABASE=energy_reporting_db
S3_BUCKET_NAME=energy-platform-datasets
MAX_REPORT_SIZE_MB=100
REPORT_TIMEOUT_SECONDS=300
```

---

## API Reference

### Device Service APIs

#### GET /health
- **Handler:** `health_check()`
- **Source:** `main.py`
- **Description:** Kubernetes liveness probe
- **Response:** `{"status": "healthy", "version": "1.0.0"}`

#### GET /ready
- **Handler:** `readiness_check()`
- **Source:** `main.py`
- **Description:** Kubernetes readiness probe with DB check
- **Response:** `{"ready": true, "checks": {"database": "connected"}}`

#### GET /api/v1/devices
- **Handler:** `list_devices()`
- **Source:** `app/api/v1/devices.py`
- **Description:** List all devices with pagination and filtering
- **Query Params:**
  - `tenant_id` (optional): Multi-tenant filter
  - `device_type` (optional): Filter by device type
  - `status` (optional): Filter by status
  - `page` (default: 1): Page number
  - `page_size` (default: 20, max: 100): Items per page
- **Response:**
```json
{
  "success": true,
  "data": [
    {
      "device_id": "D1",
      "device_name": "Compressor A",
      "device_type": "compressor",
      "status": "active",
      "location": "Building A",
      "created_at": "2026-02-07T23:20:30Z",
      "updated_at": "2026-02-07T23:20:30Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

#### GET /api/v1/devices/{device_id}
- **Handler:** `get_device()`
- **Source:** `app/api/v1/devices.py`
- **Description:** Get a single device by ID
- **Path Params:**
  - `device_id`: Device identifier (e.g., "D1")
- **Response:**
```json
{
  "success": true,
  "data": {
    "device_id": "D1",
    "device_name": "Compressor A",
    "device_type": "compressor",
    "status": "active",
    "location": "Building A",
    "manufacturer": "Acme Corp",
    "model": "XJ-9000",
    "metadata_json": "{}",
    "created_at": "2026-02-07T23:20:30Z",
    "updated_at": "2026-02-07T23:20:30Z"
  }
}
```

#### POST /api/v1/devices
- **Handler:** `create_device()`
- **Source:** `app/api/v1/devices.py`
- **Description:** Create a new device
- **Body:**
```json
{
  "device_id": "D2",
  "device_name": "Motor B",
  "device_type": "motor",
  "status": "active",
  "location": "Building B",
  "manufacturer": "Industrial Co",
  "model": "M-2000"
}
```
- **Response:** 201 Created

#### PUT /api/v1/devices/{device_id}
- **Handler:** `update_device()`
- **Source:** `app/api/v1/devices.py`
- **Description:** Update an existing device
- **Path Params:**
  - `device_id`: Device identifier
- **Body:** Partial device fields
- **Response:** 200 OK

#### DELETE /api/v1/devices/{device_id}
- **Handler:** `delete_device()`
- **Source:** `app/api/v1/devices.py`
- **Description:** Delete a device (soft delete by default)
- **Path Params:**
  - `device_id`: Device identifier
- **Query Params:**
  - `soft` (default: true): Use soft delete
- **Response:** 204 No Content

---

### Data Service APIs

#### GET /api/v1/data/health
- **Handler:** `health_check()`
- **Source:** `src/api/routes.py`
- **Description:** Health check with version and connection status

#### GET /api/v1/data/telemetry/{device_id}
- **Handler:** `get_telemetry()`
- **Source:** `src/api/telemetry.py`
- **Description:** Query telemetry data for a device
- **Path Params:**
  - `device_id`: Device identifier
- **Query Params:**
  - `start_time` (optional): ISO timestamp
  - `end_time` (optional): ISO timestamp
  - `fields` (optional): Comma-separated field names
  - `aggregate` (optional): Aggregation function (mean, sum, etc.)
  - `interval` (optional): Aggregation interval (1h, 5m)
  - `limit` (default: 1000, max: 10000): Max results
- **Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "timestamp": "2026-02-12T10:00:00Z",
        "device_id": "D1",
        "voltage": 230.5,
        "current": 1.2,
        "power": 276.6,
        "temperature": 45.2,
        "schema_version": "v1",
        "enrichment_status": "success"
      }
    ]
  }
}
```

#### GET /api/v1/data/stats/{device_id}
- **Handler:** `get_stats()`
- **Source:** `src/api/routes.py`
- **Description:** Get aggregated statistics for a device
- **Path Params:**
  - `device_id`: Device identifier
- **Response:**
```json
{
  "success": true,
  "data": {
    "device_id": "D1",
    "start_time": "2026-02-12T00:00:00Z",
    "end_time": "2026-02-12T23:59:59Z",
    "voltage_min": 220.0,
    "voltage_max": 240.0,
    "voltage_avg": 230.5,
    "current_min": 0.5,
    "current_max": 2.0,
    "current_avg": 1.2,
    "power_min": 100.0,
    "power_max": 500.0,
    "power_avg": 276.6,
    "power_total": 10000.0,
    "temperature_min": 30.0,
    "temperature_max": 60.0,
    "temperature_avg": 45.2,
    "data_points": 1440
  }
}
```

#### POST /api/v1/data/query
- **Handler:** `custom_query()`
- **Source:** `src/api/routes.py`
- **Description:** Custom telemetry query with body parameters
- **Body:** Query parameters

#### WS /ws/telemetry/{device_id}
- **Handler:** `telemetry_websocket()`
- **Source:** `src/api/websocket.py`
- **Description:** WebSocket connection for live telemetry stream
- **Path Params:**
  - `device_id`: Device identifier

---

### Rule Engine Service APIs

#### GET /health
- **Handler:** `health_check()`
- **Source:** `app/__init__.py`
- **Description:** Health check endpoint

#### GET /ready
- **Handler:** `readiness_check()`
- **Source:** `app/__init__.py`
- **Description:** Readiness check with DB verification

#### GET /api/v1/rules
- **Handler:** `list_rules()`
- **Source:** `app/api/v1/rules.py`
- **Description:** List all rules with filtering and pagination
- **Query Params:**
  - `device_id` (optional): Filter by device
  - `status` (optional): Filter by status (active, paused, archived)
  - `page` (default: 1): Page number
  - `page_size` (default: 20): Items per page
- **Response:**
```json
{
  "success": true,
  "data": [
    {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "rule_name": "High Temperature Alert",
      "scope": "selected_devices",
      "device_ids": ["D1"],
      "property": "temperature",
      "condition": ">",
      "threshold": 60.0,
      "status": "active",
      "notification_channels": ["email", "whatsapp"],
      "cooldown_minutes": 15,
      "last_triggered_at": "2026-02-12T10:00:00Z",
      "created_at": "2026-02-07T23:20:30Z",
      "updated_at": "2026-02-07T23:20:30Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

#### GET /api/v1/rules/{rule_id}
- **Handler:** `get_rule()`
- **Source:** `app/api/v1/rules.py`
- **Description:** Get a single rule by ID
- **Path Params:**
  - `rule_id`: UUID of the rule

#### POST /api/v1/rules
- **Handler:** `create_rule()`
- **Source:** `app/api/v1/rules.py`
- **Description:** Create a new monitoring rule
- **Body:**
```json
{
  "rule_name": "High Temperature Alert",
  "description": "Alert when temperature exceeds threshold",
  "scope": "selected_devices",
  "device_ids": ["D1"],
  "property": "temperature",
  "condition": ">",
  "threshold": 60.0,
  "notification_channels": ["email", "whatsapp"],
  "cooldown_minutes": 15
}
```
- **Response:** 201 Created

#### PUT /api/v1/rules/{rule_id}
- **Handler:** `update_rule()`
- **Source:** `app/api/v1/rules.py`
- **Description:** Update an existing rule
- **Path Params:**
  - `rule_id`: UUID of the rule

#### PATCH /api/v1/rules/{rule_id}/status
- **Handler:** `update_rule_status()`
- **Source:** `app/api/v1/rules.py`
- **Description:** Pause, resume, or archive a rule
- **Path Params:**
  - `rule_id`: UUID of the rule
- **Body:**
```json
{
  "status": "paused"
}
```

#### DELETE /api/v1/rules/{rule_id}
- **Handler:** `delete_rule()`
- **Source:** `app/api/v1/rules.py`
- **Description:** Delete a rule (soft delete)
- **Path Params:**
  - `rule_id`: UUID of the rule

#### POST /api/v1/rules/evaluate
- **Handler:** `evaluate_rules()`
- **Source:** `app/api/v1/rules.py`
- **Description:** Evaluate telemetry against all applicable rules
- **Body:**
```json
{
  "device_id": "D1",
  "timestamp": "2026-02-12T10:00:00Z",
  "voltage": 230.5,
  "current": 1.2,
  "power": 276.6,
  "temperature": 65.0,
  "schema_version": "v1"
}
```
- **Response:**
```json
{
  "success": true,
  "data": {
    "evaluated": 5,
    "triggered": 1,
    "results": [
      {
        "rule_id": "550e8400-e29b-41d4-a716-446655440000",
        "triggered": true,
        "alert_id": "660e8400-e29b-41d4-a716-446655440001"
      }
    ]
  }
}
```

#### GET /api/v1/alerts
- **Handler:** `list_alerts()`
- **Source:** `app/api/v1/alerts.py`
- **Description:** List alerts with filtering
- **Query Params:**
  - `device_id` (optional): Filter by device
  - `status` (optional): Filter by status (open, acknowledged, resolved)
  - `page` (default: 1): Page number
  - `page_size` (default: 20): Items per page
- **Response:**
```json
{
  "success": true,
  "data": [
    {
      "alert_id": "660e8400-e29b-41d4-a716-446655440001",
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "device_id": "D1",
      "severity": "high",
      "message": "Temperature exceeded threshold: 65.0 > 60.0",
      "actual_value": 65.0,
      "threshold_value": 60.0,
      "status": "open",
      "acknowledged_by": null,
      "acknowledged_at": null,
      "resolved_at": null,
      "created_at": "2026-02-12T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

#### PATCH /api/v1/alerts/{alert_id}/acknowledge
- **Handler:** `acknowledge_alert()`
- **Source:** `app/api/v1/alerts.py`
- **Description:** Acknowledge an alert
- **Path Params:**
  - `alert_id`: UUID of the alert
- **Body:**
```json
{
  "acknowledged_by": "user@example.com"
}
```

#### PATCH /api/v1/alerts/{alert_id}/resolve
- **Handler:** `resolve_alert()`
- **Source:** `app/api/v1/alerts.py`
- **Description:** Resolve an alert
- **Path Params:**
  - `alert_id`: UUID of the alert

---

### Analytics Service APIs

#### GET /health/live
- **Handler:** `liveness_probe()`
- **Source:** `src/api/routes/health.py`
- **Description:** Kubernetes liveness probe

#### GET /health/ready
- **Handler:** `readiness_probe()`
- **Source:** `src/api/routes/health.py`
- **Description:** Kubernetes readiness probe (checks DB, S3, Worker)

#### GET /api/v1/analytics/models
- **Handler:** `get_supported_models()`
- **Source:** `src/api/routes/analytics.py`
- **Description:** List supported ML models by type
- **Response:**
```json
{
  "anomaly_detection": ["isolation_forest", "autoencoder"],
  "failure_prediction": ["random_forest", "gradient_boosting"],
  "forecasting": ["prophet", "arima"]
}
```

#### GET /api/v1/analytics/datasets
- **Handler:** `list_datasets()`
- **Source:** `src/api/routes/analytics.py`
- **Description:** List available S3 datasets for a device
- **Query Params:**
  - `device_id`: Device identifier
- **Response:**
```json
{
  "device_id": "D1",
  "datasets": [
    {
      "key": "datasets/D1/20260201_20260212.parquet",
      "size": 1048576,
      "last_modified": "2026-02-12T10:00:00Z"
    }
  ]
}
```

#### POST /api/v1/analytics/run
- **Handler:** `run_analytics()`
- **Source:** `src/api/routes/analytics.py`
- **Description:** Submit a new analytics job
- **Body:**
```json
{
  "device_id": "D1",
  "analysis_type": "anomaly",
  "model_name": "isolation_forest",
  "dataset_key": "datasets/D1/20260201_20260212.parquet"
}
```
- **Response:** 202 Accepted
```json
{
  "job_id": "job-abc123",
  "status": "pending"
}
```

#### GET /api/v1/analytics/status/{job_id}
- **Handler:** `get_job_status()`
- **Source:** `src/api/routes/analytics.py`
- **Description:** Get job status and progress
- **Path Params:**
  - `job_id`: Job identifier
- **Response:**
```json
{
  "job_id": "job-abc123",
  "device_id": "D1",
  "analysis_type": "anomaly",
  "model_name": "isolation_forest",
  "status": "running",
  "progress": 65.5,
  "message": "Training model..."
}
```

#### GET /api/v1/analytics/results/{job_id}
- **Handler:** `get_analytics_results()`
- **Source:** `src/api/routes/analytics.py`
- **Description:** Retrieve completed job results
- **Path Params:**
  - `job_id`: Job identifier
- **Response:**
```json
{
  "job_id": "job-abc123",
  "device_id": "D1",
  "analysis_type": "anomaly",
  "model_name": "isolation_forest",
  "status": "completed",
  "results": {
    "anomalies": [
      {
        "timestamp": "2026-02-12T10:00:00Z",
        "value": 85.5,
        "is_anomaly": true,
        "anomaly_score": 0.85
      }
    ]
  },
  "accuracy_metrics": {
    "precision": 0.92,
    "recall": 0.88,
    "f1_score": 0.90
  },
  "execution_time_seconds": 120
}
```

#### GET /api/v1/analytics/jobs
- **Handler:** `list_jobs()`
- **Source:** `src/api/routes/analytics.py`
- **Description:** List jobs with filtering
- **Query Params:**
  - `status` (optional): Filter by status
  - `device_id` (optional): Filter by device
  - `limit` (default: 20): Max results
  - `offset` (default: 0): Pagination offset

---

### Data Export Service APIs

#### GET /health
- **Handler:** `health_check()`
- **Source:** `main.py`
- **Description:** Liveness probe

#### GET /ready
- **Handler:** `readiness_check()`
- **Source:** `main.py`
- **Description:** Readiness probe with worker and S3 checks

#### POST /api/v1/exports/run
- **Handler:** `run_export()`
- **Source:** `main.py`
- **Description:** Trigger on-demand export for a device
- **Body:**
```json
{
  "device_id": "D1"
}
```
- **Response:**
```json
{
  "device_id": "D1",
  "status": "started"
}
```

#### GET /api/v1/exports/status/{device_id}
- **Handler:** `get_export_status()`
- **Source:** `main.py`
- **Description:** Get export status for a device
- **Path Params:**
  - `device_id`: Device identifier
- **Response:**
```json
{
  "device_id": "D1",
  "status": "completed",
  "last_exported_at": "2026-02-12T10:00:00Z",
  "record_count": 10000,
  "s3_key": "datasets/D1/20260201_20260212.parquet"
}
```

---

### Reporting Service APIs

#### GET /
- **Handler:** `root()`
- **Source:** `src/main.py`
- **Description:** Service info

#### GET /health
- **Handler:** `health_check()`
- **Source:** `src/handlers/health.py`
- **Description:** Health check with DB status

#### GET /ready
- **Handler:** `readiness_check()`
- **Source:** `src/handlers/health.py`
- **Description:** Readiness probe

#### POST /api/reports/generate
- **Handler:** `generate_report()`
- **Source:** `src/handlers/reports.py`
- **Description:** Queue a new report generation job
- **Body:**
```json
{
  "device_id": "D1",
  "analysis_types": ["anomaly", "forecast"],
  "date_range_start": "2026-02-01T00:00:00Z",
  "date_range_end": "2026-02-12T23:59:59Z",
  "format": "pdf"
}
```
- **Response:** 202 Accepted
```json
{
  "job_id": "report-abc123",
  "status": "pending"
}
```

#### GET /api/reports/status/{job_id}
- **Handler:** `get_report_status()`
- **Source:** `src/handlers/reports.py`
- **Description:** Check report generation status
- **Path Params:**
  - `job_id`: Report job identifier

#### GET /api/reports/download/{job_id}
- **Handler:** `download_report()`
- **Source:** `src/handlers/reports.py`
- **Description:** Get presigned download URL for completed report
- **Path Params:**
  - `job_id`: Report job identifier
- **Response:**
```json
{
  "job_id": "report-abc123",
  "download_url": "https://s3.amazonaws.com/...",
  "expires_at": "2026-02-12T11:00:00Z"
}
```

---

## Database Schemas

### MySQL Database (Shared)

Each MySQL-backed service owns an isolated database (`energy_device_db`, `energy_rule_db`, `energy_analytics_db`, `energy_export_db`, `energy_reporting_db`).

---

### Device Service Tables

#### Table: `devices`
**Source:** `device-service/app/models/device.py`

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `device_id` | VARCHAR(50) | NO | PRIMARY KEY | Unique device identifier (business key) |
| `tenant_id` | VARCHAR(50) | YES | INDEX | Multi-tenant support |
| `device_name` | VARCHAR(255) | NO | | Human-readable name |
| `device_type` | VARCHAR(100) | NO | INDEX | Device category |
| `manufacturer` | VARCHAR(255) | YES | | Device manufacturer |
| `model` | VARCHAR(255) | YES | | Device model |
| `location` | VARCHAR(500) | YES | | Physical location |
| `status` | VARCHAR(50) | NO | INDEX | active, inactive, maintenance, error |
| `metadata_json` | TEXT | YES | | Extended metadata as JSON |
| `created_at` | TIMESTAMP(tz) | NO | | Creation timestamp |
| `updated_at` | TIMESTAMP(tz) | NO | | Last update timestamp |
| `deleted_at` | TIMESTAMP(tz) | YES | | Soft delete timestamp |

**Indexes:**
- `ix_devices_device_type` on `device_type`
- `ix_devices_status` on `status`
- `ix_devices_tenant_id` on `tenant_id`

---

### Rule Engine Service Tables

#### Table: `rules`
**Source:** `rule-engine-service/app/models/rule.py`

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `rule_id` | UUID | NO | PRIMARY KEY | Unique rule identifier |
| `tenant_id` | VARCHAR(50) | YES | INDEX | Multi-tenancy support |
| `rule_name` | VARCHAR(255) | NO | | Human-readable name |
| `description` | TEXT | YES | | Rule description |
| `scope` | VARCHAR(50) | NO | | 'all_devices' or 'selected_devices' |
| `device_ids` | JSON(VARCHAR(50)) | NO | | List of device IDs |
| `property` | VARCHAR(100) | NO | INDEX | Property to monitor |
| `condition` | VARCHAR(20) | NO | | Operator: >, <, =, !=, >=, <= |
| `threshold` | FLOAT | NO | | Threshold value |
| `status` | VARCHAR(50) | NO | INDEX | active, paused, archived |
| `notification_channels` | JSON(VARCHAR(50)) | NO | | Channels for alerts |
| `cooldown_minutes` | INTEGER | NO | DEFAULT 15 | Cooldown between triggers |
| `last_triggered_at` | TIMESTAMP(tz) | YES | | Last trigger time |
| `created_at` | TIMESTAMP(tz) | NO | | Creation timestamp |
| `updated_at` | TIMESTAMP(tz) | NO | | Update timestamp |
| `deleted_at` | TIMESTAMP(tz) | YES | | Soft delete timestamp |

**Indexes:**
- `ix_rules_property` on `property`
- `ix_rules_status` on `status`
- `ix_rules_tenant_id` on `tenant_id`

#### Table: `alerts`
**Source:** `rule-engine-service/app/models/rule.py`

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `alert_id` | UUID | NO | PRIMARY KEY | Unique alert identifier |
| `tenant_id` | VARCHAR(50) | YES | INDEX | Multi-tenancy support |
| `rule_id` | UUID | NO | FOREIGN KEY → rules.rule_id, ON DELETE CASCADE | Linked rule |
| `device_id` | VARCHAR(50) | NO | INDEX | Device that triggered |
| `severity` | VARCHAR(50) | NO | | Severity level |
| `message` | TEXT | NO | | Alert message |
| `actual_value` | FLOAT | NO | | Actual value read |
| `threshold_value` | FLOAT | NO | | Threshold breached |
| `status` | VARCHAR(50) | NO | DEFAULT 'open', INDEX | open, acknowledged, resolved |
| `acknowledged_by` | VARCHAR(255) | YES | | User who acknowledged |
| `acknowledged_at` | TIMESTAMP(tz) | YES | | Acknowledgment time |
| `resolved_at` | TIMESTAMP(tz) | YES | | Resolution time |
| `created_at` | TIMESTAMP(tz) | NO | | Creation timestamp |

**Indexes:**
- `ix_alerts_device_id` on `device_id`
- `ix_alerts_rule_id` on `rule_id`
- `ix_alerts_status` on `status`
- `ix_alerts_tenant_id` on `tenant_id`

**Relationships:**
- `alerts.rule_id` → `rules.rule_id` (Many-to-One)
- One rule can have many alerts

---

### Analytics Service Tables

#### Table: `analytics_jobs`
**Source:** `analytics-service/src/models/database.py`

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | UUID | NO | PRIMARY KEY, auto-generated | Internal ID |
| `job_id` | VARCHAR(100) | NO | UNIQUE, INDEX | External job identifier |
| `device_id` | VARCHAR(50) | NO | INDEX | Device being analyzed |
| `analysis_type` | VARCHAR(50) | NO | | anomaly, prediction, forecast |
| `model_name` | VARCHAR(100) | NO | | ML model used |
| `date_range_start` | TIMESTAMP(tz) | NO | | Analysis start |
| `date_range_end` | TIMESTAMP(tz) | NO | | Analysis end |
| `parameters` | JSON | YES | | Model parameters |
| `status` | VARCHAR(50) | NO | DEFAULT 'pending' | Job status |
| `progress` | FLOAT | YES | | Progress percentage (0-100) |
| `message` | TEXT | YES | | Status message |
| `error_message` | TEXT | YES | | Error details |
| `results` | JSON | YES | | Analysis results |
| `accuracy_metrics` | JSON | YES | | Performance metrics |
| `execution_time_seconds` | INTEGER | YES | | Runtime |
| `created_at` | TIMESTAMP(tz) | NO | DEFAULT now() | Creation timestamp |
| `started_at` | TIMESTAMP(tz) | YES | | Start timestamp |
| `completed_at` | TIMESTAMP(tz) | YES | | Completion timestamp |
| `updated_at` | TIMESTAMP(tz) | NO | DEFAULT now() | Last update |

**Indexes:**
- `idx_analytics_jobs_status` on `status`
- `idx_analytics_jobs_created_at` on `created_at`

---

### Data Export Service Tables

#### Table: `export_checkpoints`
**Source:** `data-export-service/checkpoint.py`

| Column | Type | Nullable | Constraints | Description |
|--------|------|----------|-------------|-------------|
| `id` | SERIAL | NO | PRIMARY KEY | Checkpoint ID |
| `device_id` | VARCHAR(50) | NO | INDEX | Device identifier |
| `last_exported_at` | TIMESTAMP(tz) | NO | | Last successful export time |
| `last_sequence` | INTEGER | NO | DEFAULT 0 | Sequence number |
| `status` | VARCHAR(50) | NO | INDEX | PENDING, IN_PROGRESS, COMPLETED, FAILED |
| `s3_key` | VARCHAR(500) | YES | | S3 key of exported file |
| `record_count` | INTEGER | NO | DEFAULT 0 | Records exported |
| `error_message` | TEXT | YES | | Error details if failed |
| `created_at` | TIMESTAMP(tz) | NO | DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP(tz) | NO | DEFAULT now() | Last update |

**Indexes:**
- `idx_checkpoint_device_id` on `device_id`
- `idx_checkpoint_status` on `status`
- `idx_checkpoint_updated` on `updated_at`

**Constraints:**
- UNIQUE(device_id, last_exported_at)

---

### Reporting Service Tables

#### Table: `analytics_results`
**Source:** `reporting-service/src/repositories/analytics_repository.py`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | SERIAL | NO | Primary key |
| `job_id` | VARCHAR | NO | Analytics job identifier |
| `device_id` | VARCHAR | NO | Device identifier |
| `analysis_type` | VARCHAR | NO | anomaly, prediction, forecast |
| `model_name` | VARCHAR | NO | ML model name |
| `date_range_start` | TIMESTAMP | NO | Analysis start |
| `date_range_end` | TIMESTAMP | NO | Analysis end |
| `results` | JSON | YES | Analysis results |
| `accuracy_metrics` | JSON | YES | Model accuracy |
| `status` | VARCHAR | NO | completed, pending, etc. |
| `created_at` | TIMESTAMP | NO | Creation timestamp |
| `completed_at` | TIMESTAMP | YES | Completion timestamp |

---

### InfluxDB Schema (Data Service)

#### Measurement: `device_telemetry`
**Source:** `data-service/src/repositories/influxdb_repository.py`

**Tags:**
- `device_id` (string): Device identifier
- `schema_version` (string): Schema version (default: "v1")
- `enrichment_status` (string): pending, success, failed, timeout, skipped
- `device_type` (string): From device metadata
- `location` (string): From device metadata

**Fields:**
- `voltage` (float): Voltage in V (200-250)
- `current` (float): Current in A (0-2)
- `power` (float): Power in W (0-500)
- `temperature` (float): Temperature in °C (20-80)

**Timestamp:** Measurement timestamp

**Retention Policy:** Configured in InfluxDB

---

## Domain Concepts

### Device ID

A `device_id` is a unique string identifier (e.g., "D1", "COMPRESSOR_A") that represents a physical industrial machine or sensor in the platform. It serves as the primary key for device records and is used throughout the system to associate telemetry, rules, analytics, and alerts with specific equipment.

**Key characteristics:**
- String format, max 50 characters
- Business-defined identifier (not auto-generated)
- Immutable once created
- Used across all services for cross-referencing

### Dataset

A `dataset` is a Parquet file stored in S3 containing exported telemetry data for a specific device over a time range. Datasets are created by the Data Export Service and consumed by the Analytics Service for ML processing.

**Key characteristics:**
- Format: Parquet with Snappy compression
- Storage: S3 (or MinIO for local dev)
- Path pattern: `datasets/{device_id}/{start_date}_{end_date}.parquet`
- Columns: timestamp, device_id, device_type, location, voltage, current, power, temperature, hour, day_of_week, is_weekend, power_factor
- Created: By Data Export Service from InfluxDB
- Consumed: By Analytics Service for ML jobs

### Analytics Job

An `analytics job` is an asynchronous ML processing task submitted to the Analytics Service. It performs one of three analysis types (anomaly detection, failure prediction, or forecasting) on a device's dataset.

**Key characteristics:**
- Job ID: Unique identifier (e.g., "job-abc123")
- Types: anomaly, prediction, forecast
- Models: Configurable (isolation_forest, prophet, etc.)
- Status lifecycle: pending → running → completed/failed
- Results: Stored in MySQL as JSON
- Progress: Tracked with percentage (0-100)

### Export Job

An `export job` represents the process of exporting telemetry data from InfluxDB to S3. The Data Export Service maintains checkpoints to track progress and ensure idempotent operations.

**Key characteristics:**
- Triggered: Scheduled (every 60s) or on-demand via API
- Checkpoint: Tracks last exported timestamp per device
- Format: Parquet with computed features
- Status: PENDING, IN_PROGRESS, COMPLETED, FAILED
- Resumable: Can resume from last checkpoint

### Telemetry

`Telemetry` refers to time-series sensor data emitted by devices. It includes electrical measurements (voltage, current, power) and environmental readings (temperature).

**Key characteristics:**
- Source: MQTT topics (`devices/+/telemetry`)
- Storage: InfluxDB (time-series database)
- Fields: voltage, current, power, temperature
- Validation: Range-checked (e.g., voltage 200-250V)
- Enrichment: Augmented with device metadata
- Processing: Triggers rule evaluation, stored in InfluxDB, exported to S3

### Anomaly Job

An `anomaly job` is a type of analytics job that identifies unusual patterns in device telemetry. It uses unsupervised ML algorithms to flag data points that deviate from normal behavior.

**Key characteristics:**
- Analysis type: "anomaly"
- Models: isolation_forest, autoencoder
- Output: Boolean is_anomaly flag, anomaly_score (0-1)
- Use case: Detect equipment malfunctions, unusual power consumption

### Failure Prediction Job

A `failure prediction job` is a type of analytics job that predicts the likelihood of equipment failure based on historical telemetry patterns. It uses supervised classification models.

**Key characteristics:**
- Analysis type: "prediction"
- Models: random_forest, gradient_boosting
- Output: Failure probability (0-1)
- Use case: Predictive maintenance scheduling

### Forecast Job

A `forecast job` is a type of analytics job that predicts future telemetry values using time-series forecasting models.

**Key characteristics:**
- Analysis type: "forecast"
- Models: prophet, arima
- Output: Forecasted values with confidence bounds
- Use case: Capacity planning, energy consumption prediction

---

## Service Interaction Flow

### 1. Telemetry Flow (Ingestion to Storage)

```
┌──────────┐     MQTT      ┌─────────────┐     HTTP      ┌──────────────┐
│  Device  │ ─────────────> │ Data Service│ ────────────> │ Rule Engine  │
│ (Sensor) │   (telemetry)  │             │  (evaluate)   │              │
└──────────┘                │             │               └──────────────┘
                            │             │                      │
                            │             │                      │ Alert
                            │             │                      │ triggered
                            │             │                      ▼
                            │             │               ┌──────────────┐
                            │             │               │   MySQL │
                            │             │               │   (alerts)   │
                            │             │               └──────────────┘
                            │             │
                            │             │ Write
                            │             ▼
                            │        ┌──────────────┐
                            └──────> │  InfluxDB    │
                               Flux  │  (telemetry) │
                                      └──────────────┘
```

**Steps:**
1. Device publishes telemetry to MQTT topic `devices/{device_id}/telemetry`
2. Data Service MQTT handler receives message
3. Data Service validates telemetry (range checks)
4. Data Service enriches with device metadata (fetches from Device Service)
5. Data Service writes to InfluxDB
6. Data Service triggers rule evaluation (calls Rule Engine)
7. Rule Engine evaluates against active rules
8. If triggered, Rule Engine creates alert in MySQL

### 2. Dataset Production and Storage

```
┌─────────────┐     Flux      ┌─────────────────┐     Parquet    ┌──────────────┐
│  InfluxDB   │ ─────────────> │ Data Export Svc │ ─────────────> │     S3       │
│ (telemetry) │   (query)      │                 │   (write)      │  (datasets)  │
└─────────────┘                │                 │                └──────────────┘
                               │                 │                      │
                               │                 │                      │ Dataset
                               │                 │                      │ listed
                               │                 │                      ▼
                               │                 │                ┌──────────────┐
                               │                 │                │   Analytics  │
                               │                 │                │   Service    │
                               │                 │                └──────────────┘
                               │                 │
                               │ Checkpoint      │
                               ▼                 │
                        ┌──────────────┐        │
                        │  MySQL  │        │
                        │(checkpoints) │        │
                        └──────────────┘        │
                                                │
                        ┌──────────────┐        │
                        │   Scheduled  │        │
                        │   Export     │───────>│
                        │   (60s loop) │  (run) │
                        └──────────────┘        │
                                                │
                        ┌──────────────┐        │
                        │  On-Demand   │        │
                        │   Export API │───────>│
                        └──────────────┘        │
```

**Steps:**
1. Data Export Service runs scheduled export loop (every 60s)
2. For each device, checks last checkpoint from MySQL
3. Queries InfluxDB for new telemetry since last checkpoint
4. Converts to Parquet format with computed features
5. Uploads to S3 with path: `datasets/{device_id}/{start}_{end}.parquet`
6. Updates checkpoint in MySQL
7. Analytics Service can now list and use the dataset

### 3. Analytics Job Lifecycle

```
┌──────────┐     POST /run     ┌─────────────────┐     Queue      ┌─────────────┐
│   UI     │ ────────────────> │ Analytics Svc   │ ─────────────> │ Job Worker  │
│          │   (submit job)    │                 │   (async)      │             │
└──────────┘                   │                 │                └─────────────┘
     │                         │                 │                       │
     │                         │                 │                       │ Process
     │                         │                 │                       ▼
     │                         │                 │                ┌─────────────┐
     │                         │                 │                │  Read S3    │
     │                         │                 │                │  Dataset    │
     │                         │                 │                └─────────────┘
     │                         │                 │                       │
     │                         │                 │                       ▼
     │                         │                 │                ┌─────────────┐
     │                         │                 │                │  Run ML     │
     │ GET /status             │                 │                │  Pipeline   │
     │<────────────────────────│                 │                └─────────────┘
     │  (poll status)          │                 │                       │
     │                         │                 │                       ▼
     │                         │                 │                ┌─────────────┐
     │                         │                 │                │  Save to    │
     │                         │                 │                │ MySQL  │
     │                         │                 │                └─────────────┘
     │                         │                 │                       │
     │ GET /results            │                 │                       │ Results
     │<────────────────────────│                 │                       │ available
     │  (fetch results)        │                 │                       │
     │                         │                 │                       │
```

**Steps:**
1. UI submits analytics job via POST /api/v1/analytics/run
2. Analytics Service creates job record (status: pending)
3. Job queued for background processing
4. Job Worker picks up job (status: running)
5. Worker reads dataset from S3
6. Worker runs ML pipeline (anomaly/prediction/forecast)
7. Worker saves results to MySQL (status: completed)
8. UI polls status endpoint until completed
9. UI fetches results via GET /api/v1/analytics/results/{job_id}

### 4. Analytics Results Persistence and Fetching

```
┌─────────────────┐     Results      ┌─────────────────┐
│  Job Worker     │ ────────────────>│   MySQL    │
│ (ML pipeline)   │   (JSON)        │ analytics_jobs  │
└─────────────────┘                  └─────────────────┘
                                              │
                                              │ Query
                                              ▼
                                     ┌─────────────────┐
                                     │      UI         │
                                     │ (display        │
                                     │  charts)        │
                                     └─────────────────┘
```

**Steps:**
1. ML pipeline generates results (anomalies, predictions, forecasts)
2. Results stored in `analytics_jobs.results` column (JSON)
3. Accuracy metrics stored in `analytics_jobs.accuracy_metrics`
4. UI fetches results and renders charts

### 5. Export Trigger and Parquet File Creation

```
┌──────────┐     POST /run     ┌─────────────────┐     Query      ┌─────────────┐
│   UI     │ ────────────────> │ Data Export Svc │ ─────────────> │  InfluxDB   │
│          │   (trigger)       │                 │   (Flux)       │             │
└──────────┘                   │                 │                └─────────────┘
     │                         │                 │                       │
     │                         │                 │ Telemetry             │
     │                         │                 │ data                  │
     │                         │                 │                       ▼
     │                         │                 │                ┌─────────────┐
     │                         │                 │                │  Pandas     │
     │                         │                 │                │  DataFrame  │
     │ GET /status             │                 │                └─────────────┘
     │<────────────────────────│                 │                       │
     │  (poll)                 │                 │                       ▼
     │                         │                 │                ┌─────────────┐
     │                         │                 │                │  Parquet    │
     │                         │                 │                │  (Snappy)   │
     │                         │                 │                └─────────────┘
     │                         │                 │                       │
     │                         │                 │                       ▼
     │                         │                 │                ┌─────────────┐
     │                         │ Upload          │                │     S3      │
     │                         │────────────────>│                │ (datasets)  │
     │                         │                 │                └─────────────┘
     │                         │                 │                       │
     │                         │ Checkpoint      │                       │
     │                         │────────────────>│                       │
     │                         │                 │                       │
     │                         │        ┌────────┴────────┐              │
     │                         │        │   MySQL    │              │
     │                         │        │export_checkpoints│             │
     │                         │        └─────────────────┘              │
```

**Steps:**
1. UI triggers export via POST /api/v1/exports/run
2. Data Export Service queries InfluxDB using Flux
3. Results converted to Pandas DataFrame
4. Computed features added (hour, day_of_week, is_weekend, power_factor)
5. DataFrame written to Parquet with Snappy compression
6. File uploaded to S3
7. Checkpoint updated in MySQL
8. UI polls status until completed

---

## Frontend to API Mapping

### Next.js Application Structure

**Source:** `/ui-web/`

**Base Configuration:** `next.config.ts`

```typescript
// API Gateway routes
/backend/device/*     → http://localhost:8000/*     (Device Service)
/backend/data/*       → http://localhost:8081/*     (Data Service)
/backend/rule-engine/*→ http://localhost:8002/*     (Rule Engine)
/backend/analytics/*  → http://localhost:8003/*     (Analytics Service)
/backend/data-export/*→ http://localhost:8080/*     (Data Export Service)
```

---

### Page: Home (`/`)
**File:** `app/page.tsx`
**Description:** Landing page with navigation cards

**APIs Called:** None (static content)

---

### Page: Machines List (`/machines`)
**File:** `app/machines/page.tsx`
**Description:** Grid view of all devices/machines

**APIs Called:**
| API | Service | Endpoint | Purpose |
|-----|---------|----------|---------|
| `getDevices()` | Device Service | `GET /api/v1/devices` | Load all machines |

**Response Used:** Display machine cards with name, ID, type, status, location

---

### Page: Machine Dashboard (`/machines/{deviceId}`)
**File:** `app/machines/[deviceId]/page.tsx`
**Description:** Single machine dashboard with tabs (Overview, Telemetry, Rules)

**APIs Called:**
| API | Service | Endpoint | Purpose |
|-----|---------|----------|---------|
| `getDeviceById()` | Device Service | `GET /api/v1/devices/{id}` | Load machine info |
| `getTelemetry()` | Data Service | `GET /api/v1/data/telemetry/{id}` | Load telemetry data |
| `getDeviceStats()` | Data Service | `GET /api/v1/data/stats/{id}` | Load statistics |

**Response Used:**
- Device info: Header display, breadcrumbs
- Telemetry: Latest values (power, voltage, temperature), time series charts
- Stats: Aggregated metrics display

---

### Page: Rules (`/rules`)
**File:** `app/rules/page.tsx`
**Description:** Rules management with create form and list

**APIs Called:**
| API | Service | Endpoint | Purpose |
|-----|---------|----------|---------|
| `listRules()` | Rule Engine | `GET /api/v1/rules` | Load all rules |
| `getDevices()` | Device Service | `GET /api/v1/devices` | Device selector |
| `createRule()` | Rule Engine | `POST /api/v1/rules` | Create new rule |
| `updateRuleStatus()` | Rule Engine | `PATCH /api/v1/rules/{id}/status` | Pause/resume |
| `deleteRule()` | Rule Engine | `DELETE /api/v1/rules/{id}` | Delete rule |

**Response Used:**
- Rules list: Table display with status badges
- Device names: Map device_ids to human-readable names

---

### Page: Create Rule (`/rules/new`)
**File:** `app/rules/new/page.tsx`
**Description:** Form to create new monitoring rule

**APIs Called:**
| API | Service | Endpoint | Purpose |
|-----|---------|----------|---------|
| `createRule()` | Rule Engine | `POST /api/v1/rules` | Submit rule |
| `updateRuleStatus()` | Rule Engine | `PATCH /api/v1/rules/{id}/status` | Disable if needed |

---

### Page: Analytics (`/analytics`)
**File:** `app/analytics/page.tsx`
**Description:** ML analytics interface for running jobs and viewing results

**APIs Called:**
| API | Service | Endpoint | Purpose |
|-----|---------|----------|---------|
| `getDevices()` | Device Service | `GET /api/v1/devices` | Device selector |
| `getSupportedModels()` | Analytics | `GET /api/v1/analytics/models` | Load ML models |
| `getAvailableDatasets()` | Analytics | `GET /api/v1/analytics/datasets` | Load datasets |
| `runAnalytics()` | Analytics | `POST /api/v1/analytics/run` | Start analysis |
| `getAnalyticsStatus()` | Analytics | `GET /api/v1/analytics/status/{id}` | Poll status |
| `getAnalyticsResults()` | Analytics | `GET /api/v1/analytics/results/{id}` | Get results |
| `runExport()` | Data Export | `POST /api/v1/exports/run` | Trigger export |
| `getExportStatus()` | Data Export | `GET /api/v1/exports/status/{id}` | Poll export |

**Response Used:**
- Models: Populate model dropdowns by analysis type
- Datasets: Populate dataset selector
- Status: Show job progress
- Results: Render charts (AnomalyChart, ForecastChart), display metrics

---

### Page: Settings (`/settings`)
**File:** `app/settings/page.tsx`
**Description:** User settings and notification preferences

**APIs Called:** None (localStorage only)

**Note:** Settings are stored in browser localStorage, not persisted to backend.

---

### Component: Machine Rules View
**File:** `app/machines/[deviceId]/rules/machine-rules-view.tsx`
**Description:** Rules configuration tab within machine dashboard

**APIs Called:**
| API | Service | Endpoint | Purpose |
|-----|---------|----------|---------|
| `listRules()` | Rule Engine | `GET /api/v1/rules?device_id={id}` | Load device rules |
| `createRule()` | Rule Engine | `POST /api/v1/rules` | Create rule for device |
| `updateRuleStatus()` | Rule Engine | `PATCH /api/v1/rules/{id}/status` | Toggle rule |
| `deleteRule()` | Rule Engine | `DELETE /api/v1/rules/{id}` | Remove rule |

---

### Component: Telemetry Charts
**File:** `components/charts/telemetry-charts.tsx`
**Description:** Recharts-based visualization components

**Used By:**
- Machine Dashboard (Power, Voltage, Temperature trends)
- Analytics Page (Anomaly detection results, Forecast results)

**Data Sources:**
- Telemetry data from Data Service
- Analytics results from Analytics Service

---

### API Client Library Structure

**Base Constants:** `lib/api.ts`
```typescript
DEVICE_SERVICE_BASE = "/backend/device"
DATA_SERVICE_BASE = "/backend/data"
RULE_ENGINE_SERVICE_BASE = "/backend/rule-engine"
ANALYTICS_SERVICE_BASE = "/backend/analytics"
DATA_EXPORT_SERVICE_BASE = "/backend/data-export"
```

**Device API:** `lib/deviceApi.ts`
- `getDevices()` → Device Service
- `getDeviceById(id)` → Device Service

**Data API:** `lib/dataApi.ts`
- `getTelemetry(id, params)` → Data Service
- `getDeviceStats(id)` → Data Service
- `getDeviceAlerts(id, params)` → Rule Engine
- `acknowledgeAlert(id, user)` → Rule Engine
- `resolveAlert(id)` → Rule Engine

**Rule API:** `lib/ruleApi.ts`
- `listRules(params)` → Rule Engine
- `createRule(payload)` → Rule Engine
- `updateRuleStatus(id, status)` → Rule Engine
- `deleteRule(id)` → Rule Engine

**Analytics API:** `lib/analyticsApi.ts`
- `runAnalytics(payload)` → Analytics Service
- `getAnalyticsStatus(id)` → Analytics Service
- `getAnalyticsResults(id)` → Analytics Service
- `getSupportedModels()` → Analytics Service
- `getAvailableDatasets(id)` → Analytics Service

**Data Export API:** `lib/dataExportApi.ts`
- `runExport(id)` → Data Export Service
- `getExportStatus(id)` → Data Export Service

---

## Appendix: Configuration Reference

### Environment Variables Summary

#### Device Service
```bash
PORT=8000
DATABASE_URL=mysql+aiomysql://energy:energy@localhost:3306/energy_device_db
LOG_LEVEL=INFO
```

#### Data Service
```bash
PORT=8081
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
INFLUXDB_URL=http://localhost:8086
INFLUXDB_BUCKET=telemetry
DEVICE_SERVICE_URL=http://localhost:8000
RULE_ENGINE_URL=http://localhost:8002
```

#### Rule Engine Service
```bash
PORT=8002
DATABASE_URL=mysql+aiomysql://energy:energy@localhost:3306/energy_rule_db
RULE_EVALUATION_TIMEOUT=5
NOTIFICATION_COOLDOWN_MINUTES=15
```

#### Analytics Service
```bash
PORT=8003
MYSQL_HOST=localhost
MYSQL_DATABASE=energy_analytics_db
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=energy-platform-datasets
MAX_CONCURRENT_JOBS=3
JOB_TIMEOUT_SECONDS=3600
```

#### Data Export Service
```bash
PORT=8080
INFLUXDB_URL=http://localhost:8086
INFLUXDB_BUCKET=telemetry
CHECKPOINT_DB_HOST=localhost
CHECKPOINT_DB_NAME=energy_export_db
S3_BUCKET=energy-platform-datasets
EXPORT_INTERVAL_SECONDS=60
EXPORT_BATCH_SIZE=1000
```

#### Reporting Service
```bash
PORT=8085
MYSQL_HOST=localhost
MYSQL_DATABASE=energy_reporting_db
S3_BUCKET_NAME=energy-platform-datasets
```

#### Frontend
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:3000
```

### Port Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Next.js Frontend | 3000 | HTTP | Web UI |
| Device Service | 8000 | HTTP | Device CRUD API |
| Rule Engine | 8002 | HTTP | Rules & Alerts API |
| Analytics Service | 8003 | HTTP | ML Analytics API |
| Data Export Service | 8080 | HTTP | Export API |
| Data Service | 8081 | HTTP + MQTT | Telemetry API |
| Reporting Service | 8085 | HTTP | Reports API |
| InfluxDB | 8086 | HTTP | Time-series DB |
| MySQL | 3306 | TCP | Relational DB |
| MQTT Broker | 1883 | TCP | Message broker |
| S3/MinIO | 9000 | HTTP | Object storage |

---

**End of Document**

*This document was generated on 2026-02-12 based on actual codebase analysis.*
