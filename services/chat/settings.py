"""
Settings and configuration for Chat Service.

Uses custom BaseSettings to manage environment variables and configuration.
"""

from typing import Optional

from services.common.settings import (
    AliasChoices,
    BaseSettings,
    Field,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    db_url_chat: str = Field(
        ...,  # Required field - no default to prevent production mistakes
        description="Database connection string",
        validation_alias=AliasChoices("DB_URL_CHAT"),
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

    # API Keys for service communication
    api_frontend_chat_key: Optional[str] = Field(
        default=None,
        description="Frontend API key to access this Chat service",
    )
    api_chat_user_key: Optional[str] = Field(
        default=None,
        description="Chat service API key to call User Management service",
    )
    api_chat_office_key: Optional[str] = Field(
        default=None,
        description="Chat service API key to call Office service",
    )

    # Service URLs
    user_management_service_url: str = Field(
        default="http://localhost:8001",
        description="User Management service URL",
    )
    office_service_url: str = Field(
        default="http://localhost:8003",
        description="Office service URL",
    )

    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_model: str = Field(default="gpt-4.1-nano", description="LLM model")
    max_tokens: int = Field(
        default=2000, description="Maximum tokens for LLM responses"
    )
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")

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
