"""Unit tests for job runner."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pandas as pd

from src.models.schemas import AnalyticsRequest, AnalyticsType, JobStatus
from src.services.job_runner import JobRunner
from src.utils.exceptions import DatasetNotFoundError


class TestJobRunner:
    """Tests for JobRunner."""
    
    @pytest.fixture
    def job_runner(self, mock_s3_client, mock_result_repository):
        """Create JobRunner instance with mocks."""
        from src.services.dataset_service import DatasetService
        
        dataset_service = DatasetService(mock_s3_client)
        return JobRunner(dataset_service, mock_result_repository)
    
    @pytest.mark.asyncio
    async def test_run_job_success(self, job_runner, mock_result_repository, sample_telemetry_data):
        """Test successful job execution."""
        # Mock dataset loading
        job_runner._dataset_service.load_dataset = AsyncMock(return_value=sample_telemetry_data)
        
        request = AnalyticsRequest(
            device_id="D1",
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now(),
            analysis_type=AnalyticsType.ANOMALY,
            model_name="isolation_forest",
        )
        
        await job_runner.run_job("test-job-123", request)
        
        # Verify status updates
        assert mock_result_repository.update_job_status.called
        assert mock_result_repository.save_results.called
        
        # Verify job was marked completed
        final_call = mock_result_repository.update_job_status.call_args_list[-1]
        assert final_call.kwargs["status"] == JobStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_run_job_dataset_not_found(self, job_runner, mock_result_repository):
        """Test job failure when dataset not found."""
        job_runner._dataset_service.load_dataset = AsyncMock(
            side_effect=DatasetNotFoundError("Dataset not found")
        )
        
        request = AnalyticsRequest(
            device_id="D1",
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now(),
            analysis_type=AnalyticsType.ANOMALY,
            model_name="isolation_forest",
        )
        
        with pytest.raises(Exception):
            await job_runner.run_job("test-job-123", request)
    
    @pytest.mark.asyncio
    async def test_run_job_updates_progress(self, job_runner, mock_result_repository, sample_telemetry_data):
        """Test that job progress is updated during execution."""
        job_runner._dataset_service.load_dataset = AsyncMock(return_value=sample_telemetry_data)
        
        request = AnalyticsRequest(
            device_id="D1",
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now(),
            analysis_type=AnalyticsType.ANOMALY,
            model_name="isolation_forest",
        )
        
        await job_runner.run_job("test-job-123", request)
        
        # Verify progress updates were called
        assert mock_result_repository.update_job_progress.called
        
        # Check that progress increases
        progress_calls = [
            call for call in mock_result_repository.update_job_progress.call_args_list
        ]
        assert len(progress_calls) > 0
