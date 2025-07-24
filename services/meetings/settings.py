"""
Settings and configuration for Meetings Service.
"""

from services.common.settings import (
    AliasChoices,
    BaseSettings,
    Field,
    SettingsConfigDict,
)

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    db_url_meetings: str = Field(
        default=...,
        description="PostgreSQL database connection string for meetings service",
        validation_alias=AliasChoices("DB_URL_MEETINGS"),
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