"""Test configuration and fixtures."""

import asyncio
from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio

from src.config.settings import Settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Test settings fixture."""
    return Settings(
        app_env="test",
        log_level="DEBUG",
        mysql_database="test_energy_analytics_db",
        s3_bucket_name="test-bucket",
    )


@pytest.fixture
def sample_telemetry_data() -> pd.DataFrame:
    """Create sample telemetry data for testing."""
    timestamps = pd.date_range(
        start=datetime.now() - timedelta(days=7),
        periods=1000,
        freq="5min",
    )
    
    data = {
        "_time": timestamps,
        "device_id": ["D1"] * 1000,
        "voltage": [230.0 + (i % 10) for i in range(1000)],
        "current": [0.85 + (i % 5) * 0.01 for i in range(1000)],
        "power": [195.0 + (i % 20) for i in range(1000)],
        "temperature": [45.0 + (i % 15) for i in range(1000)],
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def mock_s3_client():
    """Mock S3 client fixture."""
    with patch("src.infrastructure.s3_client.S3Client") as mock:
        instance = mock.return_value
        instance.download_file = AsyncMock(return_value=b"mock_parquet_data")
        instance.list_objects = AsyncMock(return_value=[])
        yield instance


@pytest.fixture
def mock_result_repository():
    """Mock result repository fixture."""
    repo = MagicMock()
    repo.create_job = AsyncMock()
    repo.get_job = AsyncMock()
    repo.update_job_status = AsyncMock()
    repo.update_job_progress = AsyncMock()
    repo.save_results = AsyncMock()
    repo.list_jobs = AsyncMock(return_value=[])
    return repo
