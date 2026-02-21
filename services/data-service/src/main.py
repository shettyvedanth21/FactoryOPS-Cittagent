
"""
Data Service Main Application

Entry point for the Data Service that handles telemetry ingestion,
validation, enrichment, and persistence.
"""

# ✅ PERMANENT FIX FOR direct execution
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --------------------------------------------------

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.handlers import MQTTHandler
from src.services import TelemetryService
from src.api import create_router, create_websocket_router
from src.utils import configure_logging, get_logger


configure_logging(settings.log_level)
logger = get_logger(__name__)


class ApplicationState:
    """Global application state management."""

    def __init__(self):
        self.telemetry_service: TelemetryService | None = None
        self.mqtt_handler: MQTTHandler | None = None
        self._shutdown_event = asyncio.Event()

    async def startup(self) -> None:
        logger.info(
            "Starting Data Service",
            version=settings.app_version,
            environment=settings.environment,
        )

        self.telemetry_service = TelemetryService()
        await self.telemetry_service.start()

        self.mqtt_handler = MQTTHandler(
            telemetry_service=self.telemetry_service,
        )
        self.mqtt_handler.connect()

        logger.info("Data Service startup complete")

    async def shutdown(self) -> None:
        logger.info("Shutting down Data Service...")

        if self.mqtt_handler:
            self.mqtt_handler.disconnect()

        if self.telemetry_service:
            await self.telemetry_service.close()

        self._shutdown_event.set()

        logger.info("Data Service shutdown complete")

    async def wait_for_shutdown(self) -> None:
        await self._shutdown_event.wait()


app_state = ApplicationState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await app_state.startup()
    yield
    await app_state.shutdown()


def create_application() -> FastAPI:
    app = FastAPI(
        title="Data Service",
        description="Telemetry ingestion, validation, and persistence service",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ✅ SINGLE REST API ROUTER
    api_router = create_router()
    app.include_router(api_router)

    # ✅ WebSocket routes
    ws_router = create_websocket_router()
    app.include_router(ws_router)

    return app


def handle_signal(sig: int, frame) -> None:
    logger.info("Received shutdown signal", signal=sig)
    asyncio.create_task(app_state.shutdown())


app = create_application()


@app.get("/")
async def root():
    return {
        "service": "Data Service",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting Data Service server",
        host=settings.host,
        port=settings.port,
    )

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )