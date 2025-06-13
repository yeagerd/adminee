# Common Services Package

This package contains shared utilities and configurations used across all Briefly services.

## Modules

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
    get_clerk_secret_key,
    get_redis_url,
    get_openai_api_key
)

# Database URL for a specific service
user_db = get_database_url('user_management')  # Gets DB_URL_USER_MANAGEMENT
chat_db = get_database_url('chat_service')     # Gets DB_URL_CHAT_SERVICE

# Authentication secrets
clerk_key = get_clerk_secret_key()
clerk_publishable = get_clerk_publishable_key()

# External service APIs
openai_key = get_openai_api_key()
redis_url = get_redis_url()
```

**Direct import from module:**
```python
from services.common.secrets import get_secret, clear_cache

# For testing - clear the secret cache
clear_cache()
```

#### Environment Setup

**Local Development:**
Set environment variables in your `.env` file or shell:
```bash
export CLERK_SECRET_KEY="sk_test_..."
export DB_URL_USER_MANAGEMENT="postgresql://..."
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
setup_telemetry("user-management-service")

# Get tracer for your service
tracer = get_tracer("user-management")
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
```

## Installation

This package is automatically available when running services in the Briefly monorepo structure. No separate installation required. 