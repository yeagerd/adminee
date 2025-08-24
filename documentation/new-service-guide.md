# New Service Guide

This guide covers the essential steps and patterns for creating a new service in the Briefly platform.

## Prerequisites

- Service follows microservice architecture principles
- Service has a clear, single responsibility
- Service integrates with existing Briefly infrastructure

## 1. Service Structure

Create your service directory under `services/`:

```
services/your-service/
├── __init__.py
├── main.py              # FastAPI app entry point
├── pyproject.toml       # Service-specific dependencies
├── settings.py          # Configuration management
├── database.py          # Database connection setup
├── models/              # SQLModel/SQLAlchemy models
├── schemas/             # Pydantic schemas
├── routers/             # API route definitions
├── services/            # Business logic
└── tests/               # Test files
```

## 2. Essential Dependencies

Add to your service's `pyproject.toml`:

```toml
[project]
name = "briefly-your-service"
version = "0.1.0"
description = "Briefly Your Service - Description of what your service does"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.104.0,<1.0.0",
    "uvicorn[standard]>=0.24.0,<1.0.0",
    "sqlmodel>=0.0.8,<1.0.0",
    "sqlalchemy>=2.0.0,<3.0.0",
    "psycopg2-binary>=2.9.0,<3.0.0",
    "structlog>=23.0.0,<24.0.0",
    "opentelemetry-api>=1.20.0,<2.0.0",
    "opentelemetry-sdk>=1.20.0,<2.0.0",
    "opentelemetry-instrumentation>=0.42b0,<1.0.0",
    "google-cloud-secret-manager>=2.16.0,<3.0.0",
    # Note: Use services.common.settings instead of pydantic-settings
]

[project.optional-dependencies]
test = [
    "pytest>=7.4.0,<8.0.0",
    "pytest-asyncio>=0.21.0,<1.0.0",
    "httpx>=0.25.0,<1.0.0",
]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["*"]


### Dependency Management with UV

This project uses [UV](https://github.com/astral-sh/uv) for Python package management. UV provides 10-100x faster dependency resolution and better caching than traditional tools like pip or poetry.

**Install dependencies:**
```bash
# Install all project dependencies including dev dependencies
uv sync --all-packages --all-extras --active

# Install specific service in development mode
uv pip install -e services/your-service

# Install with development dependencies
uv pip install -e ".[test]"
```

**Add new dependencies:**
```bash
# Add to root project
uv add fastapi

# Add to specific service
uv add sqlalchemy --project services/your-service

# Add development dependency
uv add pytest --dev
```

**Update dependencies:**
```bash
uv lock --upgrade
uv sync --all-packages --all-extras --active
```

**Run services with UV:**
```bash
# Start individual service
uv run python -m uvicorn services.your_service.main:app --port 8006 --reload

# Run tests
uv run python -m pytest services/your-service/tests/ -v
```

## 3. Common Service Integration

### Logging Configuration

Use centralized logging from `services/common/logging_config.py`:

```python
from services.common.logging_config import (
    setup_service_logging,
    setup_service_logging,
    create_request_logging_middleware,
    log_service_startup,
    log_service_shutdown
)

# In your main.py lifespan
setup_service_logging(
    service_name="your-service",
    log_level=settings.log_level,
    log_format=settings.log_format,
)

# Add request logging middleware
app.middleware("http")(create_request_logging_middleware())

# Log lifecycle events
log_service_startup("your-service", version="1.0.0")
log_service_shutdown("your-service")
```

### HTTP Error Handling

Use standardized error handling from `services/common/http_errors.py`:

```python
from services.common.http_errors import (
    register_briefly_exception_handlers,
    ValidationError,
    NotFoundError,
    AuthError,
    ServiceError
)

# Register exception handlers
register_briefly_exception_handlers(app)

# Use standard error classes
if not resource_exists:
    raise NotFoundError("Resource", resource_id)
```

### Distributed Tracing

Use OpenTelemetry from `services/common/telemetry.py`:

```python
from services.common.telemetry import setup_telemetry, get_tracer

# Initialize telemetry
setup_telemetry("your-service", "1.0.0")

# Get tracer for spans
tracer = get_tracer(__name__)
```

### Secret Management

Use centralized secret management from `services/common/config_secrets.py`:

```python
from services.common.config_secrets import (
    get_secret,
    get_database_url,
    get_redis_url
)

# Get secrets
api_key = get_secret('YOUR_API_KEY')
db_url = get_database_url('your_service')
redis_url = get_redis_url()
```

## 4. Configuration Management

**Important**: This project provides centralized configuration management through `services.common.settings`. Use this instead of importing `pydantic-settings` directly.

### Environment Variables

Add to `.example.env`:

```bash
# Database
DB_URL_YOUR_SERVICE=postgresql://briefly_your_service:$TODO@localhost:5432/briefly_your_service

# Service URLs
YOUR_SERVICE_URL=http://127.0.0.1:8006

# API Keys
API_FRONTEND_YOUR_SERVICE_KEY=$TODO
API_YOUR_SERVICE_USER_KEY=$TODO
API_YOUR_SERVICE_OFFICE_KEY=$TODO
```

### Settings Class

Create `settings.py` following the pattern from existing services:

```python
from services.common.settings import BaseSettings, Field, SettingsConfigDict
from services.common.config_secrets import get_secret

class Settings(BaseSettings):
    service_name: str = "your-service"
    environment: str = "local"
    debug: bool = False
    
    # Database
    db_url_your_service: str = get_secret("DB_URL_YOUR_SERVICE")
    
    # API Keys
    api_frontend_your_service_key: str = get_secret("API_FRONTEND_YOUR_SERVICE_KEY")
    api_your_service_user_key: str = get_secret("API_YOUR_SERVICE_USER_KEY")
    
    # Service URLs
    user_service_url: str = get_secret("USER_SERVICE_URL")
    office_service_url: str = get_secret("OFFICE_SERVICE_URL")
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )
```

## 5. Database Setup

### Connection Management

Follow the pattern from existing services:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from services.common.config_secrets import get_database_url

# Get database URL
database_url = get_database_url("your_service")

# Create engine
engine = create_async_engine(database_url, echo=False)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Models

Use SQLModel for type-safe database models:

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class YourModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

## 6. API Routes

### Router Structure

Organize routes by domain:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from services.common.http_errors import NotFoundError

router = APIRouter()

@router.get("/{item_id}")
async def get_item(
    item_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    # Your business logic here
    pass
```

### Health Check Endpoint

Include a health check endpoint:

```python
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "your-service"}
```

## 7. Service Registration

### Add to Start Script

Add your service to `scripts/start-all-services.sh`:

```bash
# Start Your Service
start_python_service "your-service" "services.your_service.main:app" 8006

# Add to port checks
check_port 8006 "Your Service" || exit 1

# Add to wait for service
wait_for_service "Your Service" "http://localhost:8006/health" &
```

### Database Setup Scripts

Add to `scripts/postgres-start.sh`:

```bash
# Add your service database
docker exec briefly-postgres psql -U postgres -c "CREATE DATABASE briefly_your_service;"
docker exec briefly-postgres psql -U postgres -c "CREATE USER briefly_your_service WITH PASSWORD 'your_password';"
docker exec briefly-postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE briefly_your_service TO briefly_your_service;"
```

Add to `scripts/check-db-status.sh` and `scripts/run-migrations.sh`:

```bash
# Add your service variables
export DB_URL_YOUR_SERVICE=postgresql://briefly_your_service:${BRIEFLY_YOUR_SERVICE_PASSWORD:-briefly_your_service_pass}@localhost:5432/briefly_your_service
export DB_URL_YOUR_SERVICE_MIGRATIONS=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@localhost:5432/briefly_your_service
```

### Docker Configuration

Create `Dockerfile.your-service`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv first
RUN pip install uv

# Copy dependency files first for better layer caching
COPY services/your_service/pyproject.toml .

# Install only the dependencies (not the service itself yet)
RUN uv pip install --only-deps .

# Copy source code
COPY services/your_service/ .

# Now install the service in editable mode (source code is available)
RUN uv pip install -e .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006"]
```

## 8. Testing

### Test Structure

Follow existing test patterns:

```python
import pytest
from fastapi.testclient import TestClient
from services.your_service.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "your-service"
```

### Running Tests

```bash
# Run all tests
nox -s test

# Run specific test environments
nox -s lint        # Linting
nox -s typecheck   # Type checking
nox -s test        # Unit tests

# Run service-specific tests
uv run python -m pytest services/your-service/tests/ -v

# Find slow tests
python -m pytest --durations=10 -q -n auto
```

### Test Dependencies

Add to your service's `pyproject.toml`:

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.4.0,<8.0.0",
    "pytest-asyncio>=0.21.0,<1.0.0",
    "httpx>=0.25.0,<1.0.0",
]
```

## 9. Authentication and Authorization

### **Key Principle: "What You Can Do" vs "Who You Are"**

**❌ DON'T**: Use caller-based authentication (e.g., `require_frontend_auth`, `require_user_service_auth`)
**✅ DO**: Use permission-based authentication with granular permissions (e.g., `read_users`, `write_users`)

