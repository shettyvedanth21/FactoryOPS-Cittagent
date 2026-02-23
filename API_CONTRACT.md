# API Contract - Energy Intelligence Platform

**Document Version:** 1.0  
**Date:** 2026-02-22  
**Purpose:** UI Developer Reference for API Integration

---

## Table of Contents

1. [Base URLs](#base-urls)
2. [Device Service APIs](#device-service-apis)
3. [Data Service APIs](#data-service-apis)
4. [Rule Engine APIs](#rule-engine-apis)
5. [Common Response Formats](#common-response-formats)
6. [Error Handling](#error-handling)

---

## 1. Base URLs

| Service | Internal URL | External URL |
|---------|-------------|--------------|
| Device Service | http://device-service:8000 | http://localhost:8000 |
| Data Service | http://data-service:8081 | http://localhost:8081 |
| Rule Engine | http://rule-engine-service:8002 | http://localhost:8002 |
| Analytics | http://analytics-service:8003 | http://localhost:8003 |
| UI Web | - | http://localhost:3000 |

**Frontend Proxy:** The UI proxies requests to backend services via `/api/*` routes.

---

## 2. Device Service APIs

**Base URL:** `/api/v1/devices`

### 2.1 List All Devices

```
GET /api/v1/devices
```

**Description:** Get a paginated list of all devices.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| tenant_id | string | No | Filter by tenant (for multi-tenancy) |
| device_type | string | No | Filter by device type (e.g., 'sensor', 'motor') |
| status | string | No | Filter by status ('active', 'inactive') |
| page | integer | No | Page number (default: 1) |
| page_size | integer | No | Items per page (default: 20, max: 100) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "device_id": "D1",
      "device_name": "Device 1 - Pressure Sensor",
      "device_type": "sensor",
      "location": "Building A",
      "runtime_status": "running",
      "last_seen_timestamp": "2026-02-22T15:30:00.000000",
      "legacy_status": "active",
      "created_at": "2026-02-21T17:51:27"
    }
  ],
  "total": 4,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### 2.2 Get Device by ID

```
GET /api/v1/devices/{device_id}
```

**Description:** Get detailed information about a specific device.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| device_id | string | Unique device identifier (e.g., 'D1') |

**Response:**
```json
{
  "success": true,
  "data": {
    "device_id": "D1",
    "device_name": "Device 1 - Pressure Sensor",
    "device_type": "sensor",
    "manufacturer": null,
    "model": null,
    "location": "Building A",
    "runtime_status": "running",
    "last_seen_timestamp": "2026-02-22T15:30:00.000000",
    "legacy_status": "active",
    "created_at": "2026-02-21T17:51:27",
    "updated_at": "2026-02-22T15:30:00"
  }
}
```

---

### 2.3 Create Device

```
POST /api/v1/devices
```

**Description:** Onboard a new device to the platform.

**Request Body:**
```json
{
  "device_id": "D5",
  "device_name": "New Device",
  "device_type": "sensor",
  "location": "Building B",
  "manufacturer": "Siemens",
  "model": "SIMATIC"
}
```

**Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| device_id | string | Yes | Unique ID (max 50 chars, alphanumeric + _ -) |
| device_name | string | Yes | Display name |
| device_type | string | Yes | Type: 'sensor', 'motor', 'compressor', etc. |
| location | string | No | Physical location |
| manufacturer | string | No | Manufacturer name |
| model | string | No | Model number |

**Response:** Returns the created device object.

---

### 2.4 Update Device

```
PUT /api/v1/devices/{device_id}
```

**Description:** Update device information.

**Request Body:** (partial update - only include fields to update)
```json
{
  "device_name": "Updated Name",
  "location": "Building C"
}
```

---

### 2.5 Delete Device

```
DELETE /api/v1/devices/{device_id}
```

**Description:** Delete a device and all its configurations.

**Response:**
```json
{
  "success": true,
  "message": "Device D1 deleted successfully"
}
```

---

### 2.6 Get Device Properties

```
GET /api/v1/devices/{device_id}/properties
```

**Description:** Get all telemetry properties discovered for a device.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| numeric_only | boolean | Return only numeric properties (default: false) |

**Response:**
```json
[
  {"id": 1, "property_name": "temperature", "data_type": "float", "is_numeric": true},
  {"id": 2, "property_name": "pressure", "data_type": "float", "is_numeric": true},
  {"id": 3, "property_name": "status", "data_type": "string", "is_numeric": false}
]
```

---

### 2.7 Get All Devices Properties

```
GET /api/v1/devices/properties
```

**Description:** Get properties for all devices.

**Response:**
```json
{
  "success": true,
  "devices": {
    "D1": ["temperature", "pressure", "power"],
    "D2": ["voltage", "current", "power"]
  },
  "all_properties": ["temperature", "pressure", "power", "voltage", "current"]
}
```

---

### 2.8 Get Common Properties

```
POST /api/v1/devices/properties/common
```

**Description:** Get common properties across selected devices (for rule creation).

**Request Body:**
```json
{
  "device_ids": ["D1", "D2", "D3"]
}
```

**Response:**
```json
{
  "success": true,
  "properties": ["temperature", "power"],
  "device_count": 3
}
```

---

### 2.9 Device Heartbeat

```
POST /api/v1/devices/{device_id}/heartbeat
```

**Description:** Update last_seen_timestamp for a device (called by telemetry service).

**Response:**
```json
{
  "success": true,
  "device_id": "D1",
  "last_seen_timestamp": "2026-02-22T15:30:00.000000",
  "runtime_status": "running"
}
```

---

### 2.10 Sync Device Properties

```
POST /api/v1/devices/{device_id}/properties/sync
```

**Description:** Sync properties from incoming telemetry data.

**Request Body:**
```json
{
  "temperature": 45.2,
  "pressure": 5.5,
  "power": 120.5
}
```

---

### 2.11 Get Shifts

```
GET /api/v1/devices/{device_id}/shifts
```

**Description:** Get all shift configurations for uptime calculation.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "device_id": "D1",
      "shift_name": "Morning Shift",
      "shift_start": "09:00:00",
      "shift_end": "17:00:00",
      "maintenance_break_minutes": 30,
      "day_of_week": 0,
      "is_active": true
    }
  ],
  "total": 1
}
```

---

### 2.12 Create Shift

```
POST /api/v1/devices/{device_id}/shifts
```

**Description:** Create a new shift configuration.

**Request Body:**
```json
{
  "shift_name": "Morning Shift",
  "shift_start": "09:00:00",
  "shift_end": "17:00:00",
  "maintenance_break_minutes": 30,
  "day_of_week": 0,
  "is_active": true
}
```

---

### 2.13 Delete Shift

```
DELETE /api/v1/devices/{device_id}/shifts/{shift_id}
```

**Description:** Delete a shift configuration.

---

### 2.14 Get Uptime

```
GET /api/v1/devices/{device_id}/uptime
```

**Description:** Calculate device uptime based on shift configurations.

**Response:**
```json
{
  "success": true,
  "device_id": "D1",
  "total_shift_hours": 8.0,
  "downtime_hours": 0.5,
  "uptime_hours": 7.5,
  "uptime_percentage": 93.75,
  "last_telemetry_at": "2026-02-22T15:30:00",
  "shifts_configured": true
}
```

---

### 2.15 Get Health Configs

```
GET /api/v1/devices/{device_id}/health-config
```

**Description:** Get all health parameter configurations for a device.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "device_id": "D1",
      "parameter_name": "temperature",
      "normal_min": 20.0,
      "normal_max": 60.0,
      "max_min": 0.0,
      "max_max": 100.0,
      "weight": 25.0,
      "ignore_zero_value": false,
      "is_active": true
    }
  ],
  "total": 3
}
```

---

### 2.16 Create Health Config

```
POST /api/v1/devices/{device_id}/health-config
```

**Description:** Create a health parameter configuration.

**Request Body:**
```json
{
  "parameter_name": "temperature",
  "normal_min": 20.0,
  "normal_max": 60.0,
 "max_min": 0.0,
  "max_max": 100.0,
  "weight": 25.0,
  "ignore_zero_value": false,
  "is_active": true
}
```

**Note:** All weights for a device must sum to 100.

---

### 2.17 Update Health Config

```
PUT /api/v1/devices/{device_id}/health-config/{config_id}
```

**Description:** Update an existing health configuration.

---

### 2.18 Delete Health Config

```
DELETE /api/v1/devices/{device_id}/health-config/{config_id}
```

**Description:** Delete a health configuration.

---

### 2.19 Validate Health Weights

```
GET /api/v1/devices/{device_id}/health-config/validate-weights
```

**Description:** Validate that all health parameter weights sum to 100%.

**Response:**
```json
{
  "success": true,
  "is_valid": true,
  "total_weight": 100.0,
  "message": "Weights are valid"
}
```

---

### 2.20 Calculate Health Score

```
POST /api/v1/devices/{device_id}/health-score
```

**Description:** Calculate device health score based on current telemetry.

**Request Body:**
```json
{
  "values": {
    "temperature": 45.0,
    "pressure": 5.5,
    "vibration": 1.2
  },
  "machine_state": "RUNNING"
}
```

**Response:**
```json
{
  "success": true,
  "device_id": "D1",
  "health_score": 85.5,
  "status": "healthy",
  "parameters": [
    {
      "parameter_name": "temperature",
      "raw_value": 45.0,
      "score": 62.5,
      "status": "warning"
    }
  ]
}
```

---

## 3. Data Service APIs

**Base URL:** `/api`

### 3.1 Get Telemetry

```
GET /api/telemetry/{device_id}
```

**Description:** Get historical telemetry data for a device.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| start_time | datetime | Start of time range (ISO 8601) |
| end_time | datetime | End of time range (ISO 8601) |
| limit | integer | Number of records (default: 100) |

**Example:**
```
GET /api/telemetry/D1?start_time=2026-02-22T00:00:00Z&end_time=2026-02-22T23:59:59Z&limit=100
```

**Response:**
```json
[
  {
    "device_id": "D1",
    "timestamp": "2026-02-22T15:30:00Z",
    "temperature": 45.2,
    "pressure": 5.5,
    "power": 120.5
  }
]
```

---

### 3.2 Get Device Stats

```
GET /api/stats/{device_id}
```

**Description:** Get statistical summary of telemetry data.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| start_time | datetime | Start of time range |
| end_time | datetime | End of time range |

**Response:**
```json
{
  "device_id": "D1",
  "count": 1000,
  "fields": {
    "temperature": {
      "min": 20.1,
      "max": 65.3,
      "mean": 42.5,
      "std": 8.2
    }
  }
}
```

---

## 4. Rule Engine APIs

**Base URL:** `/api/v1/rules`

### 4.1 List All Rules

```
GET /api/v1/rules
```

**Description:** Get all rules with optional filtering.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| tenant_id | string | Filter by tenant |
| status | string | Filter by status ('active', 'paused', 'archived') |
| page | integer | Page number |
| page_size | integer | Items per page |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "rule_id": "3db07cb9-54f3-4fc8-b863-2ab8fb797a78",
      "rule_name": "High Temperature Alert",
      "description": "Alert when temperature exceeds 80",
      "scope": "selected_devices",
      "property": "temperature",
      "condition": ">",
      "threshold": 80.0,
      "status": "active",
      "device_ids": ["D1", "D2"],
      "notification_channels": ["email"],
      "cooldown_minutes": 5,
      "created_at": "2026-02-21T17:51:27"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### 4.2 Get Rule by ID

```
GET /api/v1/rules/{rule_id}
```

**Description:** Get detailed information about a specific rule.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| rule_id | UUID | Unique rule identifier |

---

### 4.3 Create Rule

```
POST /api/v1/rules
```

**Description:** Create a new alerting rule.

**Request Body:**
```json
{
  "rule_name": "High Temperature Alert",
  "description": "Alert when temperature exceeds 80",
  "scope": "selected_devices",
  "property": "temperature",
  "condition": ">",
  "threshold": 80.0,
  "device_ids": ["D1", "D2"],
  "notification_channels": ["email", "webhook"],
  "cooldown_minutes": 5
}
```

**Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| rule_name | string | Yes | Display name for the rule |
| description | string | No | Rule description |
| scope | string | Yes | 'all_devices' or 'selected_devices' |
| property | string | Yes | Telemetry field to evaluate |
| condition | string | Yes | Comparison: '>', '<', '>=', '<=', '==', '!=' |
| threshold | float | Yes | Value to compare against |
| device_ids | array | Yes* | Array of device IDs (if scope='selected_devices') |
| notification_channels | array | Yes | ['email', 'webhook'] |
| cooldown_minutes | integer | Yes | Minimum time between alerts |

---

### 4.4 Update Rule

```
PUT /api/v1/rules/{rule_id}
```

**Description:** Update an existing rule.

---

### 4.5 Update Rule Status

```
PATCH /api/v1/rules/{rule_id}/status
```

**Description:** Pause or activate a rule.

**Request Body:**
```json
{
  "status": "paused"
}
```

**Status Values:** 'active', 'paused'

---

### 4.6 Delete Rule

```
DELETE /api/v1/rules/{rule_id}
```

**Description:** Delete a rule permanently.

---

### 4.7 Evaluate Rules

```
POST /api/v1/rules/evaluate
```

**Description:** Manually trigger rule evaluation (usually called by data service).

**Request Body:**
```json
{
  "device_id": "D1",
  "telemetry": {
    "temperature": 85.0,
    "pressure": 5.5
  }
}
```

---

## 5. Alert APIs

**Base URL:** `/api/v1/alerts`

### 5.1 List Alerts

```
GET /api/v1/alerts
```

**Description:** Get all alerts with optional filtering.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| tenant_id | string | Filter by tenant |
| device_id | string | Filter by device |
| rule_id | UUID | Filter by rule |
| status | string | Filter by status ('triggered', 'acknowledged') |
| page | integer | Page number |
| page_size | integer | Items per page |

---

### 5.2 Acknowledge Alert

```
PATCH /api/v1/alerts/{alert_id}/acknowledge
```

**Description:** Acknowledge an alert.

**Request Body:**
```json
{
  "acknowledged_by": "operator@example.com"
}
```

---

### 5.3 Resolve Alert

```
PATCH /api/v1/alerts/{alert_id}/resolve
```

**Description:** Mark an alert as resolved.

---

## 6. Common Response Formats

### 6.1 Success Response

```json
{
  "success": true,
  "data": { ... }
}
```

### 6.2 List Response

```json
{
  "success": true,
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### 6.3 Error Response

```json
{
  "success": false,
  "error": {
    "code": "DEVICE_NOT_FOUND",
    "message": "Device with ID 'D1' not found"
  },
  "timestamp": "2026-02-22T15:30:00Z"
}
```

---

## 7. Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 500 | Internal Server Error |

### Common Error Codes

| Code | Description |
|------|-------------|
| DEVICE_NOT_FOUND | Device doesn't exist |
| RULE_NOT_FOUND | Rule doesn't exist |
| VALIDATION_ERROR | Invalid input data |
| HEALTH_CONFIG_NOT_FOUND | Health config doesn't exist |
| SHIFT_NOT_FOUND | Shift doesn't exist |

---

## 8. UI Integration Notes

### Frontend API Proxy

The Next.js frontend proxies API requests:

| Frontend Path | Backend Service |
|---------------|-----------------|
| `/api/devices/*` | device-service:8000 |
| `/api/telemetry/*` | data-service:8081 |
| `/api/rules/*` | rule-engine-service:8002 |

### Example: Fetching Devices in UI

```javascript
// Using fetch
const response = await fetch('/api/devices');
const data = await response.json();

// Using the API helper
import { getDevices } from '@/lib/deviceApi';
const devices = await getDevices();
```

### Example: Creating a Device

```javascript
const response = await fetch('/api/devices', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    device_id: 'D5',
    device_name: 'New Device',
    device_type: 'sensor',
    location: 'Building A'
  })
});
```

---

## 9. WebSocket (Optional)

For real-time updates, the platform supports WebSocket connections:

**Endpoint:** `/ws/telemetry`

```javascript
const ws = new WebSocket('ws://localhost:3000/ws/telemetry');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New telemetry:', data);
};
```

---

**End of API Contract**
