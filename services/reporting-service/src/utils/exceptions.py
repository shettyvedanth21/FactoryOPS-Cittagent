"""Custom exceptions for Reporting Service."""


class ReportingServiceError(Exception):
    """Base exception for Reporting Service."""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "REPORTING_ERROR"


class ReportGenerationError(ReportingServiceError):
    """Raised when report generation fails."""
    
    def __init__(self, message: str, job_id: str = None):
        super().__init__(message, "REPORT_GENERATION_ERROR")
        self.job_id = job_id


class DatasetLoadError(ReportingServiceError):
    """Raised when loading dataset from S3 fails."""
    
    def __init__(self, message: str, device_id: str = None, s3_key: str = None):
        super().__init__(message, "DATASET_LOAD_ERROR")
        self.device_id = device_id
        self.s3_key = s3_key


class AnalyticsLoadError(ReportingServiceError):
    """Raised when loading analytics results fails."""
    
    def __init__(self, message: str, device_id: str = None, analysis_type: str = None):
        super().__init__(message, "ANALYTICS_LOAD_ERROR")
        self.device_id = device_id
        self.analysis_type = analysis_type


class FileGenerationError(ReportingServiceError):
    """Raised when generating output file fails."""
    
    def __init__(self, message: str, format_type: str = None):
        super().__init__(message, "FILE_GENERATION_ERROR")
        self.format_type = format_type


class ReportNotFoundError(ReportingServiceError):
    """Raised when requested report is not found."""
    
    def __init__(self, message: str, job_id: str = None):
        super().__init__(message, "REPORT_NOT_FOUND")
        self.job_id = job_id


class ValidationError(ReportingServiceError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class S3Error(ReportingServiceError):
    """Raised when S3 operation fails."""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "S3_ERROR")
        self.operation = operation


class DatabaseError(ReportingServiceError):
    """Raised when database operation fails."""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message, "DATABASE_ERROR")
        self.operation = operation