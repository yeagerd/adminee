from typing import Any, Dict, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .secrets import (
    get_api_frontend_office_key,
    get_api_office_user_key,
    get_office_database_url,
    get_redis_url,
)


class Settings(BaseSettings):
    """Office Service settings and configuration.
    
    This class now uses the secrets module to load sensitive configuration.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
    )

    # Environment and service configuration
    ENVIRONMENT: str = Field(
        default="development",
        description="Current environment (development, staging, production)",
    )
    SERVICE_NAME: str = Field(
        default="office-service", 
        description="Service name"
    )
    PORT: int = Field(
        default=8003, 
        description="Port to bind to"
    )
    HOST: str = Field(
        default="0.0.0.0", 
        description="Host to bind to"
    )
    DEBUG: bool = Field(
        default=False, 
        description="Debug mode"
    )
    DEMO_MODE: bool = Field(
        default=False,
        description="Whether demo mode is enabled"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format (json, console)"
    )

    # Database configuration
    db_url_office: str = Field(
        default_factory=get_office_database_url,
        description="Database connection URL"
    )

    # API Keys for service communication
    api_frontend_office_key: str = Field(
        default_factory=get_api_frontend_office_key,
        description="Frontend API key to access this Office service",
    )
    api_office_user_key: Optional[str] = Field(
        default_factory=get_api_office_user_key,
        description="Office service API key to call User Management service",
    )

    # Redis configuration for caching and background tasks
    REDIS_URL: str = Field(
        default_factory=get_redis_url,
        description="Redis connection URL"
    )

    # Logging configuration
    LOG_LEVEL: str = Field(
        default_factory=get_log_level,
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default_factory=get_log_format,
        description="Log format (json, console)"
    )

    # Rate limiting configuration
    RATE_LIMIT_REQUESTS: int = Field(
        default=1000, 
        description="Rate limit requests per minute"
    )
    RATE_LIMIT_DURATION: int = Field(
        default=60, 
        description="Rate limit duration in seconds"
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
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary.
    
    This function initializes the settings using the secrets module.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
