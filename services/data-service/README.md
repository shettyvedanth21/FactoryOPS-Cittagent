# Data Service

Telemetry ingestion, validation, enrichment, and persistence service for the Energy Intelligence & Analytics Platform.

## Overview

The Data Service is a critical component that:
- Subscribes to MQTT telemetry messages
- Validates incoming data against strict schemas
- Enriches data with device metadata
- Persists to InfluxDB
- Triggers rule evaluations
- Provides REST APIs and WebSocket for data access

## Architecture

```
MQTT Broker → MQTT Handler → Validation → Enrichment → InfluxDB
                                    ↓
                              Rule Engine (async)
                                    ↓
                              WebSocket Broadcast
```

## Features

### MQTT Subscriber
- Topic: `devices/+/telemetry`
- QoS 1 (at-least-once delivery)
- Automatic reconnection with exponential backoff

### Validation
- Required fields: device_id, timestamp, voltage, current, power, temperature
- Numeric range validation
- Schema version validation (strict v1 support)
- Dead Letter Queue for invalid messages

### Enrichment
- Fetches device metadata from Device Service
- Non-blocking async calls
- Enrichment status tracking

### Persistence
- InfluxDB for time-series data
- Tags: device_id, schema_version, enrichment_status
- Fields: voltage, current, power, temperature

### Rule Engine Integration
- Async rule evaluation triggers
- Circuit breaker pattern
- Retry with exponential backoff

## API Endpoints

### Health
- `GET /api/data/health` - Health check

### Telemetry
- `GET /api/data/telemetry/{device_id}` - Get device telemetry
  - Query params: start_time, end_time, fields, aggregate, interval, limit
- `GET /api/data/stats/{device_id}` - Get device statistics
- `POST /api/data/query` - Custom query

### WebSocket
- `WS /ws/telemetry/{device_id}` - Live telemetry stream

## Configuration

Environment variables:

```bash
# Server
HOST=0.0.0.0
PORT=8081
LOG_LEVEL=INFO

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_TOPIC=devices/+/telemetry
MQTT_QOS=1

# InfluxDB
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-token
INFLUXDB_ORG=energy-platform
INFLUXDB_BUCKET=telemetry

# Device Service
DEVICE_SERVICE_URL=http://device-service:8080

# Rule Engine
RULE_ENGINE_URL=http://rule-engine:8082

# DLQ
DLQ_ENABLED=true
DLQ_DIRECTORY=./dlq
```

## Running

### Development

```bash
cd services/data-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd src
python main.py
```

### Production

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8081 --workers 4
```

## Testing

```bash
pytest tests/ -v --cov=src --cov-report=html
```

## Data Model

### Telemetry Payload (v1)

```json
{
  "device_id": "D1",
  "timestamp": "2026-02-07T11:26:00Z",
  "voltage": 230.5,
  "current": 0.85,
  "power": 195.9,
  "temperature": 45.2,
  "schema_version": "v1"
}
```

### Validation Rules

- voltage: 200-250 V
- current: 0-2 A
- power: 0-500 W
- temperature: 20-80 °C

## License

Copyright © 2026 Energy Intelligence Platform
