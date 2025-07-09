# Centralized Logging System

This document describes the centralized logging system for all Briefly services, implemented in `services/common/logging_config.py`.

## Overview

The centralized logging system provides consistent, structured logging across all Briefly services with the following features:

- **Structured JSON logging** for easy parsing and analysis
- **Request ID tracking** for tracing requests across services
- **User context extraction** from HTTP requests
- **Service identification** in all log entries
- **Performance timing** for HTTP requests
- **Error context** with detailed debugging information
- **Consistent format** across all services

## Quick Start

### Basic Setup

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
            action="create_document",
            document_id="doc_456")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from services.common.logging_config import (
    create_request_logging_middleware,
    setup_service_logging,
    log_service_startup,
    log_service_shutdown
)

# Set up logging
setup_service_logging(
    service_name="my-service",
    log_level="INFO",
    log_format="json"
)

app = FastAPI()

# Add request logging middleware
app.middleware("http")(create_request_logging_middleware())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log_service_startup("my-service", version="1.0.0")
    yield
    # Shutdown
    log_service_shutdown("my-service")

app = FastAPI(lifespan=lifespan)
```

## Features

### 1. Structured JSON Logging

All log entries are structured JSON objects with consistent fields:

```json
{
  "timestamp": "2025-06-20T05:50:59.204Z",
  "level": "INFO",
  "logger": "chat-service.core",
  "message": "User action performed",
  "service": "chat-service",
  "user_id": "demo_user",
  "action": "create_document",
  "document_id": "doc_123"
}
```

### 2. HTTP Request Logging

The middleware automatically logs all HTTP requests with:

- **Request tracking**: Unique request ID for each request
- **User context**: Extracted from request body, query params, or path
- **Performance timing**: Request processing time
- **Error details**: Enhanced 404 debugging information

Example log output:
```
[d76ae326] → POST /chat | User: demo_user
[d76ae326] ✅ POST /chat → 200 (0.145s) | User: demo_user
```

### 3. Service Identification

Every log entry includes the service name, making it easy to filter logs by service in production:

```json
{
  "service": "chat-service",
  "message": "Processing user request"
}
```

### 4. User Context Extraction

The system automatically extracts user context from:

- **Request body**: `{"user_id": "demo_user"}`
- **Query parameters**: `?user_id=demo_user`
- **Path parameters**: `/users/{user_id}/preferences`

### 5. Error Context

Enhanced error logging with debugging information:

```json
{
  "level": "ERROR",
  "message": "404 DEBUG - Endpoint not found: GET /nonexistent",
  "request_id": "036056c0",
  "requested_endpoint": "GET /nonexistent",
  "suggestion": "Check if the endpoint path and HTTP method are correct"
}
```

## API Reference

### `setup_service_logging()`

Sets up logging configuration for a service.

```python
setup_service_logging(
    service_name: str,           # Name of the service (e.g., "chat-service")
    log_level: str = "INFO",     # Logging level (DEBUG, INFO, WARNING, ERROR)
    log_format: str = "json",    # Format type ("json" or "text")
    enable_request_logging: bool = True  # Whether to enable HTTP request logging
)
```

### `get_logger()`

Get a structured logger instance.

```python
logger = get_logger(name: str)  # Usually __name__
```

### `create_request_logging_middleware()`

Create HTTP request logging middleware for FastAPI.

```python
middleware = create_request_logging_middleware()
app.middleware("http")(middleware)
```

### `log_service_startup()` / `log_service_shutdown()`

Log service lifecycle events with configuration details.

```python
log_service_startup("service-name", version="1.0.0", **kwargs)
log_service_shutdown("service-name")
```

## Configuration

### Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: General information about service operation
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures

### Log Formats

- `json`: Structured JSON format (recommended for production)
- `text`: Human-readable text format (good for development)

### Third-Party Logger Silencing

The system automatically reduces verbosity from common third-party libraries:

- `httpx` → WARNING level
- `httpcore` → WARNING level  
- `LiteLLM` → WARNING level
- `urllib3` → WARNING level

## Migration Guide

### From Custom Logging

If your service currently has custom logging setup:

1. **Remove custom logging configuration**:
```python
# Remove this
logging.basicConfig(...)
logging.getLogger("...").setLevel(...)
```

2. **Add centralized logging import**:
```python
from services.common.logging_config import setup_service_logging
```

3. **Replace logging setup**:
```python
# Replace custom setup with
setup_service_logging(
    service_name="your-service",
    log_level="INFO",
    log_format="json"
)
```

4. **Update middleware** (if using custom HTTP logging):
```python
# Replace custom middleware with
from services.common.logging_config import create_request_logging_middleware
app.middleware("http")(create_request_logging_middleware())
```

### From services/user/logging_config.py

The user service had its own logging configuration that has been replaced:

```python
# Old
from services.user.logging_config import setup_logging
setup_logging()

# New  
from services.common.logging_config import setup_service_logging
setup_service_logging(service_name="user-management-service")
```

## Best Practices

### 1. Use Structured Logging

Always include relevant context in your log messages:

```python
# Good
logger.info("User preferences updated", 
            user_id=user_id, 
            preferences=["timezone", "language"],
            duration_ms=45)

# Avoid
logger.info(f"Updated preferences for {user_id}")
```

### 2. Include Request Context

When logging within request handlers, include request-specific context:

```python
logger.info("Processing chat request",
            user_id=request.user_id,
            message_length=len(request.message),
            model="gpt-4")
```

### 3. Use Appropriate Log Levels

- **DEBUG**: Detailed debugging information, request/response bodies
- **INFO**: Normal operation events, user actions, service state changes
- **WARNING**: Potential issues, rate limiting, deprecated features
- **ERROR**: Actual errors, exceptions, failed operations

### 4. Include Performance Metrics

Log timing information for important operations:

```python
start_time = time.time()
# ... do work ...
duration = time.time() - start_time

logger.info("Database query completed",
            query_type="user_preferences",
            duration_ms=int(duration * 1000),
            rows_returned=len(results))
```

## Production Considerations

### Log Aggregation

The JSON format is designed to work well with log aggregation tools like:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Fluentd**
- **Google Cloud Logging**
- **AWS CloudWatch**

### Performance

- Structured logging has minimal performance overhead
- Request middleware adds ~1-2ms per request
- JSON serialization is optimized for common use cases

### Storage

- JSON logs are larger than plain text but provide much more value
- Consider log rotation and retention policies
- Use log level filtering to reduce volume in production

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `services/common` is installed: `pip install -e services/common`

2. **Duplicate logs**: Make sure you're not calling `setup_service_logging()` multiple times

3. **Missing user context**: Check that your request format matches the expected patterns for user extraction

4. **Performance issues**: Consider reducing log level or disabling request body logging for high-traffic endpoints

### Debug Mode

Enable debug logging to see detailed information:

```python
setup_service_logging(
    service_name="my-service",
    log_level="DEBUG",
    log_format="text"  # More readable for debugging
)
```

## Examples

See the implementation in:

- `services/chat/main.py` - Chat service integration
- `services/user/main.py` - User management service integration  
- `services/office/app/main.py` - Office service integration

Each service demonstrates the complete integration pattern with startup/shutdown logging and request middleware. 