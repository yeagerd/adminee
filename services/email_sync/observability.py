import logging

def record_metric(name: str, value: float, tags: dict = None):
    # Stub for metrics collection
    logging.info(f"METRIC {name} value={value} tags={tags}")

# Stub for distributed tracing
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    span_processor = BatchSpanProcessor(ConsoleSpanExporter())
    trace.get_tracer_provider().add_span_processor(span_processor)
except ImportError:
    tracer = None

def trace_function(name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if tracer:
                with tracer.start_as_current_span(name):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Example usage:
# @trace_function("process_email")
# def process_email(...): ... 