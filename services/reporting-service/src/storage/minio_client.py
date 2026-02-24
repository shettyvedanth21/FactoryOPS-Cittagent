import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.config import settings


class StorageError(Exception):
    pass


class MinIOClient:
    def __init__(self):
        self.internal_endpoint = f"http://{settings.MINIO_ENDPOINT}"
        self.external_endpoint = settings.MINIO_EXTERNAL_URL
        self.client = boto3.client(
            's3',
            endpoint_url=self.internal_endpoint,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            use_ssl=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET
        self._external_client = None
    
    def _get_external_client(self):
        if self._external_client is None:
            self._external_client = boto3.client(
                's3',
                endpoint_url=self.external_endpoint,
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                config=Config(signature_version='s3v4'),
                use_ssl=settings.MINIO_SECURE
            )
        return self._external_client
    
    def ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except ClientError as e:
                raise StorageError(f"Failed to create bucket: {e}")
    
    def upload_pdf(self, pdf_bytes: bytes, s3_key: str) -> str:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType="application/pdf"
            )
            return s3_key
        except ClientError as e:
            raise StorageError(f"Failed to upload PDF: {e}")
    
    def download_pdf(self, s3_key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            raise StorageError(f"Failed to download PDF: {e}")
    
    def get_presigned_url(self, s3_key: str, expires_seconds: int = 900) -> str:
        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
        except ClientError:
            raise StorageError(f"Key not found: {s3_key}")
        
        try:
            external_client = self._get_external_client()
            presigned_url = external_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=expires_seconds
            )
            return presigned_url
        except ClientError as e:
            raise StorageError(f"Failed to generate presigned URL: {e}")
    
    def delete_file(self, s3_key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
        except ClientError as e:
            raise StorageError(f"Failed to delete file: {e}")


minio_client = MinIOClient()
