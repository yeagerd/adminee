"""
Common utilities and configurations for Briefly services.
"""

from .telemetry import (
    add_span_attributes,
    get_tracer,
    record_exception,
    setup_telemetry,
)

__all__ = [
    "setup_telemetry",
    "get_tracer",
    "add_span_attributes",
    "record_exception",
]
