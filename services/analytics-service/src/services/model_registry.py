"""Model registry for managing ML models."""

from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger()


class ModelRegistry:
    """Registry for ML model configurations and metadata."""
    
    def __init__(self):
        self._logger = logger.bind(service="ModelRegistry")
        self._model_configs = self._initialize_configs()
    
    def _initialize_configs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize model configurations."""
        return {
            # Anomaly Detection Models
            "isolation_forest": {
                "type": "anomaly",
                "library": "sklearn",
                "class": "IsolationForest",
                "default_params": {
                    "contamination": 0.1,
                    "random_state": 42,
                    "n_estimators": 100,
                },
                "supports_training": True,
                "description": "Unsupervised anomaly detection using Isolation Forest",
            },
            "autoencoder": {
                "type": "anomaly",
                "library": "sklearn",
                "class": "AutoencoderPipeline",
                "default_params": {
                    "hidden_layers": [64, 32, 16],
                    "activation": "relu",
                    "epochs": 100,
                    "batch_size": 32,
                },
                "supports_training": True,
                "description": "Deep learning anomaly detection using autoencoders",
            },
            # Failure Prediction Models
            "random_forest": {
                "type": "prediction",
                "library": "sklearn",
                "class": "RandomForestClassifier",
                "default_params": {
                    "n_estimators": 100,
                    "max_depth": 10,
                    "random_state": 42,
                },
                "supports_training": True,
                "description": "Random Forest for failure prediction",
            },
            "gradient_boosting": {
                "type": "prediction",
                "library": "sklearn",
                "class": "GradientBoostingClassifier",
                "default_params": {
                    "n_estimators": 100,
                    "learning_rate": 0.1,
                    "max_depth": 6,
                    "random_state": 42,
                },
                "supports_training": True,
                "description": "Gradient Boosted Trees for failure prediction",
            },
            # Forecasting Models
            "prophet": {
                "type": "forecast",
                "library": "prophet",
                "class": "Prophet",
                "default_params": {
                    "daily_seasonality": True,
                    "weekly_seasonality": True,
                    "yearly_seasonality": False,
                },
                "supports_training": True,
                "description": "Facebook Prophet for time series forecasting",
            },
            "arima": {
                "type": "forecast",
                "library": "statsmodels",
                "class": "ARIMA",
                "default_params": {
                    "order": [1, 1, 1],
                    "seasonal_order": [1, 1, 1, 24],
                },
                "supports_training": True,
                "description": "ARIMA model for time series forecasting",
            },
        }
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a model."""
        if model_name not in self._model_configs:
            raise ValueError(f"Unknown model: {model_name}")
        return self._model_configs[model_name]
    
    def get_default_params(self, model_name: str) -> Dict[str, Any]:
        """Get default parameters for a model."""
        config = self.get_model_config(model_name)
        return config.get("default_params", {})
    
    def merge_params(
        self,
        model_name: str,
        user_params: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Merge user parameters with defaults."""
        default_params = self.get_default_params(model_name)
        if not user_params:
            return default_params.copy()
        
        merged = default_params.copy()
        merged.update(user_params)
        return merged
    
    def list_models(self, model_type: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """List available models, optionally filtered by type."""
        if model_type:
            return {
                name: config
                for name, config in self._model_configs.items()
                if config["type"] == model_type
            }
        return self._model_configs.copy()
