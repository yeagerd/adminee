"""
Logging configuration for User Management Service.

Sets up structured logging using structlog for better observability.
"""

import logging
import sys
from typing import Any, Callable, Dict, List

import structlog

from services.user.settings import get_settings


def configure_logging() -> None:
    """Configure structured logging with structlog."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, get_settings().log_level.upper()),
    )

    # Configure structlog processors
    processors: List[Callable[..., Any]] = [
        # Add timestamp
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add appropriate renderer based on format setting
    if get_settings().log_format.lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def setup_logging() -> None:
    """Setup logging configuration (alias for configure_logging)."""
    configure_logging()


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a configured structlog logger."""
    return structlog.get_logger(name)


def log_audit_event(
    logger: structlog.BoundLogger,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: Dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Log an audit event with structured data.

    Args:
        logger: Structlog logger instance
        user_id: ID of the user performing the action
        action: Action being performed
        resource_type: Type of resource being acted upon
        resource_id: ID of the specific resource (optional)
        details: Additional details about the action (optional)
        ip_address: IP address of the request (optional)
        user_agent: User agent of the request (optional)
    """
    logger.info(
        "audit_event",
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
