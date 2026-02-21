"""Application configuration settings."""

from typing import List, Optional
from pathlib import Path

from pydantic import Field, validator, AliasChoices
from pydantic_settings import BaseSettings


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = Field(default="data-service", description="Service name")
    app_version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8081, description="Server port")

    # MQTT Configuration
    mqtt_broker_host: str = Field(default="localhost", description="MQTT broker host")
    mqtt_broker_port: int = Field(default=1883, description="MQTT broker port")
    mqtt_username: Optional[str] = Field(default=None, description="MQTT username")
    mqtt_password: Optional[str] = Field(default=None, description="MQTT password")
    mqtt_topic: str = Field(default="devices/+/telemetry", description="MQTT subscription topic")
    mqtt_qos: int = Field(default=1, description="MQTT QoS level")
    mqtt_reconnect_interval: int = Field(default=5, description="MQTT reconnect interval in seconds")
    mqtt_max_reconnect_attempts: int = Field(default=10, description="Max MQTT reconnect attempts")
    mqtt_keepalive: int = Field(default=60, description="MQTT keepalive interval")

    # InfluxDB Configuration
    influxdb_url: str = Field(default="http://localhost:8086", description="InfluxDB URL")
    influxdb_token: str = Field(default="", description="InfluxDB token")
    influxdb_org: str = Field(default="energy-platform", description="InfluxDB organization")
    influxdb_bucket: str = Field(default="telemetry", description="InfluxDB bucket")
    influxdb_timeout: int = Field(default=5000, description="InfluxDB timeout in milliseconds")

    # Device Service Configuration
    device_service_url: str = Field(
        default="http://device-service:8080",
        description="Device service base URL",
        validation_alias=AliasChoices(
            "device_service_url",
            "device_service_base_url",
        ),
    )
    device_service_timeout: float = Field(default=5.0, description="Device service timeout in seconds")
    device_service_max_retries: int = Field(default=3, description="Max retries for device service")

    # Rule Engine Configuration
    rule_engine_url: str = Field(
        default="http://rule-engine:8082",
        description="Rule engine service URL",
        validation_alias=AliasChoices(
            "rule_engine_url",
            "rule_engine_base_url",
        ),
    )
    rule_engine_timeout: float = Field(default=5.0, description="Rule engine timeout")
    rule_engine_max_retries: int = Field(default=3, description="Max retries for rule engine")
    rule_engine_retry_delay: float = Field(default=1.0, description="Initial retry delay")

    # DLQ Configuration
    dlq_enabled: bool = Field(default=True, description="Enable dead letter queue")
    dlq_directory: str = Field(default="./dlq", description="DLQ file directory")
    dlq_max_file_size: int = Field(default=10 * 1024 * 1024, description="Max DLQ file size in bytes")
    dlq_max_files: int = Field(default=10, description="Max number of DLQ files")

    # Telemetry Validation
    telemetry_schema_version: str = Field(default="v1", description="Supported schema version")
    telemetry_max_voltage: float = Field(default=250.0, description="Max voltage value")
    telemetry_min_voltage: float = Field(default=200.0, description="Min voltage value")
    telemetry_max_current: float = Field(default=2.0, description="Max current value")
    telemetry_min_current: float = Field(default=0.0, description="Min current value")
    telemetry_max_power: float = Field(default=500.0, description="Max power value")
    telemetry_min_power: float = Field(default=0.0, description="Min power value")
    telemetry_max_temperature: float = Field(default=80.0, description="Max temperature value")
    telemetry_min_temperature: float = Field(default=20.0, description="Min temperature value")

    # WebSocket Configuration
    ws_heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval")
    ws_max_connections: int = Field(default=100, description="Max WebSocket connections")

    # API Configuration
    # ✅ MUST MATCH UI
    api_prefix: str = Field(default="/api/v1/data", description="API route prefix")

    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")

    @validator("mqtt_qos")
    def validate_mqtt_qos(cls, v: int) -> int:
        if v not in [0, 1, 2]:
            raise ValueError("MQTT QoS must be 0, 1, or 2")
        return v

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    class Config:
        env_file = str(ENV_PATH)
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()