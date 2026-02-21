"""Unit tests for analytics pipelines."""

import numpy as np
import pandas as pd
import pytest

from src.services.analytics.anomaly_detection import AnomalyDetectionPipeline
from src.services.analytics.failure_prediction import FailurePredictionPipeline
from src.services.analytics.feature_engineering import FeatureEngineer
from src.services.analytics.forecasting import ForecastingPipeline


class TestFeatureEngineer:
    """Tests for feature engineering."""
    
    def test_engineer_features_adds_time_features(self):
        """Test that time features are added."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": [230.0] * 100,
            "current": [0.85] * 100,
            "power": [195.0] * 100,
            "temperature": [45.0] * 100,
        })
        
        engineer = FeatureEngineer()
        result = engineer.engineer_features(df, ["voltage", "current", "power", "temperature"])
        
        assert "hour" in result.columns
        assert "day_of_week" in result.columns
        assert "is_weekend" in result.columns
    
    def test_engineer_features_adds_rolling_stats(self):
        """Test that rolling statistics are added."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": [230.0] * 100,
            "current": [0.85] * 100,
            "power": [195.0] * 100,
            "temperature": [45.0] * 100,
        })
        
        engineer = FeatureEngineer()
        result = engineer.engineer_features(df, ["voltage"])
        
        assert "voltage_rolling_mean" in result.columns
        assert "voltage_rolling_std" in result.columns
    
    def test_engineer_features_calculates_power_factor(self):
        """Test that power factor is calculated."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": [230.0] * 100,
            "current": [0.85] * 100,
            "power": [195.0] * 100,
            "temperature": [45.0] * 100,
        })
        
        engineer = FeatureEngineer()
        result = engineer.engineer_features(df, ["voltage", "current", "power"])
        
        assert "power_factor" in result.columns
        assert result["power_factor"].max() <= 1.0
        assert result["power_factor"].min() >= 0.0


class TestAnomalyDetectionPipeline:
    """Tests for anomaly detection pipeline."""
    
    def test_prepare_data_splits_correctly(self):
        """Test data preparation and splitting."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": np.random.normal(230, 5, 100),
            "current": np.random.normal(0.85, 0.1, 100),
            "power": np.random.normal(195, 20, 100),
            "temperature": np.random.normal(45, 5, 100),
        })
        
        pipeline = AnomalyDetectionPipeline()
        train_df, test_df = pipeline.prepare_data(df, {"features": ["voltage", "current", "power", "temperature"]})
        
        assert len(train_df) == 70  # 70% of 100
        assert len(test_df) == 30   # 30% of 100
    
    def test_isolation_forest_training(self):
        """Test Isolation Forest model training."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": np.random.normal(230, 5, 100),
            "current": np.random.normal(0.85, 0.1, 100),
            "power": np.random.normal(195, 20, 100),
            "temperature": np.random.normal(45, 5, 100),
        })
        
        pipeline = AnomalyDetectionPipeline()
        train_df, _ = pipeline.prepare_data(df, {"features": ["voltage", "current", "power", "temperature"]})
        
        model = pipeline.train(train_df, "isolation_forest", {})
        
        assert "model" in model
        assert "scaler" in model
        assert "feature_cols" in model
    
    def test_isolation_forest_prediction(self):
        """Test Isolation Forest prediction."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": np.random.normal(230, 5, 100),
            "current": np.random.normal(0.85, 0.1, 100),
            "power": np.random.normal(195, 20, 100),
            "temperature": np.random.normal(45, 5, 100),
        })
        
        pipeline = AnomalyDetectionPipeline()
        train_df, test_df = pipeline.prepare_data(df, {"features": ["voltage", "current", "power", "temperature"]})
        
        model = pipeline.train(train_df, "isolation_forest", {})
        results = pipeline.predict(test_df, model, {})
        
        assert "is_anomaly" in results
        assert "anomaly_score" in results
        assert "total_anomalies" in results
        assert len(results["is_anomaly"]) == len(test_df)


class TestFailurePredictionPipeline:
    """Tests for failure prediction pipeline."""
    
    def test_prepare_data_creates_labels(self):
        """Test that failure labels are created."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": [230.0] * 100,
            "current": [0.85] * 100,
            "power": [195.0] * 100,
            "temperature": [45.0] * 100,
        })
        # Add some failure conditions
        df.loc[0:5, "temperature"] = 80.0
        
        pipeline = FailurePredictionPipeline()
        train_df, test_df = pipeline.prepare_data(df, {})
        
        assert "failure" in train_df.columns
        assert train_df["failure"].dtype == int
    
    def test_random_forest_training(self):
        """Test Random Forest model training."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": np.random.normal(230, 5, 100),
            "current": np.random.normal(0.85, 0.1, 100),
            "power": np.random.normal(195, 20, 100),
            "temperature": np.random.normal(45, 5, 100),
        })
        
        pipeline = FailurePredictionPipeline()
        train_df, _ = pipeline.prepare_data(df, {})
        
        model = pipeline.train(train_df, "random_forest", {})
        
        assert "model" in model
        assert "scaler" in model
    
    def test_failure_probability_prediction(self):
        """Test failure probability prediction."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="5min"),
            "voltage": np.random.normal(230, 5, 100),
            "current": np.random.normal(0.85, 0.1, 100),
            "power": np.random.normal(195, 20, 100),
            "temperature": np.random.normal(45, 5, 100),
        })
        
        pipeline = FailurePredictionPipeline()
        train_df, test_df = pipeline.prepare_data(df, {})
        
        model = pipeline.train(train_df, "random_forest", {})
        results = pipeline.predict(test_df, model, {})
        
        assert "failure_probability" in results
        assert "predicted_failure" in results
        assert "time_to_failure_hours" in results


class TestForecastingPipeline:
    """Tests for forecasting pipeline."""
    
    def test_prophet_training(self):
        """Test Prophet model training."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="H"),
            "power": [195.0 + (i % 10) for i in range(100)],
        })
        
        pipeline = ForecastingPipeline()
        train_df, _ = pipeline.prepare_data(df, {})
        
        model = pipeline.train(train_df, "prophet", {})
        
        assert "model" in model
    
    def test_prophet_forecast(self):
        """Test Prophet forecast generation."""
        df = pd.DataFrame({
            "_time": pd.date_range(start="2024-01-01", periods=100, freq="H"),
            "power": [195.0 + (i % 10) for i in range(100)],
        })
        
        pipeline = ForecastingPipeline()
        train_df, test_df = pipeline.prepare_data(df, {})
        
        model = pipeline.train(train_df, "prophet", {})
        results = pipeline.predict(test_df, model, {"forecast_periods": 10})
        
        assert "forecast" in results
        assert len(results["forecast"]) > 0
