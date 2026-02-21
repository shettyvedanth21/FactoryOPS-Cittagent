"""Structured logging configuration."""

import logging
import sys
from datetime import datetime, timezone
from typing import Any

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Timestamp
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Level and logger name (safe, always present on record)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # Correlation ID (optional)
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id

        # Service name
        log_record["service"] = "data-export-service"

        # Normalize message field
        if "message" in log_record:
            log_record["msg"] = log_record.pop("message")

        # Remove noisy default fields if present
        for key in ("levelname", "name"):
            log_record.pop(key, None)


def setup_logging() -> None:
    """Configure structured JSON logging."""

    handler = logging.StreamHandler(sys.stdout)

    # IMPORTANT:
    # Do NOT use rename_fields here.
    # We control the final field names ourselves in add_fields().
    formatter = CustomJsonFormatter()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("aiobotocore").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)