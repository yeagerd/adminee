#!/usr/bin/env python3
"""
Configuration settings for the Vespa loader service
"""

from services.common.settings import BaseSettings, Field, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    service_name: str = "vespa-loader"
    service_port: int = Field(default=9001, validation_alias="VESPA_LOADER_PORT")
    service_host: str = Field(default="0.0.0.0", validation_alias="VESPA_LOADER_HOST")
    ingest_endpoint: str = Field(
        default="http://localhost:9001/ingest",
        validation_alias="VESPA_LOADER_INGEST_ENDPOINT",
    )

    # API Keys for inter-service authentication
    api_frontend_vespa_loader_key: str = Field(
        ..., validation_alias="API_FRONTEND_VESPA_LOADER_KEY"
    )
    api_vespa_loader_user_key: str = Field(
        ..., validation_alias="API_VESPA_LOADER_USER_KEY"
    )
    api_vespa_loader_office_key: str = Field(
        ..., validation_alias="API_VESPA_LOADER_OFFICE_KEY"
    )

    # Service URLs for inter-service communication
    user_service_url: str = Field(..., validation_alias="USER_SERVICE_URL")
    office_service_url: str = Field(..., validation_alias="OFFICE_SERVICE_URL")

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")

    # Vespa configuration
    vespa_endpoint: str = Field(
        default="http://localhost:8080", validation_alias="VESPA_ENDPOINT"
    )
    vespa_timeout: int = Field(default=30, validation_alias="VESPA_TIMEOUT")
    vespa_batch_size: int = Field(default=100, validation_alias="VESPA_BATCH_SIZE")

    # Embedding configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_batch_size: int = Field(
        default=32, validation_alias="EMBEDDING_BATCH_SIZE"
    )
    embedding_timeout: int = Field(default=60, validation_alias="EMBEDDING_TIMEOUT")

    # Content processing
    max_content_length: int = Field(
        default=10000, validation_alias="MAX_CONTENT_LENGTH"
    )
    enable_html_stripping: bool = Field(
        default=True, validation_alias="ENABLE_HTML_STRIPPING"
    )
    enable_email_header_cleaning: bool = Field(
        default=True, validation_alias="ENABLE_EMAIL_HEADER_CLEANING"
    )

    # Batch processing
    max_concurrent_batches: int = Field(
        default=5, validation_alias="MAX_CONCURRENT_BATCHES"
    )
    batch_timeout: int = Field(default=300, validation_alias="BATCH_TIMEOUT")

    # Retry configuration
    max_retries: int = Field(default=3, validation_alias="MAX_RETRIES")
    retry_delay_seconds: float = Field(
        default=1.0, validation_alias="RETRY_DELAY_SECONDS"
    )

    # Rate limiting
    max_documents_per_second: int = Field(
        default=100, validation_alias="MAX_DOCUMENTS_PER_SECOND"
    )
    api_rate_limit_max_requests: int = Field(
        default=100, validation_alias="API_RATE_LIMIT_MAX_REQUESTS"
    )
    api_rate_limit_window_seconds: int = Field(
        default=60, validation_alias="API_RATE_LIMIT_WINDOW_SECONDS"
    )

    # Pub/Sub configuration
    pubsub_project_id: str = Field(
        default="briefly-dev", validation_alias="PUBSUB_PROJECT_ID"
    )
    pubsub_emulator_host: str = Field(
        default="localhost:8085", validation_alias="PUBSUB_EMULATOR_HOST"
    )
    enable_pubsub_consumer: bool = Field(
        default=True, validation_alias="ENABLE_PUBSUB_CONSUMER"
    )

    # Health check configuration
    health_check_interval_seconds: int = Field(
        default=30, validation_alias="HEALTH_CHECK_INTERVAL"
    )
    health_check_timeout_seconds: int = Field(
        default=5, validation_alias="HEALTH_CHECK_TIMEOUT"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )
