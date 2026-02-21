# Data Export Service

Continuous telemetry data export service for the Energy Intelligence & Analytics Platform.

## Overview

This service continuously exports telemetry data from InfluxDB to Amazon S3 in near-real-time, partitioned by device and date for efficient analytics processing.

## Features

- **Continuous Export**: Micro-batch export pipeline running at configurable intervals
- **Idempotent Design**: Checkpoint tracking prevents duplicate exports
- **Partitioned Storage**: Data organized by `device_id/date/` for analytics
- **Multiple Formats**: Supports Parquet (default) and CSV
- **Health Monitoring**: `/health` and `/ready` endpoints for k8s probes
- **Graceful Shutdown**: Proper cleanup on SIGTERM/SIGINT

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  InfluxDB    │────▶│    Worker    │────▶│    S3        │
│  (Source)    │     │   (Export)   │     │ (Destination)│
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  PostgreSQL  │
                    │(Checkpoints) │
                    └──────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- InfluxDB (source telemetry data)
- PostgreSQL (checkpoint storage)
- S3 bucket (destination)

### Installation

```bash
cd services/data-export-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# Service
SERVICE_NAME=data-export-service
LOG_LEVEL=INFO
PORT=8080

# InfluxDB (Source)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=energy-platform
INFLUXDB_BUCKET=telemetry

# MySQL (Checkpoint Storage)
CHECKPOINT_DB_HOST=mysql
CHECKPOINT_DB_PORT=3306
CHECKPOINT_DB_NAME=energy_export_db
CHECKPOINT_DB_USER=energy
CHECKPOINT_DB_PASSWORD=energy

# S3 (Destination)
S3_BUCKET=energy-platform-datasets
S3_PREFIX=telemetry
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Export Configuration
EXPORT_INTERVAL_SECONDS=60
EXPORT_BATCH_SIZE=1000
EXPORT_FORMAT=parquet
DEVICE_IDS=D1
LOOKBACK_HOURS=1
```

### Run

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

## API Endpoints

### Health Check
```bash
GET /health

Response:
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2026-02-07T11:26:00Z"
}
```

### Readiness Check
```bash
GET /ready

Response:
{
    "ready": true,
    "checks": {
        "worker_running": true,
        "checkpoint_store_connected": true,
        "s3_accessible": true
    }
}
```

## Exported Data Format

### S3 Key Structure
```
s3://bucket/telemetry/device_id=D1/date=2026/02/07/export_120000.parquet
```

### Schema
- `timestamp`: ISO8601 timestamp
- `device_id`: Device identifier
- `device_type`: Device type (bulb, compressor, etc.)
- `location`: Physical location
- `voltage`: Voltage reading (V)
- `current`: Current reading (A)
- `power`: Power consumption (W)
- `temperature`: Temperature reading (°C)
- `hour`: Hour of day (0-23)
- `day_of_week`: Day of week (0-6)
- `is_weekend`: Boolean weekend indicator
- `power_factor`: Calculated power factor

## Checkpoint System

The service tracks export progress in PostgreSQL to ensure:
- **At-least-once delivery**: No data loss on failures
- **Idempotency**: Duplicate exports are skipped
- **Resume capability**: Restarts from last successful export

## Development

### Run Tests
```bash
pytest tests/ -v --cov=.
```

### Type Checking
```bash
mypy .
```

### Code Formatting
```bash
black .
isort .
```

## Deployment

### Kubernetes

The service exposes:
- Port `8080`: HTTP API
- `/health`: Liveness probe
- `/ready`: Readiness probe

Recommended resource limits:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## License

Internal use only - Energy Intelligence Platform
