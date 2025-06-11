from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Office Service settings and configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Database configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./office_service.db",
        description="Database connection URL",
        validation_alias=AliasChoices("DB_URL_OFFICE", "DATABASE_URL"),
    )

    # Service configuration
    SERVICE_NAME: str = Field(default="office-service", description="Service name")
    PORT: int = Field(default=8003, description="Port to bind to")
    HOST: str = Field(default="0.0.0.0", description="Host to bind to")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # API Keys for inter-service communication
    api_key_office: str = Field(
        default="default-office-key",
        description="Office service access key (required to call this service)",
    )
    api_key_user_management: Optional[str] = Field(
        default=None,
        description="User Management service access key (to call User Management service)",
    )

    # Redis configuration for caching and background tasks
    REDIS_URL: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )

    # Rate limiting configuration
    RATE_LIMIT_REQUESTS: int = Field(
        default=1000, description="Rate limit requests per minute"
    )
    RATE_LIMIT_DURATION: int = Field(
        default=60, description="Rate limit duration in seconds"
    )

    # Cache configuration
    CACHE_TTL: int = Field(default=300, description="Cache TTL in seconds")
    CACHE_MAX_SIZE: int = Field(default=1000, description="Maximum cache entries")

    # Logging configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")

    # Application info
    APP_NAME: str = Field(default="office-service", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )

    # Demo mode configuration
    DEMO_MODE: bool = Field(default=False, description="Enable demo mode")

    # Service URLs
    USER_MANAGEMENT_SERVICE_URL: str = Field(
        default="http://localhost:8001", description="User management service URL"
    )


# Global settings instance
settings = Settings()
