"""Feature engineering for ML pipelines."""

from typing import List

import numpy as np
import pandas as pd


class FeatureEngineer:
    """Engineer features for ML models."""
    
    def engineer_features(
        self,
        df: pd.DataFrame,
        base_features: List[str],
    ) -> pd.DataFrame:
        """
        Add engineered features to the dataset.
        
        Args:
            df: Input DataFrame
            base_features: List of base feature columns to engineer from
            
        Returns:
            DataFrame with additional engineered features
        """
        df = df.copy()
        
        # Ensure timestamp is datetime
        if "_time" in df.columns:
            df["_time"] = pd.to_datetime(df["_time"])
        elif "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Time-based features
        if "_time" in df.columns:
            df["hour"] = df["_time"].dt.hour
            df["day_of_week"] = df["_time"].dt.dayofweek
            df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
            df["month"] = df["_time"].dt.month
        
        # Rolling statistics (5-minute window assuming 5s intervals)
        window = 60  # 60 points = 5 minutes at 5s intervals
        
        for feature in base_features:
            if feature in df.columns:
                df[f"{feature}_rolling_mean"] = df[feature].rolling(window=window, min_periods=1).mean()
                df[f"{feature}_rolling_std"] = df[feature].rolling(window=window, min_periods=1).std()
                df[f"{feature}_rolling_max"] = df[feature].rolling(window=window, min_periods=1).max()
                df[f"{feature}_rolling_min"] = df[feature].rolling(window=window, min_periods=1).min()
        
        # Rate of change (derivative)
        for feature in base_features:
            if feature in df.columns:
                df[f"{feature}_rate"] = df[feature].diff().fillna(0)
        
        # Power factor calculation
        if all(col in df.columns for col in ["voltage", "current", "power"]):
            df["power_factor"] = df["power"] / (df["voltage"] * df["current"])
            df["power_factor"] = df["power_factor"].clip(0, 1).fillna(0)
        
        # Energy efficiency proxy (power per unit temperature)
        if all(col in df.columns for col in ["power", "temperature"]):
            df["power_per_temp"] = df["power"] / df["temperature"].replace(0, np.nan)
            df["power_per_temp"] = df["power_per_temp"].fillna(0)
        
        # Lag features
        for feature in base_features:
            if feature in df.columns:
                df[f"{feature}_lag_1"] = df[feature].shift(1).fillna(df[feature])
                df[f"{feature}_lag_5"] = df[feature].shift(5).fillna(df[feature])
        
        # Fill NaN values
        df = df.fillna(method="ffill").fillna(method="bfill").fillna(0)
        
        return df
