from typing import Optional

from services.common.settings import (
    AliasChoices,
    BaseSettings,
    Field,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """Office Service settings and configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Database configuration
    db_url_office: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Database connection URL",
        validation_alias=AliasChoices("DB_URL_OFFICE"),
    )

    # Service configuration
    SERVICE_NAME: str = Field(default="office-service", description="Service name")
    PORT: int = Field(default=8003, description="Port to bind to")
    HOST: str = Field(default="0.0.0.0", description="Host to bind to")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # API Keys for service communication
    api_frontend_office_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Frontend API key to access this Office service",
    )
    api_chat_office_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Chat service API key to access this Office service",
    )
    api_meetings_office_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Meetings service API key to access this Office service",
    )
    api_backfill_office_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Backfill service API key to access this Office service",
        validation_alias=AliasChoices("API_BACKFILL_OFFICE_KEY"),
    )
    api_office_user_key: Optional[str] = Field(
        default=None,
        description="Office service API key to call User Management service",
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

    # Service URLs
    USER_SERVICE_URL: str = Field(
        default="http://localhost:8001", description="User management service URL"
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
