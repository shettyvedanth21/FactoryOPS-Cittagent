"""Failure prediction pipeline implementations."""

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import structlog
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.services.analytics.base import BasePipeline
from src.services.analytics.feature_engineering import FeatureEngineer

logger = structlog.get_logger()


class FailurePredictionPipeline(BasePipeline):
    """Pipeline for failure prediction analytics."""

    def __init__(self):
        self._logger = logger.bind(pipeline="FailurePrediction")
        self._feature_engineer = FeatureEngineer()

    def prepare_data(
        self,
        df: pd.DataFrame,
        parameters: Optional[Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:

        params = parameters or {}

        base_features = params.get(
            "features",
            ["voltage", "current", "power", "temperature"],
        )

        df = self._feature_engineer.engineer_features(df, base_features)
        df = self._create_failure_labels(df, params)

        split_idx = int(len(df) * (1 - params.get("test_size", 0.2)))

        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()

        return train_df, test_df

    def _create_failure_labels(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any],
    ) -> pd.DataFrame:

        df = df.copy()

        temp_threshold = params.get("failure_temp_threshold", 75.0)
        voltage_threshold = params.get("failure_voltage_threshold", 245.0)

        df["failure"] = (
            (df["temperature"] > temp_threshold)
            | (df["voltage"] > voltage_threshold)
        ).astype(int)

        return df

    # ------------------------------------------------------------
    # PERMANENT FIX:
    # support single-class training
    # ------------------------------------------------------------
    def train(
        self,
        train_df: pd.DataFrame,
        model_name: str,
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        params = parameters or {}

        exclude_cols = {
            "failure",
            "timestamp",
            "_time",
            "device_id",
            "device_type",
            "location",
        }

        feature_cols = [
            c
            for c in train_df.columns
            if c not in exclude_cols
            and pd.api.types.is_numeric_dtype(train_df[c])
        ]

        if "failure" not in train_df.columns:
            raise ValueError("Failure label column missing")

        X = train_df[feature_cols].values
        y = train_df["failure"].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        unique_classes = np.unique(y)

        # ----------------------------
        # single class → no sklearn model
        # ----------------------------
        if len(unique_classes) == 1:
            only_class = int(unique_classes[0])

            self._logger.warning(
                "single_class_training_detected",
                class_value=only_class,
            )

            return {
                "model": None,
                "scaler": scaler,
                "feature_cols": feature_cols,
                "base_features": params.get(
                    "features",
                    ["voltage", "current", "power", "temperature"],
                ),
                "single_class": only_class,
            }

        # ----------------------------
        # normal training
        # ----------------------------
        if model_name == "random_forest":
            model = RandomForestClassifier(
                n_estimators=params.get("n_estimators", 100),
                max_depth=params.get("max_depth", 10),
                random_state=params.get("random_state", 42),
            )

        elif model_name == "gradient_boosting":
            model = GradientBoostingClassifier(
                n_estimators=params.get("n_estimators", 100),
                learning_rate=params.get("learning_rate", 0.1),
                max_depth=params.get("max_depth", 6),
                random_state=params.get("random_state", 42),
            )

        else:
            raise ValueError(f"Unknown model: {model_name}")

        model.fit(X_scaled, y)

        return {
            "model": model,
            "scaler": scaler,
            "feature_cols": feature_cols,
            "base_features": params.get(
                "features",
                ["voltage", "current", "power", "temperature"],
            ),
            "single_class": None,
        }

    def predict(
        self,
        df: pd.DataFrame,
        model: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        base_features = model["base_features"]

        df = self._feature_engineer.engineer_features(df, base_features)

        scaler = model["scaler"]
        feature_cols = model["feature_cols"]
        single_class = model.get("single_class")

        for c in feature_cols:
            if c not in df.columns:
                df[c] = 0.0

        X = df[feature_cols].values
        X_scaled = scaler.transform(X)

        # ----------------------------
        # PERMANENT FIX:
        # single-class inference
        # ----------------------------
        if single_class is not None:
            if single_class == 1:
                failure_prob = np.ones(len(df))
            else:
                failure_prob = np.zeros(len(df))
        else:
            clf = model["model"]
            failure_prob = clf.predict_proba(X_scaled)[:, 1]

        predicted_failure = failure_prob > 0.5
        time_to_failure = self._estimate_time_to_failure(failure_prob)

        if "timestamp" in df.columns:
            ts = pd.to_datetime(df["timestamp"], utc=True)
        elif "_time" in df.columns:
            ts = pd.to_datetime(df["_time"], utc=True)
        else:
            ts = None

        points = None
        if ts is not None:
            points = [
                {
                    "timestamp": t.isoformat(),
                    "failure_probability": float(p),
                    "predicted_failure": bool(f),
                    "time_to_failure_hours": float(ttf),
                }
                for t, p, f, ttf in zip(
                    ts,
                    failure_prob,
                    predicted_failure,
                    time_to_failure,
                )
            ]

        return {
            "failure_probability": failure_prob.tolist(),
            "predicted_failure": predicted_failure.tolist(),
            "time_to_failure_hours": time_to_failure.tolist(),
            "high_risk_count": int(np.sum(failure_prob > 0.7)),
            "medium_risk_count": int(
                np.sum((failure_prob > 0.4) & (failure_prob <= 0.7))
            ),
            "low_risk_count": int(np.sum(failure_prob <= 0.4)),
            "points": points,
        }

    def _estimate_time_to_failure(self, failure_prob: np.ndarray) -> np.ndarray:

        ttf = np.zeros(len(failure_prob), dtype=float)

        for i, p in enumerate(failure_prob):
            if p > 0.8:
                ttf[i] = 1
            elif p > 0.6:
                ttf[i] = 6
            elif p > 0.4:
                ttf[i] = 24
            else:
                ttf[i] = -1

        return ttf

    # ------------------------------------------------------------
    # PERMANENT FIX:
    # evaluation aligned with full-DF inference
    # ------------------------------------------------------------
    def evaluate(
        self,
        test_df: pd.DataFrame,
        results: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:

        if "failure" not in test_df.columns:
            return {}

        n = len(test_df)

        y_true = test_df["failure"].values
        y_pred = np.asarray(results["predicted_failure"][-n:])
        y_prob = np.asarray(results["failure_probability"][-n:])

        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true,
            y_pred,
            average="binary",
            zero_division=0,
        )

        try:
            auc = roc_auc_score(y_true, y_prob)
        except Exception:
            auc = 0.5

        return {
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "auc_roc": float(auc),
            "accuracy": float(np.mean(y_true == y_pred)),
        }