"""Configuration management for Data Export Service."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    service_name: str = "data-export-service"
    service_version: str = "1.0.0"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = ""
    influxdb_org: str = "energy-platform"
    influxdb_bucket: str = "telemetry"
    influxdb_timeout_seconds: int = 30

    data_service_url: str = ""
    data_service_timeout_seconds: int = 10

    export_interval_seconds: int = 60
    export_batch_size: int = 1000
    export_format: str = "parquet"

    s3_bucket: str = "energy-platform-datasets"
    s3_prefix: str = "telemetry"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Checkpoint Storage (MySQL)
    checkpoint_db_host: str = "localhost"
    checkpoint_db_port: int = 3306
    checkpoint_db_name: str = "energy_export_db"
    checkpoint_db_user: str = ""
    checkpoint_db_password: str = ""
    checkpoint_table: str = "export_checkpoints"

    lookback_hours: int = 1
    max_export_window_hours: int = 24

    device_ids: str = "D1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_device_ids(self) -> list[str]:
        """Parse device_ids string into list."""
        return [d.strip() for d in self.device_ids.split(",") if d.strip()]

    def get_checkpoint_db_url(self) -> str:
        """Build MySQL connection URL."""
        return (
            f"mysql+pymysql://{self.checkpoint_db_user}:{self.checkpoint_db_password}"
            f"@{self.checkpoint_db_host}:{self.checkpoint_db_port}"
            f"/{self.checkpoint_db_name}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
