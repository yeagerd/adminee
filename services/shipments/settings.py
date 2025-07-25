
from services.common.settings import BaseSettings, Field, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")
    db_url_shipments: str = Field(..., validation_alias="DB_URL_SHIPMENTS")
    api_frontend_shipments_key: str = Field(
        ..., validation_alias="API_FRONTEND_SHIPMENTS_KEY"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0", validation_alias="REDIS_URL"
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", validation_alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0", validation_alias="CELERY_RESULT_BACKEND"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