**Why**: Caller-based auth is about **who** is calling, but should be about **what** they can do. This creates security vulnerabilities and makes permission management difficult.

### **Using Common Authentication Helpers**

**ALWAYS** use the common authentication modules instead of duplicating code:

```python
# ✅ CORRECT: Use common api_key_auth
from services.common.api_key_auth import (
    APIKeyConfig,
    make_service_permission_required,
    make_verify_service_authentication,
)

# ✅ CORRECT: Use common jwt_auth
from services.common.jwt_auth import (
    make_get_current_user,
    make_verify_jwt_token,
)
```

### **API Key Authentication (Service-to-Service)**

Use the common `api_key_auth.py` helper for permission-based authentication:

```python
# In your service's auth.py
from services.common.api_key_auth import (
    APIKeyConfig,
    make_service_permission_required,
    make_verify_service_authentication,
)
from your_service.settings import get_settings

# Define permissions, not callers
API_KEY_CONFIGS: Dict[str, APIKeyConfig] = {
    "api_frontend_your_service_key": APIKeyConfig(
        client="frontend",
        service="your-service-access",
        permissions=[
            "read_items",      # What they can do
            "write_items",     # What they can do
            "delete_items",    # What they can do
        ],
        settings_key="api_frontend_your_service_key",
    ),
    "api_chat_your_service_key": APIKeyConfig(
        client="chat-service",
        service="your-service-access",
        permissions=[
            "read_items",      # Read-only access
        ],
        settings_key="api_chat_your_service_key",
    ),
}

# Service-level permissions fallback
SERVICE_PERMISSIONS = {
    "your-service-access": [
        "read_items",
        "write_items", 
        "delete_items",
    ],
}

# Create FastAPI dependencies
verify_service_authentication = make_verify_service_authentication(
    API_KEY_CONFIGS, get_settings
)

def service_permission_required(
    required_permissions: List[str],
) -> Callable[[Request], Any]:
    return make_service_permission_required(
        required_permissions,
        API_KEY_CONFIGS,
        get_settings,
        SERVICE_PERMISSIONS,
    )
```

**Usage in endpoints**:
```python
@router.get("/items")
async def list_items(
    authenticated_service: str = Depends(service_permission_required(["read_items"]))
):
    # Only services with read_items permission can access
    pass

@router.post("/items")
async def create_item(
    authenticated_service: str = Depends(service_permission_required(["write_items"]))
):
    # Only services with write_items permission can access
    pass
```

### **JWT Authentication (User Operations)**

Use the common `jwt_auth.py` helper for user authentication:

```python
# In your service's auth.py
from services.common.jwt_auth import (
    make_get_current_user,
    make_get_current_user_with_claims,
)
from your_service.settings import get_settings

# Create JWT authentication functions using your service's settings
get_current_user = make_get_current_user(get_settings)
get_current_user_with_claims = make_get_current_user_with_claims(get_settings)
```

**Usage in endpoints**:
```python
@router.get("/me/items")
async def list_my_items(
    current_user_id: str = Depends(get_current_user)
):
    # User is authenticated via JWT, user_id comes from token
    pass

@router.post("/me/items")
async def create_my_item(
    item: ItemCreate,
    current_user_id: str = Depends(get_current_user)
):
    # User is authenticated via JWT
    pass
```

### **Dual Authentication Pattern**

For public endpoints that need both user identity AND service permissions:

```python
@router.get("/me/items")
async def list_my_items(
    authenticated_service: str = Depends(service_permission_required(["read_items"])),
    current_user_id: str = Depends(get_current_user),
):
    # 1. API key validates service permissions
    # 2. JWT validates user identity
    # 3. User can only access their own data
    pass
```

### **Internal vs Public Endpoints**

**Public Endpoints** (`/v1/*`):
- Require JWT authentication for user identity
- Require API key authentication for service permissions
- Use `/me/` pattern (no user_id in path/query)
- User data comes from JWT token

**Internal Endpoints** (`/internal/*`):
- Require API key authentication only
- Accept `user_id` parameter for service-to-service calls
- Used for background jobs and service integration

```python
# Public endpoint - user gets their own data
@router.get("/v1/me/items")
async def list_my_items(
    authenticated_service: str = Depends(service_permission_required(["read_items"])),
    current_user_id: str = Depends(get_current_user),
):
    return await get_items_for_user(current_user_id)

# Internal endpoint - service can get any user's data
@router.get("/internal/items")
async def list_user_items(
    user_id: str = Query(...),
    authenticated_service: str = Depends(service_permission_required(["read_items"])),
):
    return await get_items_for_user(user_id)
```

