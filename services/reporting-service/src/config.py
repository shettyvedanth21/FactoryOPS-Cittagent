"""Configuration settings for the Reporting Service."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = Field(default="reporting-service", alias="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", alias="SERVICE_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8085, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket_name: str = Field(default="energy-platform-datasets", alias="S3_BUCKET_NAME")
    s3_prefix: str = Field(default="datasets", alias="S3_PREFIX")

    mysql_host: str = Field(default="mysql", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="energy", alias="MYSQL_USER")
    mysql_password: str = Field(default="energy", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="energy_reporting_db", alias="MYSQL_DATABASE")
    mysql_pool_size: int = Field(default=10, alias="MYSQL_POOL_SIZE")

    max_report_size_mb: int = Field(default=100, alias="MAX_REPORT_SIZE_MB")
    default_page_size: int = Field(default=1000, alias="DEFAULT_PAGE_SIZE")
    report_timeout_seconds: int = Field(default=300, alias="REPORT_TIMEOUT_SECONDS")
    cleanup_interval_seconds: int = Field(default=3600, alias="CLEANUP_INTERVAL_SECONDS")

    temp_dir: str = Field(default="/tmp/reports", alias="TEMP_DIR")

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def mysql_async_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


settings = Settings()
