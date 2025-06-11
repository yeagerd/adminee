"""
Settings and configuration for User Management Service.

Uses Pydantic Settings to manage environment variables and configuration.
"""

from typing import List, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    database_url: str = Field(
        ...,
        description="PostgreSQL database connection string",
        validation_alias=AliasChoices("DB_URL_USER_MANAGEMENT", "DATABASE_URL"),
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
    encryption_service_salt: Optional[str] = Field(
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
    microsoft_client_id: Optional[str] = Field(
        default=None, description="Microsoft OAuth client ID"
    )
    microsoft_client_secret: Optional[str] = Field(
        default=None, description="Microsoft OAuth client secret"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables from other services


# Global settings instance
settings = Settings()
