"""Forecasting pipeline implementations."""

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import structlog
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.services.analytics.base import BasePipeline

logger = structlog.get_logger()


class ForecastingPipeline(BasePipeline):
    """Pipeline for time series forecasting."""

    def __init__(self):
        self._logger = logger.bind(pipeline="Forecasting")

    # ------------------------------------------------------------------

    def prepare_data(
        self,
        df: pd.DataFrame,
        parameters: Optional[Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:

        params = parameters or {}

        df = df.copy()

        ts_col, _ = self._resolve_columns(df, params)

        df[ts_col] = pd.to_datetime(df[ts_col], utc=True)
        df = df.sort_values(ts_col)

        split_idx = int(len(df) * (1 - params.get("test_size", 0.2)))

        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()

        return train_df, test_df

    # ------------------------------------------------------------------

    def train(
        self,
        train_df: pd.DataFrame,
        model_name: str,
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        params = parameters or {}

        if model_name == "prophet":
            model = self._train_prophet(train_df, params)

        elif model_name == "arima":
            model = self._train_arima(train_df, params)

        else:
            raise ValueError(f"Unknown model: {model_name}")

        model["test_size"] = params.get("test_size", 0.2)

        return model

    # ------------------------------------------------------------------

    def _resolve_columns(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any],
    ) -> Tuple[str, str]:

        target_col = params.get("target_column", "power")
        timestamp_col = params.get("timestamp_column")

        if timestamp_col and timestamp_col in df.columns:
            ts_col = timestamp_col
        elif "timestamp" in df.columns:
            ts_col = "timestamp"
        elif "_time" in df.columns:
            ts_col = "_time"
        else:
            raise ValueError("No timestamp column found")

        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found")

        return ts_col, target_col

    # ------------------------------------------------------------------
    # Prophet
    # ------------------------------------------------------------------

    def _train_prophet(
        self,
        train_df: pd.DataFrame,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:

        ts_col, target_col = self._resolve_columns(train_df, params)

        prophet_df = pd.DataFrame(
            {
                "ds": pd.to_datetime(
                    train_df[ts_col], utc=True
                ).dt.tz_localize(None),
                "y": train_df[target_col].astype(float).values,
            }
        )

        model = Prophet(
            daily_seasonality=params.get("daily_seasonality", True),
            weekly_seasonality=params.get("weekly_seasonality", True),
            yearly_seasonality=params.get("yearly_seasonality", False),
        )

        model.fit(prophet_df)

        return {
            "model_type": "prophet",
            "model": model,
            "timestamp_col": ts_col,
            "target_col": target_col,
            "freq": params.get("freq", "H"),
        }

    # ------------------------------------------------------------------
    # ARIMA
    # ------------------------------------------------------------------

    def _train_arima(
        self,
        train_df: pd.DataFrame,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:

        try:
            from statsmodels.tsa.arima.model import ARIMA
        except Exception as e:
            raise RuntimeError(
                "ARIMA requires statsmodels. Install with: poetry add statsmodels"
            ) from e

        ts_col, target_col = self._resolve_columns(train_df, params)

        y = train_df[target_col].astype(float).values

        order = tuple(params.get("order", [1, 1, 1]))
        seasonal_order = tuple(params.get("seasonal_order", [1, 1, 1, 24]))

        model = ARIMA(
            y,
            order=order,
            seasonal_order=seasonal_order,
        )

        fitted_model = model.fit()

        # store last timestamp for future index generation
        last_ts = pd.to_datetime(
            train_df[ts_col].iloc[-1], utc=True
        )

        return {
            "model_type": "arima",
            "model": fitted_model,
            "target_col": target_col,
            "last_timestamp": last_ts,
            "freq": params.get("freq", "H"),
        }

    # ------------------------------------------------------------------

    def predict(
        self,
        df: pd.DataFrame,
        model: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        params = parameters or {}

        horizon = params.get(
            "forecast_periods",
            max(1, int(len(df) * model.get("test_size", 0.2))),
        )

        model_type = model.get("model_type")

        if model_type == "prophet":
            return self._predict_prophet(model, horizon)

        if model_type == "arima":
            return self._predict_arima(model, horizon)

        raise ValueError("Unknown forecasting model type")

    # ------------------------------------------------------------------

    def _predict_prophet(
        self,
        model: Dict[str, Any],
        periods: int,
    ) -> Dict[str, Any]:

        prophet_model = model["model"]
        freq = model["freq"]

        future = prophet_model.make_future_dataframe(
            periods=periods,
            freq=freq,
        )

        forecast = prophet_model.predict(future)

        tail = forecast.tail(periods)

        return {
            "forecast": tail["yhat"].astype(float).tolist(),
            "forecast_lower": tail["yhat_lower"].astype(float).tolist(),
            "forecast_upper": tail["yhat_upper"].astype(float).tolist(),
            "forecast_timestamps": tail["ds"]
            .dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            .tolist(),
            "mean_forecast": float(np.mean(tail["yhat"])),
            "max_forecast": float(np.max(tail["yhat"])),
            "min_forecast": float(np.min(tail["yhat"])),
        }

    # ------------------------------------------------------------------
    # ARIMA prediction – WITH timestamps (PERMANENT FIX)
    # ------------------------------------------------------------------

    def _predict_arima(
        self,
        model: Dict[str, Any],
        periods: int,
    ) -> Dict[str, Any]:

        arima_model = model["model"]

        forecast_result = arima_model.get_forecast(steps=periods)

        mean = np.asarray(forecast_result.predicted_mean, dtype=float)

        conf = forecast_result.conf_int()

        if isinstance(conf, pd.DataFrame):
            lower = conf.iloc[:, 0].to_numpy(dtype=float)
            upper = conf.iloc[:, 1].to_numpy(dtype=float)
        else:
            lower = conf[:, 0].astype(float)
            upper = conf[:, 1].astype(float)

        # -----------------------------
        # generate timestamps
        # -----------------------------
        last_ts = model.get("last_timestamp")
        freq = model.get("freq", "H")

        if last_ts is None:
            raise ValueError(
                "ARIMA model missing last_timestamp for forecast index generation"
            )

        start = last_ts + pd.tseries.frequencies.to_offset(freq)

        ts_index = pd.date_range(
            start=start,
            periods=periods,
            freq=freq,
            tz="UTC",
        )

        return {
            "forecast": mean.tolist(),
            "forecast_lower": lower.tolist(),
            "forecast_upper": upper.tolist(),
            "forecast_timestamps": ts_index.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ).tolist(),
            "mean_forecast": float(np.mean(mean)),
            "max_forecast": float(np.max(mean)),
            "min_forecast": float(np.min(mean)),
        }

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        test_df: pd.DataFrame,
        results: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:

        params = parameters or {}

        _, target_col = self._resolve_columns(test_df, params)

        y_true = np.asarray(
            test_df[target_col].astype(float).values
        )
        y_pred = np.asarray(
            results.get("forecast", []),
            dtype=float,
        )

        n = min(len(y_true), len(y_pred))

        if n == 0:
            return {
                "mae": 0.0,
                "rmse": 0.0,
                "mape": 0.0,
                "mean_actual": 0.0,
                "mean_predicted": 0.0,
            }

        y_true = y_true[:n]
        y_pred = y_pred[:n]

        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))

        denom = np.where(y_true == 0, np.nan, y_true)

        with np.errstate(divide="ignore", invalid="ignore"):
            mape = np.nanmean(np.abs((y_true - y_pred) / denom)) * 100

        if not np.isfinite(mape):
            mape = 0.0

        return {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
            "mean_actual": float(np.mean(y_true)),
            "mean_predicted": float(np.mean(y_pred)),
        }