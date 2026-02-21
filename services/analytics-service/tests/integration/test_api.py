"""Integration tests for API endpoints."""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.main import create_app
from src.models.schemas import AnalyticsType


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_liveness_probe(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "analytics-service"
    
    def test_readiness_probe(self, client):
        """Test readiness probe endpoint."""
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data


class TestAnalyticsEndpoints:
    """Tests for analytics API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_submit_analytics_job(self, client):
        """Test submitting analytics job."""
        request_data = {
            "device_id": "D1",
            "start_time": (datetime.now() - timedelta(days=7)).isoformat(),
            "end_time": datetime.now().isoformat(),
            "analysis_type": "anomaly",
            "model_name": "isolation_forest",
            "parameters": {
                "contamination": 0.1,
            },
        }
        
        response = client.post("/api/v1/analytics/run", json=request_data)
        
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
    
    def test_get_supported_models(self, client):
        """Test getting supported models."""
        response = client.get("/api/v1/analytics/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "anomaly_detection" in data
        assert "failure_prediction" in data
        assert "forecasting" in data
        
        # Check specific models
        assert "isolation_forest" in data["anomaly_detection"]
        assert "random_forest" in data["failure_prediction"]
        assert "prophet" in data["forecasting"]
    
    def test_invalid_model_for_analysis_type(self, client):
        """Test validation of model for analysis type."""
        request_data = {
            "device_id": "D1",
            "start_time": (datetime.now() - timedelta(days=7)).isoformat(),
            "end_time": datetime.now().isoformat(),
            "analysis_type": "anomaly",
            "model_name": "prophet",  # Invalid - prophet is for forecasting
        }
        
        response = client.post("/api/v1/analytics/run", json=request_data)
        
        assert response.status_code == 422  # Validation error
