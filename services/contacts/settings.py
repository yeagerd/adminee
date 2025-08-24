from typing import Optional

from services.common.settings import (
    AliasChoices,
    BaseSettings,
    Field,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """Contacts Service settings and configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Database configuration
    db_url_contacts: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Database connection URL",
        validation_alias=AliasChoices("DB_URL_CONTACTS"),
    )

    # Service configuration
    SERVICE_NAME: str = Field(default="contacts-service", description="Service name")
    PORT: int = Field(default=8007, description="Port to bind to")
    HOST: str = Field(default="0.0.0.0", description="Host to bind to")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # API Keys for service communication
    api_frontend_contacts_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Frontend API key to access this Contacts service",
    )
    api_contacts_user_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="User service API key to access this Contacts service",
    )
    api_contacts_office_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Office service API key to access this Contacts service",
    )
    api_chat_contacts_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Chat service API key to access this Contacts service",
    )
    api_meetings_contacts_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Meetings service API key to access this Contacts service",
    )
    api_shipments_contacts_key: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Shipments service API key to access this Contacts service",
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
    APP_NAME: str = Field(default="contacts-service", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )

    # Service URLs
    USER_SERVICE_URL: str = Field(
        default="http://localhost:8001", description="User management service URL"
    )
    OFFICE_SERVICE_URL: str = Field(
        default="http://localhost:8003", description="Office service URL"
    )
    CHAT_SERVICE_URL: str = Field(
        default="http://localhost:8002", description="Chat service URL"
    )
    MEETINGS_SERVICE_URL: str = Field(
        default="http://localhost:8005", description="Meetings service URL"
    )
    SHIPMENTS_SERVICE_URL: str = Field(
        default="http://localhost:8004", description="Shipments service URL"
    )

    # JWT Configuration
    jwt_verify_signature: bool = Field(
        default=True, description="Whether to verify JWT signatures"
    )
    nextauth_issuer: str = Field(default="nextauth", description="NextAuth JWT issuer")
    nextauth_audience: Optional[str] = Field(
        default=None, description="NextAuth JWT audience"
    )
    nextauth_jwt_key: Optional[str] = Field(
        default=None, description="NextAuth JWT secret key"
    )

    # PubSub Configuration
    PUBSUB_PROJECT_ID: str = Field(
        default="briefly-dev", description="Google Cloud Pub/Sub project ID"
    )
    PUBSUB_EMULATOR_HOST: Optional[str] = Field(
        default="localhost:8085",
        description="Pub/Sub emulator host for local development",
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
