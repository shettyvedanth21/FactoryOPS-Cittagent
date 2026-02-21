"""Analytics result loader service."""

from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

from src.repositories.analytics_repository import AnalyticsRepository
from src.utils.exceptions import AnalyticsLoadError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AnalyticsResultLoader:
    """Service for loading and processing analytics results."""
    
    def __init__(self, analytics_repository: AnalyticsRepository):
        """Initialize analytics result loader.
        
        Args:
            analytics_repository: Analytics repository instance
        """
        self.analytics_repository = analytics_repository
    
    async def load_anomaly_results(
        self,
        device_ids: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Load anomaly detection results.
        
        Args:
            device_ids: List of device identifiers
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            DataFrame with anomaly results
        """
        logger.info(
            "Loading anomaly results",
            device_count=len(device_ids),
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )
        
        all_results = []
        
        for device_id in device_ids:
            try:
                results = await self.analytics_repository.get_analytics_results(
                    device_id, "anomaly", start_time, end_time
                )
                
                for result in results:
                    parsed = self._parse_anomaly_result(result)
                    all_results.extend(parsed)
                    
            except AnalyticsLoadError as e:
                logger.error(
                    "Failed to load anomaly results",
                    error=str(e),
                    device_id=device_id
                )
                continue
        
        if not all_results:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_results)
        logger.info("Loaded anomaly results", row_count=len(df))
        return df
    
    async def load_prediction_results(
        self,
        device_ids: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Load failure prediction results.
        
        Args:
            device_ids: List of device identifiers
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            DataFrame with prediction results
        """
        logger.info(
            "Loading prediction results",
            device_count=len(device_ids),
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )
        
        all_results = []
        
        for device_id in device_ids:
            try:
                results = await self.analytics_repository.get_analytics_results(
                    device_id, "prediction", start_time, end_time
                )
                
                for result in results:
                    parsed = self._parse_prediction_result(result)
                    all_results.extend(parsed)
                    
            except AnalyticsLoadError as e:
                logger.error(
                    "Failed to load prediction results",
                    error=str(e),
                    device_id=device_id
                )
                continue
        
        if not all_results:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_results)
        logger.info("Loaded prediction results", row_count=len(df))
        return df
    
    async def load_forecast_results(
        self,
        device_ids: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Load energy forecasting results.
        
        Args:
            device_ids: List of device identifiers
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            DataFrame with forecast results
        """
        logger.info(
            "Loading forecast results",
            device_count=len(device_ids),
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )
        
        all_results = []
        
        for device_id in device_ids:
            try:
                results = await self.analytics_repository.get_analytics_results(
                    device_id, "forecast", start_time, end_time
                )
                
                for result in results:
                    parsed = self._parse_forecast_result(result)
                    all_results.extend(parsed)
                    
            except AnalyticsLoadError as e:
                logger.error(
                    "Failed to load forecast results",
                    error=str(e),
                    device_id=device_id
                )
                continue
        
        if not all_results:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_results)
        logger.info("Loaded forecast results", row_count=len(df))
        return df
    
    def _parse_anomaly_result(self, result: dict) -> List[dict]:
        """Parse anomaly result into structured format."""
        parsed = []
        
        if not result.get("results"):
            return parsed
        
        for item in result["results"]:
            parsed.append({
                "timestamp": item.get("timestamp"),
                "device_id": result.get("device_id"),
                "is_anomaly": item.get("is_anomaly", False),
                "anomaly_score": item.get("anomaly_score", 0.0),
                "affected_metrics": item.get("affected_metrics", []),
                "severity": item.get("severity", "low"),
                "model_name": result.get("model_name"),
                "created_at": result.get("created_at")
            })
        
        return parsed
    
    def _parse_prediction_result(self, result: dict) -> List[dict]:
        """Parse prediction result into structured format."""
        parsed = []
        
        if not result.get("results"):
            return parsed
        
        for item in result["results"]:
            parsed.append({
                "timestamp": item.get("timestamp"),
                "device_id": result.get("device_id"),
                "failure_probability": item.get("failure_probability", 0.0),
                "predicted_failure": item.get("predicted_failure", False),
                "time_to_failure_hours": item.get("time_to_failure_hours"),
                "confidence_score": item.get("confidence_score", 0.0),
                "model_name": result.get("model_name"),
                "created_at": result.get("created_at")
            })
        
        return parsed
    
    def _parse_forecast_result(self, result: dict) -> List[dict]:
        """Parse forecast result into structured format."""
        parsed = []
        
        if not result.get("results"):
            return parsed
        
        for item in result["results"]:
            parsed.append({
                "timestamp": item.get("timestamp"),
                "device_id": result.get("device_id"),
                "predicted_power": item.get("predicted_power", 0.0),
                "lower_bound": item.get("lower_bound", 0.0),
                "upper_bound": item.get("upper_bound", 0.0),
                "horizon_hours": item.get("horizon_hours", 0),
                "model_name": result.get("model_name"),
                "created_at": result.get("created_at")
            })
        
        return parsed
    
    def calculate_anomaly_summary(self, df: pd.DataFrame) -> dict:
        """Calculate summary statistics for anomalies.
        
        Args:
            df: Anomaly results DataFrame
            
        Returns:
            Summary statistics dictionary
        """
        if df.empty:
            return {"total_anomalies": 0, "anomaly_rate": 0.0, "by_severity": {}}
        
        total = len(df)
        anomalies = df[df["is_anomaly"] == True] if "is_anomaly" in df.columns else pd.DataFrame()
        
        summary = {
            "total_anomalies": len(anomalies),
            "anomaly_rate": len(anomalies) / total if total > 0 else 0.0,
            "by_severity": {}
        }
        
        if "severity" in df.columns:
            summary["by_severity"] = df["severity"].value_counts().to_dict()
        
        return summary
    
    def calculate_prediction_summary(self, df: pd.DataFrame) -> dict:
        """Calculate summary statistics for predictions.
        
        Args:
            df: Prediction results DataFrame
            
        Returns:
            Summary statistics dictionary
        """
        if df.empty:
            return {
                "avg_failure_probability": 0.0,
                "high_risk_count": 0,
                "avg_time_to_failure": None
            }
        
        summary = {
            "avg_failure_probability": float(df["failure_probability"].mean()) if "failure_probability" in df.columns else 0.0,
            "high_risk_count": len(df[df["failure_probability"] > 0.7]) if "failure_probability" in df.columns else 0,
            "avg_time_to_failure": float(df["time_to_failure_hours"].mean()) if "time_to_failure_hours" in df.columns and not df["time_to_failure_hours"].isna().all() else None
        }
        
        return summary