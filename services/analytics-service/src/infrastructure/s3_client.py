"""S3 client for dataset access."""

from typing import List

import aioboto3
import structlog

from src.config.settings import get_settings

logger = structlog.get_logger()


class S3Client:
    """Async S3 client for downloading datasets."""

    def __init__(self):
        self._settings = get_settings()
        self._logger = logger.bind(service="S3Client")

        self._bucket = self._settings.s3_bucket_name

        self._session = aioboto3.Session(
            aws_access_key_id=self._settings.s3_access_key_id or None,
            aws_secret_access_key=self._settings.s3_secret_access_key or None,
            region_name=self._settings.s3_region,
        )

    def _client_kwargs(self) -> dict:
        kwargs = {
            "region_name": self._settings.s3_region,
        }

        if self._settings.s3_endpoint_url:
            kwargs["endpoint_url"] = self._settings.s3_endpoint_url

        return kwargs

    async def download_file(self, key: str) -> bytes:
        async with self._session.client("s3", **self._client_kwargs()) as client:
            self._logger.debug(
                "downloading_file",
                bucket=self._bucket,
                key=key,
            )

            response = await client.get_object(
                Bucket=self._bucket,
                Key=key,
            )

            async with response["Body"] as stream:
                data = await stream.read()

            self._logger.debug(
                "file_downloaded",
                bucket=self._bucket,
                key=key,
                size=len(data),
            )

            return data

    async def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> List[dict]:

        async with self._session.client("s3", **self._client_kwargs()) as client:
            response = await client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            objects = response.get("Contents", [])

            return [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                }
                for obj in objects
            ]

    async def upload_file(self, key: str, data: bytes) -> None:
        async with self._session.client("s3", **self._client_kwargs()) as client:
            self._logger.debug(
                "uploading_file",
                bucket=self._bucket,
                key=key,
            )

            await client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
            )

            self._logger.debug(
                "file_uploaded",
                bucket=self._bucket,
                key=key,
            )