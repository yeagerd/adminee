"""
Centralized logging configuration for all Briefly services.

This module provides consistent logging setup across all services including:
- Structured logging with JSON format
- Request ID tracking for HTTP requests
- User context extraction
- Performance timing
- Error tracking with proper context

Usage:
    from services.common.logging_config import setup_service_logging

    # In your service main.py
    setup_service_logging(
        service_name="chat-service",
        log_level="INFO",
        log_format="json"
    )
"""

import logging
import logging.config
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable

import structlog
from fastapi import Request, Response

# Context variables for request-specific data
request_id_var: ContextVar[str] = ContextVar("request_id", default="uninitialized")
user_id_var: ContextVar[str] = ContextVar("user_id", default="anonymous")


class RequestContextFilter(logging.Filter):
    """Add request context from contextvars to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter that adds context from contextvars."""
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        if not hasattr(record, "service_name"):
            record.service_name = getattr(record, "service", "unknown")
        return True


def add_request_context(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add request and user ID to all log entries."""
    request_id = request_id_var.get()
    user_id = user_id_var.get()
    if request_id and request_id != "uninitialized":
        event_dict["request_id"] = request_id
    if user_id and user_id != "anonymous":
        event_dict["user_id"] = user_id
    return event_dict


def add_service_context(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add service name to all log entries."""
    # Get service name from the logger name or context
    logger_name = event_dict.get("logger", "")
    if logger_name.startswith("services."):
        # Extract service name from logger path like "services.chat.api"
        service_parts = logger_name.split(".")
        if len(service_parts) >= 2:
            event_dict["service"] = service_parts[1]  # e.g., "chat", "user", "office"
    return event_dict


def add_file_line_context(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add file and line number context to log entries."""
    import inspect

    # Get the caller's frame (skip this function and the structlog wrapper)
    frame = inspect.currentframe()
    try:
        # Go up the call stack to find the actual caller
        # We need to skip more frames to get past the logging system
        for _ in range(8):  # Skip more frames to get to the actual caller
            if frame:
                frame = frame.f_back
            if not frame:
                break

        if frame:
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno

            # Skip if we're still in the logging system
            if "logging" in filename or "structlog" in filename:
                # Go up a few more frames
                for _ in range(3):
                    if frame:
                        frame = frame.f_back
                    if not frame:
                        break
                if frame:
                    filename = frame.f_code.co_filename
                    lineno = frame.f_lineno

            # Extract just the filename without path for cleaner output
            if "/" in filename:
                filename = filename.split("/")[-1]
            elif "\\" in filename:
                filename = filename.split("\\")[-1]

            event_dict["file"] = filename
            event_dict["line"] = lineno
    except Exception:
        # If we can't get the frame info, just continue
        pass
    finally:
        # Clean up the frame reference
        del frame

    return event_dict


class EnhancedTextRenderer:
    """Custom text renderer for better debugging during development."""

    def __init__(self, service_name: str):
        self.service_name = service_name

    def __call__(
        self,
        logger: structlog.types.WrappedLogger,
        method_name: str,
        event_dict: structlog.types.EventDict,
    ) -> str:
        """Render log entry as enhanced text format."""
        # Extract key fields
        timestamp = event_dict.get("timestamp", "")
        level = event_dict.get("level", "INFO").upper()
        logger_name = event_dict.get("logger", "")
        message = event_dict.get("event", "")

        # Get service name (prefer explicit service, fallback to extracted)
        service = event_dict.get("service", self.service_name)

        # Get request ID and truncate to last 4 chars for readability
        request_id = event_dict.get("request_id", "")
        if request_id and request_id != "uninitialized" and len(request_id) > 0:
            request_id_suffix = (
                f"[{request_id[-4:]}]" if len(request_id) >= 4 else f"[{request_id}]"
            )
        else:
            request_id_suffix = ""

        # Get file and line info
        file_info = ""
        if "file" in event_dict and "line" in event_dict:
            file_info = f" {event_dict['file']}:{event_dict['line']}"

        # Get user ID if present
        user_info = ""
        user_id = event_dict.get("user_id", "")
        if user_id and user_id != "anonymous":
            user_info = f" | User: {user_id}"

        # Build the enhanced log line
        parts = [
            timestamp,
            f"[{service}]",
            f"[{level}]",
            request_id_suffix,
            f"{logger_name}{file_info}",
            f"- {message}{user_info}",
        ]

        # Add extra context as key=value pairs
        extra_context = []
        for key, value in event_dict.items():
            if key not in [
                "timestamp",
                "level",
                "logger",
                "event",
                "service",
                "request_id",
                "user_id",
                "file",
                "line",
            ]:
                if isinstance(value, (str, int, float, bool)):
                    extra_context.append(f"{key}={value}")
                else:
                    extra_context.append(f"{key}={str(value)[:50]}...")

        if extra_context:
            parts.append(f" | {' '.join(extra_context)}")

        return " ".join(filter(None, parts))


def setup_service_logging(
    service_name: str,
    log_level: str = "INFO",
    log_format: str = "json",
    enable_request_logging: bool = True,
) -> None:
    """
    Set up logging configuration for a service.

    Args:
        service_name: Name of the service (e.g., "chat-service")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type ("json" or "text")
        enable_request_logging: Whether to enable HTTP request logging
    """

    # Configure structlog for consistent structured logging
    processors: list = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_request_context,  # Add our custom context processor
        add_service_context,  # Add service context
        add_file_line_context,  # Add file/line context
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add the appropriate renderer
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Use our custom text renderer for better debugging
        processors.append(EnhancedTextRenderer(service_name))

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Always use a pass-through formatter for structlog output
    formatter = logging.Formatter("%(message)s")

    # Configure root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestContextFilter())

    # Set service name in all log records
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        record.service_name = service_name
        return record

    logging.setLogRecordFactory(record_factory)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=[handler],
        force=True,  # Override any existing configuration
    )

    # Silence verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured for {service_name}",
        extra={
            "log_level": log_level,
            "log_format": log_format,
            "request_logging": enable_request_logging,
        },
    )


def create_request_logging_middleware() -> Callable:
    """
    Create HTTP request logging middleware for FastAPI.

    Returns:
        Async middleware function for FastAPI
    """

    async def log_requests(request: Request, call_next: Callable) -> Response:
        """
        Middleware to log all incoming requests and responses with context.
        """
        # Get request ID from header or generate a new one
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        request_id_var.set(request_id)

        # Get user ID from header, with fallbacks to path and query params
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            try:
                user_id = request.path_params.get("user_id")
            except (AttributeError, KeyError):
                user_id = None
        if not user_id:
            user_id = request.query_params.get("user_id")

        user_id_var.set(user_id or "anonymous")

        start_time = time.time()
        logger = get_logger("http.requests")

        # Log incoming request
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": (
                    str(request.query_params) if request.query_params else None
                ),
                "client_ip": (
                    getattr(request.client, "host", "unknown")
                    if request.client
                    else "unknown"
                ),
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type"),
            },
        )

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        log_level = logging.ERROR if response.status_code >= 400 else logging.INFO
        status_emoji = "❌" if response.status_code >= 400 else "✅"

        logger.log(
            log_level,
            f"{status_emoji} {request.method} {request.url.path} → {response.status_code} ({process_time:.3f}s)",
            extra={
                "status_code": response.status_code,
                "process_time": process_time,
                "method": request.method,
                "path": request.url.path,
            },
        )

        # Special logging for 404 errors to help with debugging
        if response.status_code == 404:
            logger.error(
                f"🔍 404 DEBUG - Endpoint not found: {request.method} {request.url.path}",
                extra={
                    "requested_endpoint": f"{request.method} {request.url.path}",
                    "suggestion": "Check if the endpoint path and HTTP method are correct",
                },
            )

        return response

    return log_requests


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def log_service_startup(service_name: str, **kwargs: Any) -> None:
    """Log service startup with configuration details."""
    logger = get_logger("startup")
    logger.info(f"Starting {service_name}", service=service_name, **kwargs)


def log_service_shutdown(service_name: str) -> None:
    """Log service shutdown."""
    logger = get_logger("shutdown")
    logger.info(f"Shutting down {service_name}", service=service_name)
