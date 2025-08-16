#!/usr/bin/env python3
"""
Configuration settings for the Vespa loader service
"""

from services.common.settings import BaseSettings, Field, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = "vespa-loader"
    service_port: int = Field(default=9001, env="VESPA_LOADER_PORT")
    service_host: str = Field(default="0.0.0.0", env="VESPA_LOADER_HOST")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Vespa configuration
    vespa_endpoint: str = Field(
        default="http://localhost:8080",
        env="VESPA_ENDPOINT"
    )
    vespa_timeout: int = Field(default=30, env="VESPA_TIMEOUT")
    vespa_batch_size: int = Field(default=100, env="VESPA_BATCH_SIZE")
    
    # Embedding configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    embedding_batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    embedding_timeout: int = Field(default=60, env="EMBEDDING_TIMEOUT")
    
    # Content processing
    max_content_length: int = Field(default=10000, env="MAX_CONTENT_LENGTH")
    enable_html_stripping: bool = Field(default=True, env="ENABLE_HTML_STRIPPING")
    enable_email_header_cleaning: bool = Field(default=True, env="ENABLE_EMAIL_HEADER_CLEANING")
    
    # Batch processing
    max_concurrent_batches: int = Field(default=5, env="MAX_CONCURRENT_BATCHES")
    batch_timeout: int = Field(default=300, env="BATCH_TIMEOUT")
    
    # Retry configuration
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay_seconds: float = Field(default=1.0, env="RETRY_DELAY_SECONDS")
    
    # Rate limiting
    max_documents_per_second: int = Field(default=100, env="MAX_DOCUMENTS_PER_SECOND")
    
    # Health check configuration
    health_check_interval_seconds: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout_seconds: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
