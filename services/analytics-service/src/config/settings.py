"""Application configuration."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="analytics-service")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    mysql_host: str = Field(default="mysql")
    mysql_port: int = Field(default=3306)
    mysql_database: str = Field(default="energy_analytics_db")
    mysql_user: str = Field(default="energy")
    mysql_password: str = Field(default="energy")
    mysql_pool_size: int = Field(default=10)

    s3_bucket_name: str = Field(default="energy-platform-datasets")
    s3_region: str = Field(default="us-east-1")
    s3_endpoint_url: str | None = Field(default=None)
    s3_access_key_id: str | None = Field(default=None)
    s3_secret_access_key: str | None = Field(default=None)

    default_train_test_split: float = Field(default=0.8)
    max_dataset_size_mb: int = Field(default=500)
    supported_models: List[str] = Field(
        default=[
            "isolation_forest",
            "autoencoder",
            "random_forest",
            "gradient_boosting",
            "prophet",
            "arima",
        ]
    )

    max_concurrent_jobs: int = Field(default=3)
    job_timeout_seconds: int = Field(default=3600)

    @property
    def mysql_dsn(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def mysql_sync_dsn(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
