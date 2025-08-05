from services.common.settings import BaseSettings, Field, SettingsConfigDict, PaginationSettings


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

    # JWT Authentication settings (optional - for direct JWT token support)
    jwt_verify_signature: bool = Field(
        default=True, validation_alias="JWT_VERIFY_SIGNATURE"
    )
    nextauth_issuer: str = Field(default="nextauth", validation_alias="NEXTAUTH_ISSUER")
    nextauth_audience: str | None = Field(
        default=None, validation_alias="NEXTAUTH_AUDIENCE"
    )
    nextauth_jwt_key: str | None = Field(
        default=None, validation_alias="NEXTAUTH_JWT_KEY"
    )

    # Pagination settings
    pagination_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        validation_alias="PAGINATION_SECRET_KEY",
        description="Secret key for pagination token signing"
    )
    pagination_token_expiry: int = Field(
        default=3600,
        validation_alias="PAGINATION_TOKEN_EXPIRY",
        description="Pagination token expiration time in seconds"
    )
    pagination_max_page_size: int = Field(
        default=100,
        validation_alias="PAGINATION_MAX_PAGE_SIZE",
        description="Maximum allowed page size for pagination"
    )
    pagination_default_page_size: int = Field(
        default=20,
        validation_alias="PAGINATION_DEFAULT_PAGE_SIZE",
        description="Default page size for pagination"
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
