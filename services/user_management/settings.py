"""
Settings and configuration for User Management Service.

Uses Pydantic Settings to manage environment variables and configuration.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/briefly",
        description="PostgreSQL database connection string",
    )

    # Service Configuration
    service_name: str = Field(default="user-management", description="Service name")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8001, description="Port to bind to")
    debug: bool = Field(default=False, description="Debug mode")

    # Security Configuration
    service_api_key: str = Field(
        default="dev-service-key",
        description="API key for service-to-service authentication",
    )
    token_encryption_salt: str = Field(
        default="default-salt-change-in-production",
        description="Salt for token encryption key derivation",
    )

    # Clerk Configuration
    clerk_secret_key: Optional[str] = Field(
        default=None, description="Clerk secret key for JWT validation"
    )
    clerk_webhook_secret: Optional[str] = Field(
        default=None, description="Clerk webhook secret for signature verification"
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
