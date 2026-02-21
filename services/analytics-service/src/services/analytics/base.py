"""Base pipeline for analytics operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

import pandas as pd


class BasePipeline(ABC):
    """Base class for all analytics pipelines."""
    
    @abstractmethod
    def prepare_data(
        self,
        df: pd.DataFrame,
        parameters: Optional[Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare and split data for training and testing.
        
        Returns:
            Tuple of (train_df, test_df)
        """
        pass
    
    @abstractmethod
    def train(
        self,
        train_df: pd.DataFrame,
        model_name: str,
        parameters: Optional[Dict[str, Any]],
    ) -> Any:
        """
        Train the model.
        
        Returns:
            Trained model object
        """
        pass
    
    @abstractmethod
    def predict(
        self,
        test_df: pd.DataFrame,
        model: Any,
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Run inference on test data.
        
        Returns:
            Dictionary of results
        """
        pass
    
    @abstractmethod
    def evaluate(
        self,
        test_df: pd.DataFrame,
        results: Dict[str, Any],
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Evaluate model performance.
        
        Returns:
            Dictionary of accuracy metrics
        """
        pass
