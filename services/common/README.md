# Common Services Package

This package contains shared utilities and configurations used across all Briefly services.

## Modules

### `logging_config.py` - Centralized Logging System

Provides consistent, structured logging across all Briefly services with features like:
- Structured JSON logging for easy parsing and analysis
- Request ID tracking for tracing requests across services
- User context extraction from HTTP requests
- Service identification in all log entries
- Performance timing for HTTP requests
- Error context with detailed debugging information

#### Quick Start

```python
from services.common.logging_config import setup_service_logging, get_logger

# Set up logging for your service
setup_service_logging(
    service_name="your-service-name",
    log_level="INFO",
    log_format="json"
)

# Get a structured logger
logger = get_logger(__name__)

# Log structured messages
logger.info("User action performed", 
            user_id="user123", 
            action="create_document")
```

#### FastAPI Integration

```python
from services.common.logging_config import create_request_logging_middleware

# Add request logging middleware
app.middleware("http")(create_request_logging_middleware())
```

For complete documentation, see [README_logging.md](./README_logging.md).

### `secrets.py` - Secret Management

Provides unified secret management for all services with support for:
- Local development (environment variables)
- Production (GCP Secret Manager with fallback to environment variables)

#### Usage Examples

**Basic secret retrieval:**
```python
from services.common import get_secret

# Get any secret by name
api_key = get_secret('OPENAI_API_KEY')
```

**Service-specific helpers:**
```python
from services.common import (
    get_database_url,
    get_nextauth_secret_key,
    get_redis_url,
    get_openai_api_key
)

# Database URL for a specific service
user_db = get_database_url('user')  # Gets DB_URL_USER
chat_db = get_database_url('chat_service')     # Gets DB_URL_CHAT_SERVICE

# Authentication secrets
nextauth_key = get_nextauth_secret_key()
nextauth_publishable = get_nextauth_publishable_key()

# External service APIs
openai_key = get_openai_api_key()
redis_url = get_redis_url()
```

**Direct import from module:**
```python
from services.common.config_secrets import get_secret, clear_cache

# For testing - clear the secret cache
clear_cache()
```

#### Environment Setup

**Local Development:**
Set environment variables in your `.env` file or shell:
```bash
export CLERK_SECRET_KEY="sk_test_..."
export DB_URL_USER="postgresql://..."
export OPENAI_API_KEY="sk-..."
```

**Production (GCP):**
The module automatically detects the environment and uses:
1. GCP Secret Manager (primary)
2. Environment variables (fallback, e.g., from Cloud Run secret mounts)

### `telemetry.py` - OpenTelemetry Setup

Provides OpenTelemetry configuration for distributed tracing across services.

#### Usage
```python
from services.common import setup_telemetry, get_tracer

# Initialize telemetry for your service
setup_telemetry("user-service")

# Get tracer for your service
tracer = get_tracer("user")
```

## Dependencies

Each service using this common package should include these dependencies in their `requirements.txt`:

```txt
# For secret management
google-cloud-secret-manager

# For telemetry (already included in most services)
opentelemetry-api
opentelemetry-sdk
opentelemetry-instrumentation

# For centralized logging (automatically included)
structlog
fastapi
```

## Installation

This package is automatically available when running services in the Briefly monorepo structure. No separate installation required. 