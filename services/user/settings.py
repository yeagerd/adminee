"""
Settings and configuration for User Management Service.

Uses custom BaseSettings to manage environment variables and configuration.
"""

from typing import List, Optional

from services.common.settings import (
    AliasChoices,
    BaseSettings,
    SettingsConfigDict,
    field,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    db_url_user: str = field(
        default=...,
        description="PostgreSQL database connection string",
        validation_alias=AliasChoices("DB_URL_USER"),
    )

    # Service Configuration
    service_name: str = field(default="user", description="Service name")
    host: str = field(default="0.0.0.0", description="Host to bind to")
    port: int = field(default=8001, description="Port to bind to")
    debug: bool = field(default=False, description="Debug mode")
    environment: str = field(
        default="development",
        description="Environment (development, staging, production)",
    )

    # CORS Configuration
    cors_origins: List[str] = field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )

    # Security Configuration
    api_frontend_user_key: str = field(
        ...,
        description="Frontend API key to access User Management service",
    )
    api_chat_user_key: str = field(
        ...,
        description="Chat service API key to access User Management service",
    )
    api_office_user_key: str = field(
        ...,
        description="Office service API key to access User Management service",
    )
    api_meetings_user_key: str = field(
        ...,
        description="Meetings service API key to access User Management service",
    )
    token_encryption_salt: Optional[str] = field(
        default=None,
        description="Base64-encoded service salt for token encryption key derivation",
    )
    jwt_verify_signature: bool = field(
        default=True,
        description="Whether to verify JWT signatures (set to False for development)",
    )

    # Redis Configuration (for caching and background jobs)
    redis_url: str = field(
        default="redis://localhost:6379", description="Redis connection string"
    )

    # Celery Configuration
    celery_broker_url: str = field(
        default="redis://localhost:6379/0", description="Celery broker URL"
    )
    celery_result_backend: str = field(
        default="redis://localhost:6379/0", description="Celery result backend URL"
    )

    # OAuth Provider Configuration
    google_client_id: Optional[str] = field(
        default=None, description="Google OAuth client ID"
    )
    google_client_secret: Optional[str] = field(
        default=None, description="Google OAuth client secret"
    )
    azure_ad_client_id: Optional[str] = field(
        default=None, description="Microsoft OAuth client ID"
    )
    azure_ad_client_secret: Optional[str] = field(
        default=None, description="Microsoft OAuth client secret"
    )
    azure_ad_tenant_id: Optional[str] = field(
        default=None,
        description="Azure AD tenant ID for tenant-specific OAuth endpoints",
    )

    # OAuth Redirect Configuration
    oauth_redirect_uri: str = field(
        default="http://localhost:8001/oauth/callback",
        description="OAuth callback redirect URI for all providers",
    )
    oauth_base_url: str = field(
        default="http://localhost:8001",
        description="Base URL for OAuth callbacks (used to construct redirect URI)",
    )

    # Token Management Configuration
    refresh_timeout_seconds: float = field(
        default=30.0,
        description="Timeout for waiting on concurrent token refresh operations (seconds)",
    )

    # NextAuth Configuration
    nextauth_jwt_key: Optional[str] = field(
        default=None, description="NextAuth JWT secret key for token verification"
    )
    nextauth_issuer: Optional[str] = field(
        default="nextauth", description="NextAuth JWT issuer claim"
    )
    nextauth_audience: Optional[str] = field(
        default="briefly-backend", description="NextAuth JWT audience claim"
    )

    # Logging Configuration
    log_level: str = field(default="INFO", description="Logging level")
    log_format: str = field(default="json", description="Log format (json or text)")

    # Pagination settings
    pagination_secret_key: str = field(
        default="your-secret-key-change-in-production",
        validation_alias="PAGINATION_SECRET_KEY",
        description="Secret key for pagination token signing",
    )
    pagination_token_expiry: int = field(
        default=3600,
        validation_alias="PAGINATION_TOKEN_EXPIRY",
        description="Pagination token expiration time in seconds",
    )
    pagination_max_page_size: int = field(
        default=100,
        validation_alias="PAGINATION_MAX_PAGE_SIZE",
        description="Maximum allowed page size for pagination",
    )
    pagination_default_page_size: int = field(
        default=20,
        validation_alias="PAGINATION_DEFAULT_PAGE_SIZE",
        description="Default page size for pagination",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables from other services
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
