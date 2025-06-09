"""
Logging configuration for the Office Service.

Provides structured JSON logging with proper formatting and log levels
for production and development environments.
"""

import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict

from core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Formats log records as JSON with consistent structure including
    timestamp, level, message, and additional context.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        # Build base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up JSON logging with appropriate log levels and handlers
    based on the environment configuration.
    """
    # Determine log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": (
                    "json" if settings.ENVIRONMENT == "production" else "simple"
                ),
                "level": log_level,
            },
        },
        "loggers": {
            # Office Service loggers
            "services.office_service": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # FastAPI loggers
            "fastapi": {
                "level": logging.INFO,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": logging.INFO,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": logging.INFO,
                "handlers": ["console"],
                "propagate": False,
            },
            # HTTP client loggers
            "httpx": {
                "level": logging.WARNING,
                "handlers": ["console"],
                "propagate": False,
            },
            # Database loggers
            "databases": {
                "level": logging.WARNING,
                "handlers": ["console"],
                "propagate": False,
            },
            "ormar": {
                "level": logging.WARNING,
                "handlers": ["console"],
                "propagate": False,
            },
            # Redis loggers
            "redis": {
                "level": logging.WARNING,
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": logging.WARNING,
            "handlers": ["console"],
        },
    }

    # Apply the configuration
    logging.config.dictConfig(logging_config)

    # Log startup message
    logger = logging.getLogger("services.office_service.core.logging_config")
    logger.info(
        "Logging configured",
        extra={
            "environment": settings.ENVIRONMENT,
            "log_level": settings.LOG_LEVEL,
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: The logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Context manager for adding request context to logs
class LogContext:
    """
    Context manager for adding request-specific context to log records.

    Usage:
        with LogContext(request_id="abc123", user_id="user456"):
            logger.info("Processing request")
    """

    def __init__(self, **context: Any):
        """
        Initialize log context.

        Args:
            **context: Key-value pairs to add to log records
        """
        self.context = context
        self.old_factory = logging.getLogRecordFactory()

    def __enter__(self) -> "LogContext":
        """Enter the context manager."""

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager."""
        logging.setLogRecordFactory(self.old_factory)
