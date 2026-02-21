# Device Simulator for Energy Intelligence Platform

Production-grade MQTT device simulator for generating realistic telemetry data.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run simulator
python main.py --device-id D1 --interval 5

# With custom broker
python main.py --device-id D1 --interval 5 --broker localhost --port 1883

# With fault injection
python main.py --device-id D1 --interval 5 --fault-mode overheating
```

## CLI Options

- `--device-id`: Device identifier (required)
- `--interval`: Publish interval in seconds (default: 5)
- `--broker`: MQTT broker host (default: localhost)
- `--port`: MQTT broker port (default: 1883)
- `--fault-mode`: Fault injection mode - 'none', 'spike', 'drop', 'overheating' (default: none)
- `--log-level`: Logging level (default: INFO)

## Telemetry Schema

```json
{
  "device_id": "D1",
  "timestamp": "2026-02-07T11:26:00Z",
  "schema_version": "v1",
  "voltage": 230.5,
  "current": 0.85,
  "power": 195.9,
  "temperature": 45.2
}
```

## Features

- Realistic time-series data generation with smooth variation and noise
- MQTT QoS 1 publishing with automatic reconnect
- Exponential backoff for reconnection
- Graceful shutdown handling
- Structured JSON logging
- Multiple fault injection modes
- Production-ready error handling
