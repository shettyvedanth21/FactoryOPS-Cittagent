"""S3 writer for exporting datasets to Amazon S3.

Handles upload of telemetry datasets in Parquet or CSV format
with proper partitioning and metadata.
"""

import io
from datetime import datetime, timezone
from typing import Optional

import aioboto3
import pandas as pd
from botocore.exceptions import ClientError

from config import Settings
from logging_config import get_logger
from models import DatasetMetadata, ExportBatch, ExportFormat, TelemetryData

logger = get_logger(__name__)


class S3Writer:
    """Async S3 writer for telemetry datasets."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._session: Optional[aioboto3.Session] = None

    def initialize(self) -> None:
        """Initialize S3 session."""
        self._session = aioboto3.Session(
            aws_access_key_id=self.settings.aws_access_key_id or None,
            aws_secret_access_key=self.settings.aws_secret_access_key or None,
            region_name=self.settings.s3_region,
        )

        logger.info(
            "S3 session initialized",
            extra={
                "bucket": self.settings.s3_bucket,
                "region": self.settings.s3_region,
            },
        )

    async def close(self) -> None:
        logger.info("S3 writer closed")

    # ------------------------------------------------------------------
    # Analytics compatible layout
    #
    # datasets/{device_id}/{YYYYMMDD}_{YYYYMMDD}.parquet
    # ------------------------------------------------------------------
    def _build_s3_key(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        format: ExportFormat = ExportFormat.PARQUET,
    ) -> str:
        extension = "parquet" if format == ExportFormat.PARQUET else "csv"

        start_str = start_time.strftime("%Y%m%d")
        end_str = end_time.strftime("%Y%m%d")

        return f"datasets/{device_id}/{start_str}_{end_str}.{extension}"

    def _convert_to_dataframe(self, records: list[TelemetryData]) -> pd.DataFrame:
        data = []
        for record in records:
            data.append(
                {
                    "timestamp": record.timestamp,
                    "device_id": record.device_id,
                    "device_type": record.device_type,
                    "location": record.location,
                    "voltage": record.voltage,
                    "current": record.current,
                    "power": record.power,
                    "temperature": record.temperature,
                }
            )

        df = pd.DataFrame(data)

        if df.empty:
            return df

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

        if (
            "voltage" in df.columns
            and "current" in df.columns
            and "power" in df.columns
        ):
            apparent_power = df["voltage"] * df["current"]
            df["power_factor"] = (
                (df["power"] / apparent_power)
                .replace([float("inf"), -float("inf")], 0)
                .fillna(0)
                .clip(0, 1)
            )

        return df

    async def write_batch(
        self,
        batch: ExportBatch,
        format: ExportFormat = ExportFormat.PARQUET,
    ) -> DatasetMetadata:

        if not self._session:
            raise RuntimeError("S3Writer is not initialized")

        if not batch.records:
            raise ValueError("Cannot write empty batch")

        # ------------------------------------------------------------------
        # Freeze time window locally (PERMANENT FIX)
        # ------------------------------------------------------------------
        start_time = batch.start_time
        end_time = batch.end_time

        if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
            raise TypeError(
                "ExportBatch.start_time and end_time must be datetime objects"
            )

        df = self._convert_to_dataframe(batch.records)

        s3_key = self._build_s3_key(
            batch.device_id,
            start_time,
            end_time,
            format,
        )

        buffer = io.BytesIO()

        if format == ExportFormat.PARQUET:
            df.to_parquet(
                buffer,
                engine="pyarrow",
                compression="snappy",
                index=False,
            )
        else:
            df.to_csv(buffer, index=False)

        buffer.seek(0)
        file_size = buffer.getbuffer().nbytes

        async with self._session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url or None,
        ) as s3_client:
            try:
                await s3_client.put_object(
                    Bucket=self.settings.s3_bucket,
                    Key=s3_key,
                    Body=buffer.getvalue(),
                    ContentType=(
                        "application/octet-stream"
                        if format == ExportFormat.PARQUET
                        else "text/csv"
                    ),
                    Metadata={
                        "device_id": batch.device_id,
                        "record_count": str(batch.record_count),
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "export_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

                logger.info(
                    "Uploaded telemetry batch to S3",
                    extra={
                        "device_id": batch.device_id,
                        "s3_key": s3_key,
                        "file_size_bytes": file_size,
                        "format": format.value,
                    },
                )

                return DatasetMetadata(
                    device_id=batch.device_id,
                    date_partition=start_time.strftime("%Y-%m-%d"),
                    format=format,
                    record_count=batch.record_count,
                    start_time=start_time,
                    end_time=end_time,
                    columns=list(df.columns),
                    file_size_bytes=file_size,
                )

            except ClientError as e:
                logger.error(
                    "Failed to upload to S3",
                    extra={
                        "device_id": batch.device_id,
                        "s3_key": s3_key,
                        "error": str(e),
                    },
                )
                raise

    async def health_check(self) -> bool:
        if not self._session:
            raise RuntimeError("S3Writer is not initialized")

        async with self._session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url or None,
        ) as s3_client:
            try:
                await s3_client.head_bucket(Bucket=self.settings.s3_bucket)
                return True
            except ClientError as e:
                logger.error(f"S3 health check failed: {e}")
                raise