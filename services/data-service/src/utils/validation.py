"""
Validation utilities for telemetry data.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from src.config import settings


class ValidationError(Exception):
    """Raised when telemetry validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class TelemetryValidator:
    """Validator for telemetry payloads - accepts dynamic numeric fields."""

    REQUIRED_FIELDS = [
        "device_id",
        "timestamp",
    ]

    @classmethod
    def validate_payload(
        cls,
        payload: Dict[str, Any],
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate raw payload dictionary.

        Args:
            payload: Raw telemetry payload

        Returns:
            Tuple of (is_valid, error_type, error_message)
        """
        try:
            missing_fields = cls._check_required_fields(payload)
            if missing_fields:
                return (
                    False,
                    "missing_required_fields",
                    f"Missing required fields: {missing_fields}",
                )

            timestamp_error = cls._validate_timestamp(payload.get("timestamp"))
            if timestamp_error:
                return (
                    False,
                    "invalid_timestamp",
                    timestamp_error,
                )

            numeric_errors = cls._validate_numeric_fields(payload)
            if numeric_errors:
                return (
                    False,
                    "invalid_numeric_fields",
                    f"Invalid numeric fields: {numeric_errors}",
                )

            return True, None, None

        except Exception as e:
            return False, "validation_error", str(e)

    @classmethod
    def _check_required_fields(
        cls,
        payload: Dict[str, Any],
    ) -> List[str]:
        missing: List[str] = []
        for field in cls.REQUIRED_FIELDS:
            if field not in payload:
                missing.append(field)
        return missing

    @classmethod
    def _validate_numeric_fields(
        cls,
        payload: Dict[str, Any],
    ) -> List[str]:
        """Validate that any additional fields are numeric if present."""
        errors: List[str] = []
        
        for key, value in payload.items():
            if key in cls.REQUIRED_FIELDS:
                continue
            if key == "schema_version":
                continue
            if value is None:
                continue
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append(f"{key} is not a valid number: {value}")
        
        return errors

    @classmethod
    def _validate_timestamp(
        cls,
        timestamp: Any,
    ) -> Optional[str]:
        """Validate timestamp format."""
        if timestamp is None:
            return "Timestamp is required"

        try:
            if isinstance(timestamp, str):
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elif isinstance(timestamp, (int, float)):
                datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, datetime):
                pass
            else:
                return f"Invalid timestamp type: {type(timestamp)}"
        except (ValueError, OSError) as e:
            return f"Invalid timestamp format: {e}"

        return None

    @classmethod
    def validate_and_parse(
        cls,
        payload: Dict[str, Any],
    ):
        """
        Validate and parse payload into TelemetryPayload model.

        Args:
            payload: Raw telemetry payload

        Returns:
            Validated TelemetryPayload

        Raises:
            ValidationError: If validation fails
        """
        is_valid, error_type, error_message = cls.validate_payload(payload)

        if not is_valid:
            raise ValidationError(
                error_message or "Validation failed",
                error_type,
            )

        try:
            from src.models import TelemetryPayload
            return TelemetryPayload(**payload)
        except Exception as e:
            raise ValidationError(
                f"Failed to parse payload: {e}",
                "parse_error",
            )
