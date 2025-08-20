#!/usr/bin/env python3
"""
Configuration settings for the Vespa query service
"""

from services.common.settings import BaseSettings, Field, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    service_name: str = "vespa-query"
    service_port: int = Field(default=8006, env="VESPA_QUERY_PORT")
    service_host: str = Field(default="0.0.0.0", env="VESPA_QUERY_HOST")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")

    # Vespa configuration
    vespa_endpoint: str = Field(default="http://localhost:8080", env="VESPA_ENDPOINT")
    vespa_timeout: int = Field(default=30, env="VESPA_TIMEOUT")
    vespa_application: str = Field(default="briefly", env="VESPA_APPLICATION")

    # Search configuration
    default_max_hits: int = Field(default=10, env="DEFAULT_MAX_HITS")
    max_max_hits: int = Field(default=100, env="MAX_MAX_HITS")
    default_ranking_profile: str = Field(
        default="hybrid", env="DEFAULT_RANKING_PROFILE"
    )

    # Query processing
    query_timeout: int = Field(default=10, env="QUERY_TIMEOUT")
    max_concurrent_queries: int = Field(default=20, env="MAX_CONCURRENT_QUERIES")
    enable_query_caching: bool = Field(default=True, env="ENABLE_QUERY_CACHING")

    # Result processing
    enable_facets: bool = Field(default=True, env="ENABLE_FACETS")
    enable_highlighting: bool = Field(default=True, env="ENABLE_HIGHLIGHTING")
    max_facet_values: int = Field(default=50, env="MAX_FACET_VALUES")

    # Performance tuning
    connection_pool_size: int = Field(default=10, env="CONNECTION_POOL_SIZE")
    keepalive_timeout: int = Field(default=60, env="KEEPALIVE_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay: float = Field(default=0.1, env="RETRY_DELAY")

    # Health check configuration
    health_check_interval_seconds: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout_seconds: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")

    # Security
    enable_user_isolation: bool = Field(default=True, env="ENABLE_USER_ISOLATION")
    max_query_length: int = Field(default=1000, env="MAX_QUERY_LENGTH")

    # API Key configuration for inter-service authentication
    api_frontend_vespa_query_key: str = Field(..., env="API_FRONTEND_VESPA_QUERY_KEY")
    api_vespa_query_user_key: str = Field(..., env="API_VESPA_QUERY_USER_KEY")
    api_vespa_query_office_key: str = Field(..., env="API_VESPA_QUERY_OFFICE_KEY")

    # Service URLs for inter-service communication
    vespa_loader_url: str = Field(default="http://localhost:9001", env="VESPA_LOADER_URL")
    office_service_url: str = Field(default="http://localhost:8003", env="OFFICE_SERVICE_URL")
    user_service_url: str = Field(default="http://localhost:8001", env="USER_SERVICE_URL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )
