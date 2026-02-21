"""S3 dataset loader service."""

from datetime import datetime
from typing import Dict, List
import pandas as pd

from src.repositories.s3_repository import S3Repository
from src.utils.exceptions import DatasetLoadError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class S3DatasetLoader:
    """Service for loading telemetry datasets from S3."""
    
    def __init__(self, s3_repository: S3Repository):
        """Initialize S3 dataset loader.
        
        Args:
            s3_repository: S3 repository instance
        """
        self.s3_repository = s3_repository
    
    async def load_device_datasets(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Load all datasets for a device within time range.
        
        Args:
            device_id: Device identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Combined DataFrame with all telemetry data
            
        Raises:
            DatasetLoadError: If loading fails
        """
        logger.info(
            "Loading device datasets",
            device_id=device_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )
        
        # List available dataset keys
        keys = await self.s3_repository.list_dataset_keys(
            device_id, start_time, end_time
        )
        
        if not keys:
            logger.warning("No datasets found for device", device_id=device_id)
            return pd.DataFrame()
        
        # Load and combine all datasets
        dataframes = []
        for key in keys:
            try:
                df = await self.s3_repository.load_dataset(key)
                dataframes.append(df)
            except DatasetLoadError as e:
                logger.error(
                    "Failed to load dataset",
                    error=str(e),
                    s3_key=key,
                    device_id=device_id
                )
                continue
        
        if not dataframes:
            raise DatasetLoadError(
                "No datasets could be loaded",
                device_id=device_id
            )
        
        # Combine all dataframes
        combined_df = pd.concat(dataframes, ignore_index=True)
        
        # Filter by time range
        if "_time" in combined_df.columns:
            combined_df["_time"] = pd.to_datetime(combined_df["_time"])
            combined_df = combined_df[
                (combined_df["_time"] >= start_time) &
                (combined_df["_time"] <= end_time)
            ]
        
        logger.info(
            "Loaded device datasets",
            device_id=device_id,
            total_rows=len(combined_df),
            files_loaded=len(dataframes)
        )
        
        return combined_df
    
    async def load_multiple_devices(
        self,
        device_ids: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, pd.DataFrame]:
        """Load datasets for multiple devices.
        
        Args:
            device_ids: List of device identifiers
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dictionary mapping device_id to DataFrame
        """
        results = {}
        
        for device_id in device_ids:
            try:
                df = await self.load_device_datasets(device_id, start_time, end_time)
                results[device_id] = df
            except DatasetLoadError as e:
                logger.error(
                    "Failed to load device dataset",
                    error=str(e),
                    device_id=device_id
                )
                results[device_id] = pd.DataFrame()
        
        return results
    
    def calculate_summary_stats(self, df: pd.DataFrame) -> dict:
        """Calculate summary statistics for telemetry data.
        
        Args:
            df: Telemetry DataFrame
            
        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {
                "total_records": 0,
                "time_range": {"start": None, "end": None},
                "metrics": {}
            }
        
        stats = {
            "total_records": len(df),
            "time_range": {
                "start": df["_time"].min().isoformat() if "_time" in df.columns else None,
                "end": df["_time"].max().isoformat() if "_time" in df.columns else None
            },
            "metrics": {}
        }
        
        # Calculate stats for numeric columns
        numeric_columns = ["voltage", "current", "power", "temperature"]
        for col in numeric_columns:
            if col in df.columns:
                stats["metrics"][col] = {
                    "mean": float(df[col].mean()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "std": float(df[col].std())
                }
        
        return stats