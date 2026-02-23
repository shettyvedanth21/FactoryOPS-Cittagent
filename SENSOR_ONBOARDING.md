# Sensor Onboarding Guide - Firmware Team

**Document Version:** 1.0  
**Date:** 2026-02-23  
**Purpose:** Technical guide for firmware developers to integrate sensors with the Energy Intelligence Platform

---

## Table of Contents

1. [Overview](#overview)
2. [MQTT Connection](#mqtt-connection)
3. [Telemetry Format](#telemetry-format)
4. [Supported Data Types](#supported-data-types)
5. [Example Payloads](#example-payloads)
6. [Connection Settings](#connection-settings)
7. [Testing Your Integration](#testing-your-integration)
8. [FAQ](#faq)

---

## 1. Overview

The Energy Intelligence Platform receives telemetry data from sensors via **MQTT protocol**. Sensors must:

1. Connect to the MQTT broker
2. Publish telemetry data to a specific topic
3. Follow the defined JSON payload format

---

## 2. MQTT Connection

### Broker Details

| Setting | Value |
|---------|-------|
| Protocol | MQTT (TCP) |
| Host | `localhost` or `emqx` (Docker) |
| Port | `1883` |
| QoS | 1 (Recommended) |
| Client ID | Unique identifier for your device |

### Topic Structure

```
devices/{device_id}/telemetry
```

**Example:**
```
devices/D1/telemetry
devices/SENSOR-001/telemetry
devices/COMPRESSOR-A/telemetry
```

### Wildcard Subscription (For Testing)

The platform subscribes to:
```
devices/+/telemetry
```

---

## 3. Telemetry Format

### Required Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_id` | string | ✅ Yes | Unique device identifier |
| `timestamp` | string | ✅ Yes | ISO 8601 UTC timestamp |
| `schema_version` | string | ✅ Yes | Schema version (use "v1") |

### Optional Fields

Any additional **numeric** fields will be automatically captured and stored.

---

## 4. Supported Data Types

### Numeric Types (Automatically Stored)

| Type | Example Values | Use Case |
|------|---------------|----------|
| `float` | 45.23, 230.5, 0.85 | Sensor readings |
| `integer` | 100, 500, 1024 | Counters, states |
| `boolean` | 0, 1 | On/off states |

### Recommended Metric Names

| Metric | Unit | Typical Range | Description |
|--------|------|---------------|-------------|
| `voltage` | V | 200 - 250 | Supply voltage |
| `current` | A | 0 - 20 | Current draw |
| `power` | W | 0 - 500 | Power consumption |
| `temperature` | °C | 0 - 100 | Temperature sensor |
| `pressure` | bar | 0 - 10 | Pressure sensor |
| `humidity` | % | 0 - 100 | Humidity sensor |
| `vibration` | mm/s | 0 - 10 | Vibration sensor |
| `frequency` | Hz | 45 - 55 | Frequency sensor |
| `power_factor` | - | 0.8 - 1.0 | Power factor |
| `speed` | RPM | 0 - 3000 | Motor speed |
| `torque` | Nm | 0 - 500 | Motor torque |
| `oil_pressure` | bar | 0 - 5 | Oil pressure |

### Custom Metrics

You can send **any numeric field** - the system will automatically discover and store it:

```json
{
  "custom_field_1": 123.45,
  "my_sensor_value": 67.89
}
```

---

## 5. Example Payloads

### Minimal Payload (Temperature Sensor)

```json
{
  "device_id": "D1",
  "timestamp": "2026-02-23T10:30:00Z",
  "schema_version": "v1",
  "temperature": 45.5
}
```

### Full Payload (Multiple Sensors)

```json
{
  "device_id": "D1",
  "timestamp": "2026-02-23T10:30:00Z",
  "schema_version": "v1",
  "temperature": 45.5,
  "pressure": 5.2,
  "vibration": 1.3,
  "power": 195.5,
  "voltage": 230.2,
  "current": 0.85
}
```

### Motor Sensor Payload

```json
{
  "device_id": "MOTOR-001",
  "timestamp": "2026-02-23T10:30:00Z",
  "schema_version": "v1",
  "speed": 1450,
  "torque": 250.5,
  "temperature": 55.2,
  "vibration": 2.1,
  "power": 4200,
  "current": 18.5
}
```

### Power Monitor Payload

```json
{
  "device_id": "POWER-MON-01",
  "timestamp": "2026-02-23T10:30:00Z",
  "schema_version": "v1",
  "voltage": 235.5,
  "current": 12.8,
  "power": 2980.0,
  "frequency": 50.2,
  "power_factor": 0.95
}
```

---

## 6. Connection Settings

### MQTT Connection Parameters

```c
// Example MQTT connection settings for embedded systems

#define MQTT_BROKER_HOST "localhost"
#define MQTT_BROKER_PORT 1883
#define MQTT_TOPIC_PREFIX "devices/"
#define MQTT_DEVICE_ID "D1"  // Replace with your device ID
#define MQTT_QOS 1

// Full topic: devices/D1/telemetry
```

### Recommended Publish Interval

| Interval | Use Case |
|----------|----------|
| 1 second | High-frequency monitoring |
| 5 seconds | Standard monitoring |
| 30 seconds | Low-power devices |
| 60 seconds | Battery-powered sensors |

---

## 7. Testing Your Integration

### Option 1: MQTT Test Client

Use MQTT Explorer or similar tool:

1. Connect to `localhost:1883`
2. Subscribe to `devices/+/telemetry`
3. Publish test message to `devices/D1/telemetry`

### Option 2: Command Line (mosquitto_pub)

```bash
# Publish test telemetry
mosquitto_pub -h localhost -p 1883 -t devices/D1/telemetry -m '{
  "device_id": "D1",
  "timestamp": "2026-02-23T10:30:00Z",
  "schema_version": "v1",
  "temperature": 45.5
}'
```

### Option 3: Python Script

```python
import paho.mqtt.client as mqtt
import json
import time

def publish_telemetry():
    client = mqtt.Client(client_id="test_sensor")
    client.connect("localhost", 1883)
    
    payload = {
        "device_id": "D1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "schema_version": "v1",
        "temperature": 45.5,
        "pressure": 5.2
    }
    
    client.publish("devices/D1/telemetry", json.dumps(payload))
    client.disconnect()

publish_telemetry()
```

### Verify Data Received

After publishing, check:

1. **Device Service:** `GET /api/v1/devices/{device_id}`
   - Should show `runtime_status: "running"`
   - Should show `last_seen_timestamp` updated

2. **Data Service:** `GET /api/telemetry/{device_id}?limit=10`
   - Should return the telemetry data

---

## 8. FAQ

### Q: What if my device has network issues?

**A:** The platform handles reconnection. Just ensure:
- Device reconnects when network is available
- Resumes publishing telemetry
- Last seen will update automatically

### Q: Can I send non-numeric data?

**A:** Currently only numeric fields (int, float) are stored. String fields are ignored but don't cause errors.

### Q: What happens if I change the device ID?

**A:** Each device ID is treated as a unique device. If you change it, it will appear as a new device in the platform.

### Q: Do I need to register devices first?

**A:** Yes. Before sending telemetry, the device must be onboarded via:
```
POST /api/v1/devices
{
  "device_id": "D1",
  "device_name": "My Sensor",
  "device_type": "sensor",
  "location": "Building A"
}
```

### Q: What timestamp format should I use?

**A:** ISO 8601 UTC format is required:
```
2026-02-23T10:30:00Z
```
or
```
2026-02-23T10:30:00+00:00
```

### Q: How do I know my data is being received?

**A:** Check the API:
```bash
curl http://localhost:8000/api/v1/devices/D1
```
Look for:
- `runtime_status`: should be "running"
- `last_seen_timestamp`: should be recent

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│              SENSOR INTEGRATION CHECKLIST              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1. Onboard device:                                      │
│    POST /api/v1/devices                                │
│    { device_id, device_name, device_type, location }   │
│                                                         │
│ 2. Connect to MQTT:                                    │
│    Host: localhost:1883                                 │
│    Topic: devices/{device_id}/telemetry                │
│                                                         │
│ 3. Publish JSON:                                       │
│    {                                                    │
│      "device_id": "D1",                                │
│      "timestamp": "2026-02-23T10:30:00Z",            │
│      "schema_version": "v1",                           │
│      "temperature": 45.5,                              │
│      ...                                                │
│    }                                                    │
│                                                         │
│ 4. Verify:                                             │
│    GET /api/v1/devices/D1                              │
│    → runtime_status: "running"                         │
│    → last_seen_timestamp: updated                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Support

For technical questions:
- Check API documentation: `API_CONTRACT.md`
- Check database schema: `TableSchem.md`

---

**End of Sensor Onboarding Guide**
