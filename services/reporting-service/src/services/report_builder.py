"""Report builder service - orchestrates report generation."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd

from src.models.report import (
    AnalysisType, GenerateReportRequest, ReportFormat, ReportStatus
)
from src.repositories.analytics_repository import AnalyticsRepository
from src.repositories.s3_repository import S3Repository
from src.services.analytics_loader import AnalyticsResultLoader
from src.services.file_generator import FileGenerator
from src.services.s3_loader import S3DatasetLoader
from src.utils.exceptions import ReportGenerationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ReportJob:
    """Represents a report generation job."""
    
    def __init__(self, job_id: str, request: GenerateReportRequest):
        self.job_id = job_id
        self.request = request
        self.status = ReportStatus.PENDING
        self.progress_percent = 0
        self.message = "Job queued"
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.s3_key: Optional[str] = None
        self.file_size_bytes: Optional[int] = None


class ReportBuilder:
    """Service for building comprehensive reports."""
    
    def __init__(
        self,
        s3_loader: S3DatasetLoader,
        analytics_loader: AnalyticsResultLoader,
        file_generator: FileGenerator,
        s3_repository: S3Repository
    ):
        """Initialize report builder.
        
        Args:
            s3_loader: S3 dataset loader
            analytics_loader: Analytics result loader
            file_generator: File generator
            s3_repository: S3 repository for uploads
        """
        self.s3_loader = s3_loader
        self.analytics_loader = analytics_loader
        self.file_generator = file_generator
        self.s3_repository = s3_repository
        
        # In-memory job store (in production, use Redis or database)
        self._jobs: Dict[str, ReportJob] = {}
    
    async def create_job(self, request: GenerateReportRequest) -> ReportJob:
        """Create a new report generation job.
        
        Args:
            request: Report generation request
            
        Returns:
            Created report job
        """
        job_id = str(uuid.uuid4())
        job = ReportJob(job_id, request)
        self._jobs[job_id] = job
        
        logger.info(
            "Created report job",
            job_id=job_id,
            device_count=len(request.device_ids),
            format=request.format.value
        )
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[ReportJob]:
        """Get a report job by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Report job if found, None otherwise
        """
        return self._jobs.get(job_id)
    
    async def generate_report(self, job_id: str) -> None:
        """Generate a report for the given job.
        
        This is the main orchestration method that:
        1. Loads telemetry data from S3
        2. Loads analytics results
        3. Generates the report file
        4. Uploads to S3
        
        Args:
            job_id: Job identifier
            
        Raises:
            ReportGenerationError: If generation fails
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ReportGenerationError(f"Job not found: {job_id}", job_id=job_id)
        
        try:
            job.status = ReportStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.message = "Loading telemetry data"
            job.progress_percent = 10
            
            logger.info("Starting report generation", job_id=job_id)
            
            # Determine device IDs
            device_ids = job.request.device_ids
            if device_ids == ["all"]:
                # In production, query device service for all active devices
                device_ids = ["D1"]  # Phase-1 default
            
            # Load telemetry data from S3
            telemetry_data = await self._load_telemetry_data(
                device_ids, job.request.start_time, job.request.end_time
            )
            job.progress_percent = 30
            
            # Load analytics results
            job.message = "Loading analytics results"
            anomaly_data, prediction_data, forecast_data = await self._load_analytics_data(
                device_ids, job.request.start_time, job.request.end_time,
                job.request.analysis_types
            )
            job.progress_percent = 60
            
            # Calculate summary statistics
            job.message = "Calculating summaries"
            summary = self._calculate_summary(
                device_ids, telemetry_data, anomaly_data, prediction_data, forecast_data
            )
            job.progress_percent = 80
            
            # Generate report file
            job.message = "Generating report file"
            report_metadata = {
                "job_id": job_id,
                "title": "Energy Intelligence Report",
                "device_ids": device_ids,
                "start_time": job.request.start_time.isoformat(),
                "end_time": job.request.end_time.isoformat(),
                "generated_at": datetime.utcnow().isoformat(),
                "analysis_types": [at.value for at in job.request.analysis_types]
            }
            
            report_bytes = await self.file_generator.generate(
                job.request.format,
                telemetry_data,
                anomaly_data,
                prediction_data,
                forecast_data,
                summary,
                report_metadata
            )
            job.progress_percent = 90
            
            # Upload to S3
            job.message = "Uploading report"
            s3_key = await self.s3_repository.upload_report(
                job_id, report_bytes, job.request.format.value
            )
            
            # Update job status
            job.status = ReportStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.s3_key = s3_key
            job.file_size_bytes = len(report_bytes)
            job.progress_percent = 100
            job.message = "Report generated successfully"
            
            logger.info(
                "Report generation completed",
                job_id=job_id,
                s3_key=s3_key,
                file_size=len(report_bytes)
            )
            
        except Exception as e:
            logger.error("Report generation failed", job_id=job_id, error=str(e))
            job.status = ReportStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            raise ReportGenerationError(f"Report generation failed: {str(e)}", job_id=job_id)
    
    async def _load_telemetry_data(
        self,
        device_ids: list,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Load telemetry data for devices."""
        all_data = []
        
        for device_id in device_ids:
            try:
                df = await self.s3_loader.load_device_datasets(
                    device_id, start_time, end_time
                )
                if not df.empty:
                    all_data.append(df)
            except Exception as e:
                logger.warning(
                    "Failed to load telemetry for device",
                    device_id=device_id,
                    error=str(e)
                )
                continue
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    
    async def _load_analytics_data(
        self,
        device_ids: list,
        start_time: datetime,
        end_time: datetime,
        analysis_types: list
    ):
        """Load analytics data based on requested types."""
        anomaly_data = pd.DataFrame()
        prediction_data = pd.DataFrame()
        forecast_data = pd.DataFrame()
        
        include_all = AnalysisType.ALL in analysis_types
        
        # Load anomalies
        if include_all or AnalysisType.ANOMALY in analysis_types:
            try:
                anomaly_data = await self.analytics_loader.load_anomaly_results(
                    device_ids, start_time, end_time
                )
            except Exception as e:
                logger.warning("Failed to load anomaly results", error=str(e))
        
        # Load predictions
        if include_all or AnalysisType.PREDICTION in analysis_types:
            try:
                prediction_data = await self.analytics_loader.load_prediction_results(
                    device_ids, start_time, end_time
                )
            except Exception as e:
                logger.warning("Failed to load prediction results", error=str(e))
        
        # Load forecasts
        if include_all or AnalysisType.FORECAST in analysis_types:
            try:
                forecast_data = await self.analytics_loader.load_forecast_results(
                    device_ids, start_time, end_time
                )
            except Exception as e:
                logger.warning("Failed to load forecast results", error=str(e))
        
        return anomaly_data, prediction_data, forecast_data
    
    def _calculate_summary(
        self,
        device_ids: list,
        telemetry_data: pd.DataFrame,
        anomaly_data: pd.DataFrame,
        prediction_data: pd.DataFrame,
        forecast_data: pd.DataFrame
    ) -> dict:
        """Calculate comprehensive summary statistics."""
        # Telemetry summary
        telemetry_summary = self.s3_loader.calculate_summary_stats(telemetry_data)
        
        # Anomaly summary
        anomaly_summary = self.analytics_loader.calculate_anomaly_summary(anomaly_data)
        
        # Prediction summary
        prediction_summary = self.analytics_loader.calculate_prediction_summary(prediction_data)
        
        return {
            "total_devices": len(device_ids),
            "total_records": telemetry_summary.get("total_records", 0),
            "telemetry_summary": telemetry_summary,
            "anomaly_summary": anomaly_summary,
            "prediction_summary": prediction_summary,
            "forecast_count": len(forecast_data)
        }
    
    async def get_download_url(self, job_id: str, expiration: int = 3600) -> Optional[str]:
        """Get presigned download URL for a completed report.
        
        Args:
            job_id: Job identifier
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL if report is complete, None otherwise
        """
        job = self._jobs.get(job_id)
        if not job or job.status != ReportStatus.COMPLETED or not job.s3_key:
            return None
        
        return await self.s3_repository.generate_presigned_url(job.s3_key, expiration)