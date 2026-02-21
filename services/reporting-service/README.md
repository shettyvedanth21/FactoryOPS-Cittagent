# Reporting Service

Energy Intelligence & Analytics Platform - Reporting Service

## Overview

The Reporting Service generates downloadable reports (PDF, Excel, JSON) from:
- S3 exported datasets (from data-export-service)
- Analytics results (from analytics-service)

## Architecture

This service follows the microservice architecture defined in the project LLD:
- **Does NOT** read from InfluxDB directly
- **Does NOT** call data-service
- **Does NOT** run ML models
- **Does NOT** evaluate rules

## Data Sources

1. **S3 Datasets**: Exported telemetry data from data-export-service
2. **Analytics Results**: Stored in PostgreSQL by analytics-service

## API Endpoints

- `POST /api/reports/generate` - Generate a new report
- `GET /api/reports/status/{job_id}` - Check report generation status
- `GET /api/reports/download/{job_id}` - Download generated report
- `GET /health` - Health check endpoint

## Report Formats

- PDF (using ReportLab)
- Excel (using openpyxl)
- JSON (raw data export)

## Development

### Setup

```bash
cd services/reporting-service
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### Running

```bash
python -m src.main
```

Or with uvicorn directly:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8085 --reload
```

### Environment Variables

See `src/config.py` for all configuration options.

## Project Structure

```
services/reporting-service/
├── src/
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration settings
│   ├── models/                 # Pydantic models
│   ├── handlers/               # API route handlers
│   ├── services/               # Business logic
│   ├── repositories/           # Data access layer
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── requirements.txt
└── README.md
```

## License

Private - Energy Intelligence Platform