"""
Settings and configuration for User Management Service.

Uses Pydantic Settings to manage environment variables and configuration.
"""

from typing import List, Optional

from pydantic import AliasChoices, Field  # Removed ConfigDict
from pydantic_settings import (  # Added SettingsConfigDict
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    db_url_user_management: str = Field(
        default=None,
        description="PostgreSQL database connection string",
        validation_alias=AliasChoices("DB_URL_USER_MANAGEMENT"),
    )

    # Service Configuration
    service_name: str = Field(default="user-management", description="Service name")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8001, description="Port to bind to")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )

    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )

    # Security Configuration
    api_frontend_user_key: Optional[str] = Field(
        default=None,
        description="Frontend API key to access User Management service",
    )
    api_chat_user_key: Optional[str] = Field(
        default=None,
        description="Chat service API key to access User Management service",
    )
    api_office_user_key: Optional[str] = Field(
        default=None,
        description="Office service API key to access User Management service",
    )
    token_encryption_salt: Optional[str] = Field(
        default=None,
        description="Base64-encoded service salt for token encryption key derivation",
    )

    # Clerk Configuration
    clerk_secret_key: Optional[str] = Field(
        default=None, description="Clerk secret key for JWT validation"
    )
    clerk_webhook_secret: Optional[str] = Field(
        default=None, description="Clerk webhook secret for signature verification"
    )
    clerk_jwt_key: Optional[str] = Field(
        default=None,
        description="Clerk JWKS public key for networkless JWT verification",
    )
    jwt_verify_signature: bool = Field(
        default=True,
        description="Enable JWT signature verification (requires Clerk public key)",
    )

    # Redis Configuration (for caching and background jobs)
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection string"
    )

    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0", description="Celery result backend URL"
    )

    # OAuth Provider Configuration
    google_client_id: Optional[str] = Field(
        default=None, description="Google OAuth client ID"
    )
    google_client_secret: Optional[str] = Field(
        default=None, description="Google OAuth client secret"
    )
    azure_ad_client_id: Optional[str] = Field(
        default=None, description="Microsoft OAuth client ID"
    )
    azure_ad_client_secret: Optional[str] = Field(
        default=None, description="Microsoft OAuth client secret"
    )
    azure_ad_tenant_id: Optional[str] = Field(
        default=None,
        description="Azure AD tenant ID for tenant-specific OAuth endpoints",
    )

    # OAuth Redirect Configuration
    oauth_redirect_uri: str = Field(
        default="http://localhost:8001/oauth/callback",
        description="OAuth callback redirect URI for all providers",
    )
    oauth_base_url: str = Field(
        default="http://localhost:8001",
        description="Base URL for OAuth callbacks (used to construct redirect URI)",
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")

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
