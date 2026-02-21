"""Device Service - Energy Intelligence Platform.

This module initializes the FastAPI application with all required configurations.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.database import engine
from app.logging_config import configure_logging
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for graceful startup and shutdown."""
    # Startup
    configure_logging()
    logger.info(
        "Starting Device Service",
        extra={
            "service": "device-service",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down Device Service - closing database connections")
    await engine.dispose()
    logger.info("Device Service shutdown complete")


app = FastAPI(
    title="Device Service",
    description="Energy Intelligence Platform - Device Management Service",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "device-service",
            "version": settings.APP_VERSION,
        },
        status_code=200
    )


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint for Kubernetes probes."""
    try:
        # Check database connectivity
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        return JSONResponse(
            content={
                "status": "ready",
                "service": "device-service",
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            content={
                "status": "not_ready",
                "service": "device-service",
                "error": str(e),
            },
            status_code=503
        )
