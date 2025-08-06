"""
Common utilities and configurations for Briefly services.
"""

from services.common.config_secrets import (
    clear_cache,
    get_database_url,
    get_llama_cloud_api_key,
    get_openai_api_key,
    get_redis_url,
    get_secret,
    get_token_encryption_salt,
)
from services.common.telemetry import (
    add_span_attributes,
    get_tracer,
    record_exception,
    setup_telemetry,
)


def get_async_database_url(url: str) -> str:
    """Convert database URL to async format for async SQLAlchemy drivers."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    else:
        return url


__all__ = [
    "setup_telemetry",
    "get_tracer",
    "add_span_attributes",
    "record_exception",
    "get_secret",
    "get_database_url",
    "get_redis_url",
    "get_token_encryption_salt",
    "get_openai_api_key",
    "get_llama_cloud_api_key",
    "clear_cache",
    "get_async_database_url",
]
