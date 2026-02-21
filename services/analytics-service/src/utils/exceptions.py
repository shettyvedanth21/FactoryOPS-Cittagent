"""Custom exceptions for analytics service."""


class AnalyticsServiceError(Exception):
    """Base exception for analytics service."""
    pass


class JobNotFoundError(AnalyticsServiceError):
    """Raised when a job is not found."""
    pass


class DatasetNotFoundError(AnalyticsServiceError):
    """Raised when a dataset is not found in S3."""
    pass


class DatasetReadError(AnalyticsServiceError):
    """Raised when reading a dataset fails."""
    pass


class AnalyticsError(AnalyticsServiceError):
    """Raised when analytics processing fails."""
    pass


class ModelNotSupportedError(AnalyticsServiceError):
    """Raised when an unsupported model is requested."""
    pass


class ValidationError(AnalyticsServiceError):
    """Raised when input validation fails."""
    pass
