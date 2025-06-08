from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    SERVICE_NAME: str = "office-service"
    SERVICE_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://user:password@host:5432/briefly"
    REDIS_URL: str = "redis://redis:6379/0"

    USER_MANAGEMENT_SERVICE_URL: str = "http://user-management-service:8000"
    SERVICE_API_KEY: str = "secure-service-key"

    GOOGLE_CLIENT_ID: str = "google-oauth-client-id"
    GOOGLE_CLIENT_SECRET: str = "google-oauth-client-secret"
    MICROSOFT_CLIENT_ID: str = "microsoft-oauth-client-id"
    MICROSOFT_CLIENT_SECRET: str = "microsoft-oauth-client-secret"

    DEFAULT_RATE_LIMIT_PER_HOUR: int = 1000
    PREMIUM_RATE_LIMIT_PER_HOUR: int = 5000

    DEFAULT_CACHE_TTL_SECONDS: int = 900  # 15 minutes
    MAX_CACHE_SIZE_MB: int = 512

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings():
    return Settings()