### **Settings Configuration**

Add JWT settings to your service's `settings.py`:

```python
# JWT Configuration
jwt_verify_signature: bool = Field(
    default=True, description="Whether to verify JWT signatures"
)
nextauth_issuer: str = Field(
    default="nextauth", description="NextAuth JWT issuer"
)
nextauth_audience: Optional[str] = Field(
    default=None, description="NextAuth JWT audience"
)
nextauth_jwt_key: Optional[str] = Field(
    default=None, description="NextAuth JWT secret key"
)
```

### **Permission Design Guidelines**

1. **Use descriptive permission names**: `read_users`, `write_users`, `delete_users`
2. **Group related permissions**: `user_management` could include all user operations
3. **Follow least privilege**: Chat service only needs `read_users`, not `write_users`
4. **Be specific**: `read_user_preferences` is better than just `read_users`

### **Migration from Caller-Based Auth**

If you have existing caller-based authentication:

```python
# ❌ OLD: Caller-based
async def require_frontend_auth(request: Request) -> str:
    # ... validation logic

# ✅ NEW: Permission-based
def service_permission_required(required_permissions: List[str]):
    return make_service_permission_required(
        required_permissions,
        API_KEY_CONFIGS,
        get_settings,
        SERVICE_PERMISSIONS,
    )

# Usage
@router.get("/items")
async def list_items(
    authenticated_service: str = Depends(service_permission_required(["read_items"]))
):
    pass
```

### **Testing Authentication**

Test both API key and JWT authentication:

```python
def test_api_key_permissions():
    # Test different API keys have correct permissions
    pass

def test_jwt_authentication():
    # Test JWT validation and user extraction
    pass

def test_user_isolation():
    # Test users can only access their own data
    pass
```

## 11. OpenAPI Schema and Type Generation

### **Overview**

When you create or modify API endpoints, you need to regenerate the OpenAPI schemas and TypeScript types to keep the frontend in sync with your backend changes.

### **OpenAPI Schema Generation**

Generate OpenAPI schemas for your service:

```bash
# Generate schemas for all services
./scripts/generate-openapi-schemas.sh

# Generate schema for specific service only
./scripts/generate-openapi-schemas.sh your-service-name
```

**What this does:**
- Runs your FastAPI app to generate OpenAPI schema
- Saves schema to `services/your-service/openapi/schema.json`
- Copies schema to `openapi-schemas/your-service-openapi.json`

### **TypeScript Type Generation**

Generate TypeScript types from OpenAPI schemas:

```bash
cd frontend
./scripts/generate-types.sh
```

**What this does:**
- Creates TypeScript types for all services
- Generates client classes for API calls
- Updates `frontend/types/api/index.ts`

### **Complete Workflow Script**

Use the unified script for the entire process:

```bash
./scripts/update-types.sh
```

This script:
1. Generates OpenAPI schemas for all services
2. Copies schemas to frontend directory
3. Generates TypeScript types
4. Runs type validation

### **Verification**

After generating types, verify they're valid:

```bash
cd frontend
npm run typecheck
```

### **When to Regenerate**

**Always regenerate after:**
- Adding new API endpoints
- Modifying request/response models
- Changing authentication patterns
- Updating service dependencies
- Refactoring API structure

**Example workflow after API changes:**

```bash
# 1. Make your API changes
# 2. Test your service locally
# 3. Generate updated schema and types
./scripts/generate-openapi-schemas.sh
cd frontend && npm run generate-types

# 5. Verify types are valid
npm run typecheck

# 6. Commit changes
git add .
git commit -m "feat: add new API endpoint with updated types"
```

### **Generated File Structure**

```
frontend/types/api/
├── index.ts                    # Main export file
├── your-service/              # Your service types
│   ├── models/                # Request/response models
│   ├── services/              # API client classes
│   └── index.ts               # Service-specific exports
└── other-services/            # Other service types
```

### **Troubleshooting**

**Common issues and solutions:**

1. **Schema generation fails:**
   - Ensure your service starts without errors
   - Check that FastAPI app is properly configured
   - Verify all dependencies are installed

2. **Type conflicts:**
   - Check `frontend/types/api/index.ts` for duplicate exports
   - Use aliases for conflicting service names
   - Ensure unique model names across services

3. **Type validation fails:**
   - Run `npm run typecheck` to see specific errors
   - Check for missing or incorrect type definitions
   - Verify OpenAPI schema is valid JSON

### **Best Practices**

