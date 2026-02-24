from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/energy_reporting_db"
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = "my-token"
    INFLUXDB_ORG: str = "my-org"
    INFLUXDB_BUCKET: str = "telemetry"
    INFLUXDB_MEASUREMENT: str = "device_telemetry"
    INFLUX_POWER_FIELD: str = "power"
    INFLUX_VOLTAGE_FIELD: str = "voltage"
    INFLUX_CURRENT_FIELD: str = "current"
    INFLUX_POWER_FACTOR_FIELD: str = "power_factor"
    INFLUX_REACTIVE_POWER_FIELD: str = "reactive_power"
    INFLUX_FREQUENCY_FIELD: str = "frequency"
    INFLUX_THD_FIELD: str = "thd"
    INFLUX_AGGREGATION_WINDOW: str = "5m"
    DEVICE_SERVICE_URL: str = "http://device-service:8000"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_EXTERNAL_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minio"
    MINIO_SECRET_KEY: str = "minio123"
    MINIO_BUCKET: str = "energy-platform-datasets"
    MINIO_SECURE: bool = False
    DEMAND_WINDOW_MINUTES: int = 15
    SERVICE_NAME: str = "reporting-service"


settings = Settings()
