"""Main application entry point for Reporting Service."""

import asyncio
import signal
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.repositories.analytics_repository import AnalyticsRepository
from src.repositories.s3_repository import S3Repository
from src.services.analytics_loader import AnalyticsResultLoader
from src.services.file_generator import FileGenerator
from src.services.report_builder import ReportBuilder
from src.services.s3_loader import S3DatasetLoader
from src.handlers import health, reports
from src.utils.logging_config import configure_logging, get_logger

logger = get_logger(__name__)

# Global service instances
analytics_repo: AnalyticsRepository = None
s3_repo: S3Repository = None
report_builder: ReportBuilder = None


async def initialize_services():
    """Initialize all service dependencies."""
    global analytics_repo, s3_repo, report_builder
    
    logger.info("Initializing services...")
    
    # Initialize repositories
    analytics_repo = AnalyticsRepository()
    await analytics_repo.connect()
    
    s3_repo = S3Repository()
    
    # Initialize services
    s3_loader = S3DatasetLoader(s3_repo)
    analytics_loader = AnalyticsResultLoader(analytics_repo)
    file_generator = FileGenerator()
    
    # Initialize report builder
    report_builder = ReportBuilder(
        s3_loader=s3_loader,
        analytics_loader=analytics_loader,
        file_generator=file_generator,
        s3_repository=s3_repo
    )
    
    # Set handlers' dependencies
    health.set_analytics_repository(analytics_repo)
    reports.set_report_builder(report_builder)
    
    logger.info("Services initialized successfully")


async def shutdown_services():
    """Gracefully shutdown all services."""
    logger.info("Shutting down services...")
    
    if analytics_repo:
        await analytics_repo.disconnect()
    
    logger.info("Services shutdown complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    configure_logging()
    await initialize_services()
    
    yield
    
    # Shutdown
    await shutdown_services()


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Reporting Service",
        description="Energy Intelligence & Analytics Platform - Report Generation Service",
        version=settings.service_version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router)
    app.include_router(reports.router)
    
    return app


app = create_app()


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "docs": "/docs"
    }


async def graceful_shutdown(sig):
    """Handle graceful shutdown signals."""
    logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")
    await shutdown_services()
    asyncio.get_event_loop().stop()


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(graceful_shutdown(s))
        )


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    configure_logging()
    
    # Setup signal handlers
    setup_signal_handlers()
    
    logger.info(
        f"Starting {settings.service_name} v{settings.service_version}",
        host=settings.host,
        port=settings.port,
        environment=settings.environment
    )
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development"
    )