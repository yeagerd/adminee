"""
Settings and configuration for Chat Service.

Uses custom BaseSettings to manage environment variables and configuration.
"""

from typing import Optional

from services.common.settings import (
    AliasChoices,
    BaseSettings,
    field,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    db_url_chat: str = field(
        ...,  # Required field - no default to prevent production mistakes
        description="Database connection string",
        validation_alias=AliasChoices("DB_URL_CHAT"),
    )

    # Service Configuration
    service_name: str = field(default="chat-service", description="Service name")
    host: str = field(default="0.0.0.0", description="Host to bind to")
    port: int = field(default=8002, description="Port to bind to")
    debug: bool = field(default=False, description="Debug mode")
    environment: str = field(
        default="development",
        description="Environment (development, staging, production)",
    )

    # API Keys for service communication
    api_frontend_chat_key: Optional[str] = field(
        ...,
        description="Frontend API key to access this Chat service",
        validation_alias=AliasChoices("API_FRONTEND_CHAT_KEY"),
    )
    api_chat_user_key: Optional[str] = field(
        ...,
        description="Chat service API key to call User Management service",
        validation_alias=AliasChoices("API_CHAT_USER_KEY"),
    )
    api_chat_office_key: Optional[str] = field(
        ...,
        description="Chat service API key to call Office service",
        validation_alias=AliasChoices("API_CHAT_OFFICE_KEY"),
    )

    # Service URLs
    user_service_url: str = field(
        ...,
        description="User management service URL",
        validation_alias=AliasChoices(
            "USER_SERVICE_URL", "USER_MANAGEMENT_SERVICE_URL"
        ),
    )
    office_service_url: str = field(
        default=...,
        description="Office service URL",
    )

    # LLM Configuration
    llm_provider: str = field(default="openai", description="LLM provider")
    llm_model: str = field(default="gpt-4.1-nano", description="LLM model")
    max_tokens: int = field(
        default=2000, description="Maximum tokens for LLM responses"
    )
    openai_api_key: Optional[str] = field(default=None, description="OpenAI API key")

    # Logging Configuration
    log_level: str = field(default="INFO", description="Logging level")
    log_format: str = field(default="json", description="Log format (json or text)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global _settings
    if _settings is None:
        # In production, the required fields are set in the environment variables.
        # In unit tests, we patch or mock the settings object.
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