1. **Always regenerate after API changes** - Don't skip this step
2. **Test types before committing** - Run `npm run typecheck`
3. **Use descriptive model names** - Avoid generic names like "Item"
4. **Keep schemas up to date** - Regenerate when adding new endpoints
5. **Document breaking changes** - Update frontend developers about API changes
```

## 12. Service Discovery

### Gateway Integration

Your service will be accessible through the Express Gateway at `http://localhost:3001/your-service/*`.

### Service URLs

Configure service URLs in `.example.env` and use them for inter-service communication.

### Port Assignment

Use unique ports to avoid conflicts:
- Gateway: 3001
- User Service: 8001
- Chat Service: 8002
- Office Service: 8003
- Shipments Service: 8004
- Meetings Service: 8005
- **Your Service: 8006** (or next available)

## 13. Monitoring and Observability

### Logging Best Practices

- Use structured logging with context
- Include request IDs in all log entries
- Log performance metrics for critical operations
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)

### Tracing

- Use OpenTelemetry for distributed tracing
- Create spans for database operations
- Track external API calls
- Include correlation IDs in logs

## 12. Deployment Considerations

### Environment Variables

- Use GCP Secret Manager in production
- Fall back to environment variables
- Never commit secrets to version control

### Health Checks

- Implement `/health` endpoint
- Check database connectivity
- Verify external service dependencies
- Return appropriate HTTP status codes

### Graceful Shutdown

- Handle SIGTERM signals
- Close database connections
- Complete in-flight requests
- Log shutdown events

### Production Setup

**GCP Secret Manager (NOT YET IN USE):**
```bash
# Run setup script
./scripts/setup-gcp-secrets.sh

# Environment variables
ENVIRONMENT=production
GOOGLE_CLOUD_PROJECT_ID=your-project-id
```

**Docker Build (NOT RELEVANT YET):**
```bash
# Build service image
docker build -f Dockerfile.your-service -t briefly/your-service:latest .

# Push to registry
docker push briefly/your-service:latest
```

## Example Service Implementation

See these files for complete examples:

- `services/user/main.py` - User management service
- `services/chat/main.py` - Chat service  
- `services/office/app/main.py` - Office service
- `services/shipments/main.py` - Shipments service
- `services/meetings/main.py` - Meetings service

## Common Patterns

### Database Migrations

Use Alembic for database schema changes. **Important:** Always run migrations from the repository root, not from within service directories:

```bash
# Generate migration
alembic -c services/your-service/alembic.ini revision --autogenerate -m "Add new table"

# Apply migration
alembic -c services/your-service/alembic.ini upgrade head

# Check migration status
alembic -c services/your-service/alembic.ini current

# List all migrations
alembic -c services/your-service/alembic.ini history
```

**Note:** The database URLs in your `.env` file are configured to work from the root directory. Running Alembic from within service directories will fail.

### Database Management

**Start PostgreSQL:**
```bash
./scripts/postgres-start.sh --env-file env.postgres.local
```

**Check database status:**
```bash
./scripts/check-db-status.sh --env-file env.postgres.local
```

**Run all migrations:**
```bash
./scripts/run-migrations.sh --env-file env.postgres.local
```

**Stop PostgreSQL:**
```bash
./scripts/postgres-stop.sh
```

### Error Handling

Use standard error responses:

```python
from services.common.http_errors import ServiceError

try:
    # Your operation
    pass
except Exception as e:
    raise ServiceError(
        "Operation failed",
        details={"operation": "create_item", "error": str(e)}
    )
```

### Rate Limiting

Implement rate limiting for external APIs:

```python
from services.common.http_errors import RateLimitError

if rate_limit_exceeded:
    raise RateLimitError(
        "API rate limit exceeded",
        retry_after=3600
    )
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `services/common` is available
2. **Database connection**: Check database URL and credentials
3. **API key validation**: Verify API keys are set correctly
4. **Port conflicts**: Ensure unique port assignment

### Debug Mode

Enable debug logging:

```python
setup_service_logging(
    service_name="your-service",
    log_level="DEBUG",
    log_format="text"
)
```

## Quick Start Checklist

- [ ] Create `services/your-service/` directory
- [ ] Add to `scripts/start-all-services.sh`
- [ ] Add to `scripts/postgres-start.sh`
- [ ] Add to `scripts/check-db-status.sh`
- [ ] Add to `scripts/run-migrations.sh`
- [ ] Create `env.postgres.local` with service password
- [ ] Add environment variables to `.example.env`
- [ ] Create `Dockerfile.your-service`
- [ ] Test with `./scripts/start-all-services.sh`
