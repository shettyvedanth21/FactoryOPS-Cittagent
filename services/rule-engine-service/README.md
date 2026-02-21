# Rule Engine Service

Real-time rule evaluation service for the Energy Intelligence Platform.

## Overview

The Rule Engine Service provides:
- Rule management APIs (CRUD operations)
- Real-time telemetry evaluation
- Multi-device rule support
- Notification orchestration
- Cooldown management

## Architecture

### Multi-Device Support

Rules can be configured for:
- **All devices** (`scope: all_devices`): Applies to every device in the system
- **Selected devices** (`scope: selected_devices`): Applies to specific device IDs

### Rule Evaluation Flow

1. Data Service receives telemetry from MQTT
2. Data Service sends telemetry to Rule Engine via `/api/v1/rules/evaluate`
3. Rule Engine fetches all active rules applicable to the device
4. Each rule is evaluated against the telemetry data
5. If triggered:
   - An alert is created in the database
   - Notifications are sent through configured channels
   - Rule's `last_triggered_at` is updated for cooldown

### Notification Channels

- **Email**: AWS SES (placeholder)
- **WhatsApp**: Twilio (placeholder)
- **Telegram**: Bot API (placeholder)

## API Endpoints

### Rule Management

- `GET /api/v1/rules` - List all rules
- `GET /api/v1/rules/{rule_id}` - Get rule by ID
- `POST /api/v1/rules` - Create new rule
- `PUT /api/v1/rules/{rule_id}` - Update rule
- `PATCH /api/v1/rules/{rule_id}/status` - Pause/resume rule
- `DELETE /api/v1/rules/{rule_id}` - Delete rule

### Rule Evaluation

- `POST /api/v1/rules/evaluate` - Evaluate telemetry against rules

### Health Checks

- `GET /health` - Health check
- `GET /ready` - Readiness check

## Database Schema

### Rules Table

```sql
CREATE TABLE rules (
    rule_id UUID PRIMARY KEY,
    tenant_id VARCHAR(50) NULL,  -- Multi-tenancy support
    rule_name VARCHAR(255) NOT NULL,
    description TEXT,
    scope VARCHAR(50) NOT NULL,  -- 'all_devices' or 'selected_devices'
    device_ids JSON,    -- Array of device IDs
    property VARCHAR(100) NOT NULL,  -- 'temperature', 'voltage', etc.
    condition VARCHAR(20) NOT NULL,  -- '>', '<', '=', etc.
    threshold FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'active', 'paused', 'archived'
    notification_channels JSON,
    cooldown_minutes INTEGER DEFAULT 15,
    last_triggered_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP
);
```

### Alerts Table

```sql
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY,
    tenant_id VARCHAR(50) NULL,
    rule_id UUID REFERENCES rules(rule_id),
    device_id VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    actual_value FLOAT NOT NULL,
    threshold_value FLOAT NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
);
```

## Configuration

Environment variables:

```bash
# Application
APP_NAME=rule-engine-service
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=false

# Database
DATABASE_URL=mysql+aiomysql://energy:energy@localhost:3306/energy_rule_db

# Logging
LOG_LEVEL=INFO

# Rule Engine
RULE_EVALUATION_TIMEOUT=5
NOTIFICATION_COOLDOWN_MINUTES=15
```

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the service
python main.py
```

## Development

### Code Structure

```
app/
├── __init__.py           # FastAPI app initialization
├── config.py             # Configuration management
├── database.py           # Database setup
├── logging_config.py     # Structured logging
├── models/
│   └── rule.py          # SQLAlchemy models
├── schemas/
│   └── rule.py          # Pydantic schemas
├── repositories/
│   └── rule.py          # Data access layer
├── services/
│   ├── rule.py          # Rule business logic
│   └── evaluator.py     # Rule evaluation engine
├── api/
│   └── v1/
│       ├── router.py    # API router
│       ├── rules.py     # Rule endpoints
│       └── evaluation.py # Evaluation endpoints
└── notifications/
    └── adapter.py       # Notification adapters
```

## License

Proprietary - Energy Intelligence Platform
