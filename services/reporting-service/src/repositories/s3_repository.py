"""S3 repository for accessing exported datasets."""

import io
from datetime import datetime
from typing import List, Optional
import aioboto3
import pandas as pd
from botocore.exceptions import ClientError

from src.config import settings
from src.utils.exceptions import S3Error, DatasetLoadError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class S3Repository:
    """Repository for accessing S3 exported datasets."""
    
    def __init__(self):
        """Initialize S3 repository with AWS credentials."""
        self.bucket_name = settings.s3_bucket_name
        self.prefix = settings.s3_prefix
        self.session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
    
    async def list_dataset_keys(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[str]:
        """List S3 keys for datasets matching criteria.
        
        Args:
            device_id: Device identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of S3 object keys
            
        Raises:
            S3Error: If S3 operation fails
        """
        prefix = f"{self.prefix}/{device_id}/"
        keys = []
        
        try:
            async with self.session.client("s3") as s3:
                paginator = s3.get_paginator("list_objects_v2")
                
                async for page in paginator.paginate(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                ):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            key = obj["Key"]
                            # Parse date from key format: datasets/{device_id}/YYYYMMDD_YYYYMMDD.parquet
                            try:
                                filename = key.split("/")[-1]
                                date_part = filename.split("_")[0]
                                file_date = datetime.strptime(date_part, "%Y%m%d")
                                
                                if start_time.date() <= file_date.date() <= end_time.date():
                                    keys.append(key)
                            except (IndexError, ValueError):
                                logger.warning("Skipping file with unexpected format", key=key)
                                continue
            
            logger.info(
                "Listed dataset keys",
                device_id=device_id,
                key_count=len(keys),
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat()
            )
            
            return keys
            
        except ClientError as e:
            logger.error("Failed to list S3 objects", error=str(e), device_id=device_id)
            raise S3Error(f"Failed to list datasets: {str(e)}", operation="list_objects")
    
    async def load_dataset(self, s3_key: str) -> pd.DataFrame:
        """Load a dataset from S3 into a pandas DataFrame.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            DataFrame containing the dataset
            
        Raises:
            DatasetLoadError: If dataset cannot be loaded
        """
        try:
            async with self.session.client("s3") as s3:
                response = await s3.get_object(Bucket=self.bucket_name, Key=s3_key)
                
                async with response["Body"] as stream:
                    data = await stream.read()
                    
                    # Load based on file extension
                    if s3_key.endswith(".parquet"):
                        df = pd.read_parquet(io.BytesIO(data))
                    elif s3_key.endswith(".csv"):
                        df = pd.read_csv(io.BytesIO(data))
                    elif s3_key.endswith(".json"):
                        df = pd.read_json(io.BytesIO(data))
                    else:
                        raise DatasetLoadError(
                            f"Unsupported file format: {s3_key}",
                            s3_key=s3_key
                        )
                    
                    logger.info(
                        "Loaded dataset from S3",
                        s3_key=s3_key,
                        rows=len(df),
                        columns=list(df.columns)
                    )
                    
                    return df
                    
        except ClientError as e:
            logger.error("Failed to load dataset from S3", error=str(e), s3_key=s3_key)
            raise DatasetLoadError(
                f"Failed to load dataset: {str(e)}",
                s3_key=s3_key
            )
    
    async def upload_report(
        self,
        job_id: str,
        data: bytes,
        format_type: str
    ) -> str:
        """Upload generated report to S3.
        
        Args:
            job_id: Report job identifier
            data: Report binary data
            format_type: Report format (pdf, excel, json)
            
        Returns:
            S3 key of uploaded report
            
        Raises:
            S3Error: If upload fails
        """
        s3_key = f"reports/{job_id}.{format_type}"
        
        try:
            async with self.session.client("s3") as s3:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=data,
                    ContentType=self._get_content_type(format_type),
                    Metadata={
                        "job_id": job_id,
                        "format": format_type,
                        "generated_at": datetime.utcnow().isoformat()
                    }
                )
            
            logger.info("Uploaded report to S3", job_id=job_id, s3_key=s3_key)
            return s3_key
            
        except ClientError as e:
            logger.error("Failed to upload report", error=str(e), job_id=job_id)
            raise S3Error(f"Failed to upload report: {str(e)}", operation="put_object")
    
    async def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> str:
        """Generate presigned URL for downloading a report.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string
            
        Raises:
            S3Error: If URL generation fails
        """
        try:
            async with self.session.client("s3") as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": s3_key},
                    ExpiresIn=expiration
                )
            
            return url
            
        except ClientError as e:
            logger.error("Failed to generate presigned URL", error=str(e), s3_key=s3_key)
            raise S3Error(
                f"Failed to generate download URL: {str(e)}",
                operation="generate_presigned_url"
            )
    
    def _get_content_type(self, format_type: str) -> str:
        """Get MIME content type for report format."""
        content_types = {
            "pdf": "application/pdf",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json"
        }
        return content_types.get(format_type, "application/octet-stream")