"""
Settings and configuration for Chat Service.

Uses Pydantic Settings to manage environment variables and configuration.
"""

from typing import Optional

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./chat_service.db",
        description="Database connection string",
        validation_alias=AliasChoices("DB_URL_CHAT", "DATABASE_URL"),
    )

    # Service Configuration
    service_name: str = Field(default="chat-service", description="Service name")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )

    # API Keys for outgoing service-to-service communication
    # Following the api-{client}-{service}-key naming convention
    api_chat_user_key: Optional[str] = Field(
        default=None,
        description="API key for Chat Service to call User Management service (api-chat-user-key)",
    )
    api_chat_office_key: Optional[str] = Field(
        default=None,
        description="API key for Chat Service to call Office service (api-chat-office-key)",
    )

    # Service URLs
    user_management_service_url: str = Field(
        default="http://localhost:8001",
        description="User Management service URL",
    )
    office_service_url: str = Field(
        default="http://localhost:8080",
        description="Office service URL",
    )

    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_model: str = Field(default="gpt-4.1-nano", description="LLM model")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()
