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
from typing import Any, Callable

import structlog
from fastapi import Request, Response


class RequestContextFilter(logging.Filter):
    """Add request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Add default values if not present
        if not hasattr(record, "request_id"):
            record.request_id = None
        if not hasattr(record, "user_id"):
            record.user_id = None
        if not hasattr(record, "service_name"):
            record.service_name = getattr(record, "service", "unknown")
        return True


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
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if log_format == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
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
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        user_context = ""

        logger = logging.getLogger("http.requests")

        # Extract user context from headers only (don't consume request body)
        # The request body will be consumed by FastAPI for endpoint processing
        if request.method in ["POST", "PUT", "PATCH"]:
            # Try to get user context from headers instead of body
            user_id_header = request.headers.get("X-User-Id")
            if user_id_header:
                user_context = f" | User: {user_id_header}"

            # Log that we're not reading the body to avoid conflicts
            logger.debug(f"[{request_id}] Skipping body read to avoid consumption")

        # Extract user_id from query params if not found in body
        if not user_context and "user_id" in request.query_params:
            user_context = f" | User: {request.query_params['user_id']}"

        # Extract from path parameters (e.g., /users/{user_id}/preferences)
        if not user_context and hasattr(request, "path_params"):
            if "user_id" in request.path_params:
                user_context = f" | User: {request.path_params['user_id']}"

        # Log incoming request
        logger.info(
            f"[{request_id}] → {request.method} {request.url.path}{user_context}",
            extra={
                "request_id": request_id,
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
                "user_id": (
                    user_context.replace(" | User: ", "") if user_context else None
                ),
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
            f"[{request_id}] {status_emoji} {request.method} {request.url.path} → {response.status_code} ({process_time:.3f}s){user_context}",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": process_time,
                "method": request.method,
                "path": request.url.path,
                "user_id": (
                    user_context.replace(" | User: ", "") if user_context else None
                ),
            },
        )

        # Special logging for 404 errors to help with debugging
        if response.status_code == 404:
            logger.error(
                f"[{request_id}] 🔍 404 DEBUG - Endpoint not found: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
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
