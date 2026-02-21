"""Application configuration management for Rule Engine Service."""

from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    SERVICE_NAME: str = "rule-engine-service"
    APP_NAME: str = "rule-engine-service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "mysql+aiomysql://energy:energy@localhost:3306/energy_rule_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    
    # API
    API_PREFIX: str = "/api/v1"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Rule Engine
    RULE_EVALUATION_TIMEOUT: int = 5  # seconds
    NOTIFICATION_COOLDOWN_MINUTES: int = 15
    MAX_RULES_PER_DEVICE: int = 100
    
    # Notification Adapters (for future configuration)
    EMAIL_ENABLED: bool = False
    WHATSAPP_ENABLED: bool = False
    TELEGRAM_ENABLED: bool = False
    
    # Multi-tenancy (Phase-2 ready)
    TENANT_ID_HEADER: str = "X-Tenant-ID"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
