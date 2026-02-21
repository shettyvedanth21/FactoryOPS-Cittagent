"""Anomaly detection pipeline implementations."""

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import structlog
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from src.services.analytics.base import BasePipeline
from src.services.analytics.feature_engineering import FeatureEngineer

logger = structlog.get_logger()


class AnomalyDetectionPipeline(BasePipeline):
    """Pipeline for anomaly detection analytics."""

    def __init__(self):
        self._logger = logger.bind(pipeline="AnomalyDetection")
        self._feature_engineer = FeatureEngineer()

    def prepare_data(
        self,
        df: pd.DataFrame,
        parameters: Optional[Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Prepare data for anomaly detection."""
        params = parameters or {}

        features = params.get(
            "features",
            ["voltage", "current", "power", "temperature"],
        )

        df = self._feature_engineer.engineer_features(df, features)

        split_idx = int(len(df) * 0.7)
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()

        return train_df, test_df

    def train(
        self,
        train_df: pd.DataFrame,
        model_name: str,
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Train anomaly detection model."""
        params = parameters or {}

        if model_name == "isolation_forest":
            return self._train_isolation_forest(train_df, params)
        elif model_name == "autoencoder":
            return self._train_autoencoder(train_df, params)
        else:
            raise ValueError(f"Unknown model: {model_name}")

    # ------------------------------------------------------------------
    # Isolation Forest
    # ------------------------------------------------------------------

    def _train_isolation_forest(
        self,
        train_df: pd.DataFrame,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:

        feature_cols = params.get(
            "feature_cols",
            ["voltage", "current", "power", "temperature"],
        )

        available_cols = [c for c in feature_cols if c in train_df.columns]
        X = train_df[available_cols].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = IsolationForest(
            contamination=params.get("contamination", 0.1),
            random_state=params.get("random_state", 42),
            n_estimators=params.get("n_estimators", 100),
        )

        model.fit(X_scaled)

        return {
            "model_type": "isolation_forest",
            "model": model,
            "scaler": scaler,
            "feature_cols": available_cols,
        }

    # ------------------------------------------------------------------
    # Autoencoder
    # ------------------------------------------------------------------

    def _train_autoencoder(
        self,
        train_df: pd.DataFrame,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:

        feature_cols = params.get(
            "feature_cols",
            ["voltage", "current", "power", "temperature"],
        )

        available_cols = [c for c in feature_cols if c in train_df.columns]
        X = train_df[available_cols].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        hidden_layers = params.get("hidden_layers", [64, 32, 16])

        model = MLPRegressor(
            hidden_layer_sizes=tuple(hidden_layers),
            activation=params.get("activation", "relu"),
            max_iter=params.get("epochs", 100),
            batch_size=params.get("batch_size", 32),
            random_state=42,
        )

        # Autoencoder: target == input
        model.fit(X_scaled, X_scaled)

        reconstructed = model.predict(X_scaled)
        errors = np.mean((X_scaled - reconstructed) ** 2, axis=1)

        threshold = float(np.percentile(errors, 95))

        return {
            "model_type": "autoencoder",
            "model": model,
            "scaler": scaler,
            "threshold": threshold,
            "feature_cols": available_cols,
        }

    # ------------------------------------------------------------------
    # Predict
    # ------------------------------------------------------------------

    def predict(
        self,
        test_df: pd.DataFrame,
        model: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        model_type = model.get("model_type")
        scaler = model["scaler"]
        feature_cols = model["feature_cols"]

        X = test_df[feature_cols].values
        X_scaled = scaler.transform(X)

        # ---------------------------------------------------------
        # Isolation Forest
        # ---------------------------------------------------------
        if model_type == "isolation_forest":

            clf = model["model"]

            # sklearn convention:
            # higher decision_function = more normal
            raw_scores = clf.decision_function(X_scaled)
            scores = -raw_scores

            predictions = clf.predict(X_scaled)
            is_anomaly = predictions == -1

            threshold = float(np.percentile(scores, 95))

            return {
                "anomaly_score": scores.tolist(),
                "is_anomaly": is_anomaly.tolist(),
                "threshold": threshold,
                "total_anomalies": int(np.sum(is_anomaly)),
                "anomaly_percentage": float(
                    100.0 * np.sum(is_anomaly) / len(is_anomaly)
                ),
            }

        # ---------------------------------------------------------
        # Autoencoder
        # ---------------------------------------------------------
        elif model_type == "autoencoder":

            ae = model["model"]

            reconstructed = ae.predict(X_scaled)

            errors = np.mean(
                (X_scaled - reconstructed) ** 2,
                axis=1,
            )

            threshold = float(
                model.get("threshold", np.percentile(errors, 95))
            )

            is_anomaly = errors > threshold

            return {
                "anomaly_score": errors.tolist(),
                "is_anomaly": is_anomaly.tolist(),
                "threshold": threshold,
                "total_anomalies": int(np.sum(is_anomaly)),
                "anomaly_percentage": float(
                    100.0 * np.sum(is_anomaly) / len(is_anomaly)
                ),
            }

        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        test_df: pd.DataFrame,
        results: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:

        total_points = len(test_df)
        anomalies = results.get("total_anomalies", 0)

        scores = np.asarray(results.get("anomaly_score", []))

        metrics = {
            "total_points": float(total_points),
            "anomalies_detected": float(anomalies),
            "anomaly_rate": float(
                (anomalies / total_points) * 100 if total_points else 0.0
            ),
            "mean_anomaly_score": float(scores.mean()) if len(scores) else 0.0,
            "max_anomaly_score": float(scores.max()) if len(scores) else 0.0,
        }

        return metrics