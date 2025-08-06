"""
Settings and configuration for Meetings Service.
"""

from services.common.settings import (
    AliasChoices,
    BaseSettings,
    SettingsConfigDict,
    field,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    db_url_meetings: str = field(
        default=...,
        description="PostgreSQL database connection string for meetings service",
        validation_alias=AliasChoices("DB_URL_MEETINGS"),
    )

    api_email_sync_meetings_key: str = field(
        default=...,  # required
        description="API key for syncing email responses to meetings",
        validation_alias=AliasChoices("API_EMAIL_SYNC_MEETINGS_KEY"),
    )

    api_meetings_office_key: str = field(
        default=...,  # required
        description="API key for meetings service to access office service",
        validation_alias=AliasChoices("API_MEETINGS_OFFICE_KEY"),
    )

    api_meetings_user_key: str = field(
        default=...,  # required
        description="API key for meetings service to access user management service",
        validation_alias=AliasChoices("API_MEETINGS_USER_KEY"),
    )

    api_frontend_meetings_key: str = field(
        default=...,  # required
        description="Frontend API key to access meetings service",
        validation_alias=AliasChoices("API_FRONTEND_MEETINGS_KEY"),
    )

    office_service_url: str = field(
        default=...,
        description="URL for the office service",
        validation_alias=AliasChoices("OFFICE_SERVICE_URL"),
    )

    user_service_url: str = field(
        default="http://localhost:8001",
        description="URL for the user management service",
        validation_alias=AliasChoices("USER_SERVICE_URL"),
    )

    # Logging configuration
    log_level: str = field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
        validation_alias=AliasChoices("LOG_LEVEL"),
    )
    log_format: str = field(
        default="json",
        description="Log format (json or text)",
        validation_alias=AliasChoices("LOG_FORMAT"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
