import asyncio
import logging
from contextlib import asynccontextmanager
from sqlalchemy import text

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings
from src.database import engine
from src.handlers import energy_router, comparison_router, tariffs_router, common_router
from src.services.influx_reader import influx_reader
from src.tasks.scheduler import start_scheduler, stop_scheduler
from src.storage.minio_client import minio_client


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up reporting-service...")
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    try:
        influx_reader.client.ping()
        logger.info("InfluxDB connection verified")
    except Exception as e:
        logger.error(f"InfluxDB connection failed: {e}")
    
    try:
        minio_client.ensure_bucket_exists()
        logger.info(f"MinIO bucket '{settings.MINIO_BUCKET}' ready")
    except Exception as e:
        logger.error(f"MinIO bucket initialization failed: {e}")
    
    try:
        scheduler = start_scheduler()
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Scheduler startup failed: {e}")
    
    yield
    
    logger.info("Shutting down reporting-service...")
    stop_scheduler()
    influx_reader.close()
    await engine.dispose()


app = FastAPI(
    title="Energy Reporting Service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_messages = []
    for error in exc.errors():
        if "Input tag" in str(error.get("msg", "")):
            continue
        loc = ".".join(str(l) for l in error.get("loc", []))
        msg = error.get("msg", "")
        error_messages.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "INVALID_DATE_RANGE",
            "message": "Reports allowed between 1 and 90 days within 1-year retention."
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # If detail is a dict (our structured error), return it as-is
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    # Otherwise, wrap it
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": str(exc.detail)
        }
    )


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    db: str
    influx: str
    minio: str


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy")


@app.get("/ready", response_model=ReadyResponse)
async def ready():
    db_status = "connected"
    influx_status = "connected"
    minio_status = "connected"
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    
    try:
        influx_reader.client.ping()
    except Exception:
        influx_status = "disconnected"
    
    return ReadyResponse(
        status="ready",
        db=db_status,
        influx=influx_status,
        minio=minio_status
    )


app.include_router(energy_router, prefix="/api/reports/energy", tags=["Energy Reports"])
app.include_router(comparison_router, prefix="/api/reports/energy/comparison", tags=["Comparison Reports"])
app.include_router(tariffs_router, prefix="/api/reports/tariffs", tags=["Tariffs"])
app.include_router(common_router, prefix="/api/reports", tags=["Reports"])
