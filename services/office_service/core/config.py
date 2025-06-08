from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./services/office_service/office_service.db"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"

    # External Services
    USER_MANAGEMENT_SERVICE_URL: str = "http://localhost:8001"
    SERVICE_API_KEY: str = "your-service-api-key-here"

    # Application Configuration
    APP_NAME: str = "Office Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    DEFAULT_RATE_LIMIT: int = 1000  # requests per hour

    # Cache Configuration
    DEFAULT_CACHE_TTL_SECONDS: int = 900  # 15 minutes default
    CACHE_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
