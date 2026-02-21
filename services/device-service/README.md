# Device Service

Energy Intelligence Platform - Device Management Service

## Overview

This service provides device metadata CRUD operations for the Energy Intelligence Platform. It's built with Python 3.11, FastAPI, and SQLAlchemy async.

## Features

- **Device CRUD**: Create, read, update, and delete device metadata
- **Multi-tenant Ready**: Architecture supports future multi-tenancy
- **Async Operations**: Full async/await support with aiomysql
- **Structured Logging**: JSON-formatted logs for observability
- **Health Checks**: Kubernetes-ready health and readiness endpoints
- **Database Migrations**: Alembic for schema versioning

## Technology Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async)
- aiomysql
- Pydantic v2
- Alembic
- MySQL 15+

## Project Structure

```
services/device-service/
├── app/
│   ├── __init__.py              # FastAPI app factory
│   ├── main.py                  # Entry point
│   ├── config.py                # Configuration management
│   ├── database.py              # SQLAlchemy setup
│   ├── logging_config.py        # Structured logging
│   ├── models/
│   │   ├── __init__.py
│   │   └── device.py            # Device SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── device.py            # Pydantic schemas
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── device.py            # Repository layer
│   ├── services/
│   │   ├── __init__.py
│   │   └── device.py            # Business logic
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py        # API router aggregation
│           └── devices.py       # Device endpoints
├── alembic/
│   ├── env.py                   # Alembic environment
│   ├── script.py.mako           # Migration template
│   └── versions/                # Migration files
├── requirements.txt
├── alembic.ini
└── README.md
```

## Installation

1. Create virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables (or create `.env` file):
```bash
export DATABASE_URL="mysql+aiomysql://energy:energy@localhost:3306/energy_device_db"
export LOG_LEVEL="INFO"
export ENVIRONMENT="development"
```

4. Run database migrations:
```bash
alembic upgrade head
```

## Running the Service

### Development
```bash
python main.py
```

### Production
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Checks
- `GET /health` - Health check
- `GET /ready` - Readiness probe (includes DB connectivity check)

### Device Management
- `GET /api/v1/devices` - List all devices (with pagination)
- `GET /api/v1/devices/{device_id}` - Get device by ID
- `POST /api/v1/devices` - Create new device
- `PUT /api/v1/devices/{device_id}` - Update device
- `DELETE /api/v1/devices/{device_id}` - Delete device (soft delete by default)

## API Documentation

When running in development mode, API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Migrations

### Create new migration
```bash
alembic revision --autogenerate -m "description"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback
```bash
alembic downgrade -1
```

## Device Model

The Device model includes the following fields:

- `device_id` (PK): Unique device identifier (business key)
- `tenant_id`: Multi-tenant support (nullable for Phase-1)
- `device_name`: Human-readable name
- `device_type`: Device category (e.g., bulb, compressor)
- `manufacturer`: Device manufacturer
- `model`: Device model
- `location`: Physical location
- `status`: Device status (active, inactive, maintenance, error)
- `metadata_json`: Additional metadata as JSON
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `deleted_at`: Soft delete timestamp

## Configuration

Configuration is managed through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `mysql+aiomysql://energy:energy@localhost:3306/energy_device_db` | MySQL connection string |
| `DATABASE_POOL_SIZE` | `10` | Connection pool size |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | Environment (development/production) |
| `APP_VERSION` | `1.0.0` | Application version |

## Architecture

### Layer Structure

1. **API Layer** (`app/api/`): FastAPI route handlers, request validation
2. **Service Layer** (`app/services/`): Business logic
3. **Repository Layer** (`app/repositories/`): Data access abstraction
4. **Model Layer** (`app/models/`): SQLAlchemy ORM models

### Multi-tenancy Support

The service is designed with multi-tenancy in mind:
- `tenant_id` field is present on Device model
- Repository methods accept optional `tenant_id` parameter
- API endpoints accept `tenant_id` as query parameter

For Phase-1, tenant filtering is optional (nullable). In future phases, this can be enforced via middleware or authentication context.

## License

Proprietary - Energy Intelligence Platform
