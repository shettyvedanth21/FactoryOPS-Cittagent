"""Structured logging configuration."""

import logging
import sys
from typing import Any, Dict

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


def log_telemetry_processed(
    logger: structlog.stdlib.BoundLogger,
    device_id: str,
    correlation_id: str,
    enrichment_status: str,
    **kwargs: Any,
) -> None:
    """
    Log successful telemetry processing.
    
    Args:
        logger: Logger instance
        device_id: Device identifier
        correlation_id: Request correlation ID
        enrichment_status: Metadata enrichment status
        **kwargs: Additional dynamic fields
    """
    log_data = {
        "device_id": device_id,
        "correlation_id": correlation_id,
        "enrichment_status": enrichment_status,
    }
    log_data.update(kwargs)
    
    logger.info(
        "Telemetry processed successfully",
        **log_data,
    )


def log_telemetry_error(
    logger: structlog.stdlib.BoundLogger,
    device_id: str,
    correlation_id: str,
    error_type: str,
    error_message: str,
    payload: Dict[str, Any],
) -> None:
    """
    Log telemetry processing error.
    
    Args:
        logger: Logger instance
        device_id: Device identifier
        correlation_id: Request correlation ID
        error_type: Error classification
        error_message: Error details
        payload: Original payload
    """
    logger.error(
        "Telemetry processing failed",
        device_id=device_id,
        correlation_id=correlation_id,
        error_type=error_type,
        error_message=error_message,
        payload=payload,
    )
