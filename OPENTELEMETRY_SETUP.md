# OpenTelemetry Setup and Merge Conflict Resolution

This document describes the changes made to resolve merge conflicts and set up OpenTelemetry instrumentation across all services.

## Summary of Changes

### 1. Merge Conflicts Resolved

**Files affected:**
- `Dockerfile.chat-service`
- `Dockerfile.office-service`

**Resolution:**
- Combined OpenTelemetry instrumentation with the uvicorn command
- Changed from separate `ENTRYPOINT` and `CMD` to a single `CMD` with `opentelemetry-instrument`

**Before:**
```dockerfile
ENTRYPOINT ["opentelemetry-instrument"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**After:**
```dockerfile
CMD ["opentelemetry-instrument", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. OpenTelemetry Dependencies Added

**Dependencies added to all service requirements.txt files:**
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-instrumentation`
- `opentelemetry-instrumentation-fastapi`
- `opentelemetry-instrumentation-httpx`
- `opentelemetry-distro`
- `opentelemetry-exporter-gcp-trace`

**Files updated:**
- `services/chat_service/requirements.txt`
- `services/office_service/requirements.txt` (already had them)
- `services/user_management/requirements.txt`

### 3. Docker Configuration Updated

**All Dockerfiles now include OpenTelemetry instrumentation:**

- `Dockerfile.chat-service`
- `Dockerfile.office-service` 
- `Dockerfile.user-service`

Each service is now launched with `opentelemetry-instrument` which automatically instruments FastAPI and HTTP client calls.

### 4. Shared Telemetry Module Created

**New files:**
- `services/common/telemetry.py` - Shared OpenTelemetry configuration
- `services/common/__init__.py` - Module initialization

**Features:**
- Centralized telemetry setup
- Service-specific resource configuration
- Google Cloud Trace exporter for production
- Utility functions for tracing
- Exception recording

## Usage

### Automatic Instrumentation

OpenTelemetry is automatically set up when services are launched with `opentelemetry-instrument`. This provides:

- **FastAPI instrumentation**: Automatic span creation for HTTP requests
- **HTTPX instrumentation**: Automatic tracing of outbound HTTP calls
- **Resource detection**: Service name, version, and environment metadata

### Manual Instrumentation (Optional)

For additional custom tracing, use the shared telemetry module:

```python
from services.common import setup_telemetry, get_tracer, add_span_attributes

# Set up telemetry (optional - already done by opentelemetry-instrument)
setup_telemetry("user-management", "1.0.0")

# Get a tracer for custom spans
tracer = get_tracer(__name__)

# Create custom spans
with tracer.start_as_current_span("custom_operation") as span:
    add_span_attributes(user_id="123", operation="data_processing")
    # Your code here
```

## Environment Variables

### Production Configuration

For production environments with Google Cloud Trace:

```bash
ENVIRONMENT=production
GOOGLE_CLOUD_PROJECT_ID=your-project-id
```

### Development Configuration

For development, OpenTelemetry runs with basic configuration:

```bash
ENVIRONMENT=development
```

## Verification

### 1. Docker Builds

All services should build successfully:

```bash
docker build -f Dockerfile.user-service -t user-service .
docker build -f Dockerfile.chat-service -t chat-service .
docker build -f Dockerfile.office-service -t office-service .
```

### 2. Tox Tests

All tox environments should pass:

```bash
tox -e format  # Code formatting check
tox -e lint    # Linting check
tox -e typecheck  # Type checking
tox -e test    # Unit tests
```

### 3. Docker Compose

The complete system should start:

```bash
docker-compose up
```

### 4. Service Health Checks

Each service exposes health endpoints:

- User Management: http://localhost:8001/health
- Chat Service: http://localhost:8002/health  
- Office Service: http://localhost:8080/health

## Telemetry Features

### Automatic Spans

- HTTP request/response spans for all FastAPI endpoints
- Outbound HTTP call spans for service-to-service communication
- Database query spans (when using instrumented drivers)

### Custom Attributes

Services automatically include:
- `service.name` - Service identifier
- `service.version` - Service version
- `host.name` - Container/host name
- `deployment.environment` - Environment (dev/prod)

### Error Tracking

- Automatic exception recording in spans
- HTTP error status tracking
- Custom exception handling with telemetry

## Benefits

1. **Distributed Tracing**: Track requests across multiple services
2. **Performance Monitoring**: Identify slow operations and bottlenecks
3. **Error Tracking**: Automatic error collection and correlation
4. **Service Dependencies**: Visualize service interaction patterns
5. **Production Ready**: Google Cloud Trace integration for production

## Next Steps

1. **Add custom business logic spans** in critical code paths
2. **Set up alerting** based on trace data
3. **Configure sampling** for high-traffic environments
4. **Add custom metrics** using OpenTelemetry metrics API
5. **Set up trace visualization** dashboards 