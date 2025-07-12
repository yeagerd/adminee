"""
OpenTelemetry configuration for Briefly services.

This module provides shared OpenTelemetry setup that can be used across all services.
"""

import os
import socket

from opentelemetry import trace  # type: ignore[import-unresolved]

try:
    from opentelemetry.exporter.gcp.trace import CloudTraceSpanExporter  # type: ignore
except ImportError:
    CloudTraceSpanExporter = None
from opentelemetry.instrumentation.fastapi import (
    FastAPIInstrumentor,  # type: ignore[import-unresolved]
)
from opentelemetry.instrumentation.httpx import (
    HTTPXClientInstrumentor,  # type: ignore[import-unresolved]
)
from opentelemetry.sdk.resources import Resource  # type: ignore[import-unresolved]
from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-unresolved]
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,  # type: ignore[import-unresolved]
)


def setup_telemetry(service_name: str, service_version: str = "1.0.0") -> None:
    """
    Set up OpenTelemetry for a service.

    Args:
        service_name: Name of the service (e.g., "user-management", "chat-service")
        service_version: Version of the service
    """
    # Only set up telemetry if not already configured
    if trace.get_tracer_provider() != trace.NoOpTracerProvider():
        return

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "host.name": socket.gethostname(),
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        }
    )

    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()

    # Set up exporters based on environment
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")

    if project_id and os.getenv("ENVIRONMENT") == "production":
        # Use Google Cloud Trace in production
        if CloudTraceSpanExporter:
            cloud_trace_exporter = CloudTraceSpanExporter(project_id=project_id)
            tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))  # type: ignore[attr-defined]
    else:
        # In development, you could add console exporter or other exporters
        # For now, we'll just set up the basics
        pass

    # Auto-instrument FastAPI and HTTPX
    FastAPIInstrumentor.instrument()  # type: ignore[attr-defined]
    HTTPXClientInstrumentor.instrument()  # type: ignore[attr-defined]


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer for the given name.

    Args:
        name: Name of the tracer (typically __name__ of the module)

    Returns:
        OpenTelemetry tracer instance
    """
    return trace.get_tracer(name)


def add_span_attributes(**attributes) -> None:
    """
    Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add as span attributes
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(exception: Exception, escaped: bool = False) -> None:
    """
    Record an exception in the current span.

    Args:
        exception: The exception to record
        escaped: Whether the exception escaped the span
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.record_exception(exception, escaped=escaped)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
