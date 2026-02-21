"""Dataset access service - reads from S3 only."""

import io
from datetime import datetime
from typing import Optional

import pandas as pd
import structlog

from src.infrastructure.s3_client import S3Client
from src.utils.exceptions import DatasetNotFoundError, DatasetReadError

logger = structlog.get_logger()


class DatasetService:
    """Service for accessing datasets from S3."""

    def __init__(self, s3_client: S3Client):
        self._s3 = s3_client
        self._logger = logger.bind(service="DatasetService")

    async def load_dataset(
        self,
        device_id: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        s3_key: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Load dataset from S3.

        If s3_key is provided, it is used directly.
        Otherwise, the key is constructed from device_id and time range.
        """

        # ---------------------------------------------------------
        # Permanent fix:
        # s3_key takes priority and does NOT require start/end time
        # ---------------------------------------------------------
        if s3_key is None:
            if start_time is None or end_time is None:
                raise DatasetReadError(
                    "start_time and end_time must be provided when s3_key is not specified"
                )

            s3_key = self._construct_s3_key(
                device_id,
                start_time,
                end_time,
            )

            self._logger.info(
                "loading_dataset",
                device_id=device_id,
                s3_key=s3_key,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
            )
        else:
            self._logger.info(
                "loading_dataset",
                device_id=device_id,
                s3_key=s3_key,
                mode="explicit_dataset_key",
            )

        try:
            data = await self._s3.download_file(s3_key)

            df = pd.read_parquet(io.BytesIO(data))

            self._logger.info(
                "dataset_loaded",
                device_id=device_id,
                rows=len(df),
                columns=list(df.columns),
            )

            return df

        except Exception as e:
            self._logger.error(
                "dataset_load_failed",
                device_id=device_id,
                s3_key=s3_key,
                error=str(e),
            )

            if "Not Found" in str(e) or "NoSuchKey" in str(e):
                raise DatasetNotFoundError(f"Dataset not found: {s3_key}")

            raise DatasetReadError(f"Failed to read dataset: {e}") from e

    def _construct_s3_key(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> str:
        """Construct S3 key from parameters."""
        return (
            f"datasets/{device_id}/"
            f"{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.parquet"
        )

    async def list_available_datasets(
        self,
        device_id: str,
        prefix: Optional[str] = None,
    ) -> list:
        """List available datasets for a device."""
        if prefix is None:
            prefix = f"datasets/{device_id}/"

        return await self._s3.list_objects(prefix)