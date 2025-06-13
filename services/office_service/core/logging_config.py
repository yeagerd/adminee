"""
Logging configuration for the Office Service.

Provides centralized logging setup with structured logging,
request IDs, and appropriate log levels for different environments.
"""

import json
import logging
import logging.config
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.office_service.core.settings import Settings, get_settings


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
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add module, function, and line number if available
        if hasattr(record, 'module'):
            log_entry["module"] = record.module
        if hasattr(record, 'funcName'):
            log_entry["function"] = record.funcName
        if hasattr(record, 'lineno'):
            log_entry["line"] = record.lineno

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra attributes
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ["args", "asctime", "created", "exc_info", "exc_text",
                             "filename", "funcName", "id", "levelname", "levelno",
                             "lineno", "module", "msecs", "message", "msg",
                             "name", "pathname", "process", "processName",
                             "relativeCreated", "stack_info", "thread", "threadName"]:
                    log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging(settings: Optional[Settings] = None) -> None:
    """
    Configure structured logging for the application.

    Sets up JSON logging with appropriate log levels and handlers
    based on the environment configuration.

    Args:
        settings: Optional settings instance. If not provided, will use get_settings()
    """
    if settings is None:
        settings = get_settings()
    
    # Get log level and format from settings
    log_level = settings.LOG_LEVEL.upper()
    log_format = settings.LOG_FORMAT.lower()
    
    # Convert log level string to logging level
    numeric_level = getattr(logging, log_level, logging.INFO)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # Create console handler with appropriate formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers with appropriate levels
    loggers = {
        # Application loggers
        "app": numeric_level,
        "services": numeric_level,
        
        # Framework loggers
        "uvicorn": logging.INFO,
        "uvicorn.error": logging.WARNING,
        "uvicorn.access": logging.WARNING,
        "fastapi": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "urllib3": logging.WARNING,
    }

    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    This ensures that logging is properly configured before returning the logger.

    Args:
        name: The logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    # Ensure logging is configured
    if not logging.root.handlers:
        setup_logging()
    
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

    def __enter__(self) -> None:
        """Enter the context manager."""
        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager."""
        logging.setLogRecordFactory(self.old_factory)
