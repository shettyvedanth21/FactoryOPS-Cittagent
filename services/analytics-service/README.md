# Analytics Service

ML Analytics Service for the Energy Intelligence Platform.

## Overview

This service provides machine learning analytics capabilities including:
- Anomaly detection (Isolation Forest, Autoencoder)
- Failure prediction (Random Forest, Gradient Boosted Trees)
- Time series forecasting (Prophet, ARIMA-style)

## Architecture

- Reads datasets exclusively from S3 (exported by Data Export Service)
- No direct InfluxDB access
- Background job processing
- Results stored in PostgreSQL

## Quick Start

```bash
# Install dependencies
poetry install

# Run the service
poetry run uvicorn src.main:app --reload

# Run tests
poetry run pytest
```

## Environment Variables

See `src/config/settings.py` for configuration options.

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
