# Briefly API v1 Package

This package contains shared API schemas for inter-service communication in the Briefly platform. It provides a clean separation between internal service models and external API contracts.

## Structure

```
services/api/v1/
├── __init__.py
├── pyproject.toml
├── README.md
├── common/           # Common schemas used across all services
│   ├── models/      # Base models and common data structures
│   ├── events/      # Event schemas for inter-service communication
│   └── pagination/  # Pagination schemas
├── user/            # User service API schemas
├── office/          # Office service API schemas
├── meetings/        # Meetings service API schemas
├── chat/            # Chat service API schemas
├── shipments/       # Shipments service API schemas
├── email_sync/      # Email sync service API schemas
└── vespa/           # Vespa services API schemas
```

## Usage

### For Service Development

Instead of importing schemas directly from other services:

```python
# ❌ Don't do this
from services.user.schemas import UserProfile
from services.office.schemas import CalendarEvent

# ✅ Do this instead
from services.api.v1.user import UserProfile
from services.api.v1.office import CalendarEvent
```

### For Inter-Service Communication

Use the shared schemas for HTTP requests/responses and event data:

```python
from services.api.v1.user import UserProfile
from services.api.v1.common.events import UserCreatedEvent

# Validate incoming data
user_data = UserProfile.model_validate(request.json)

# Create events with proper schemas
event = UserCreatedEvent(user_id=user.id, profile=user_data)
```

## Benefits

1. **Clean Dependencies**: Services only depend on the API package, not each other
2. **Version Control**: All API schemas are versioned together
3. **Type Safety**: Shared schemas ensure consistent data structures
4. **Documentation**: Single source of truth for API contracts
5. **Testing**: Easier to mock and test inter-service communication

## Development

### Adding New Schemas

1. Create the schema in the appropriate service directory under `services/api/v1/`
2. Update the service's `__init__.py` to export the new schemas
3. Update any services that need to use the new schemas
4. Run tests to ensure compatibility

### Updating Existing Schemas

1. Make changes in the API package
2. Update all services that use the schema
3. Run full test suite to catch any breaking changes
4. Update documentation if needed

## Testing

The API package includes its own test suite to ensure schema validity and compatibility. Run tests with:

```bash
cd services/api/v1
uv run pytest
```

## Migration Guide

When migrating existing services:

1. Move schemas from `services/{service}/schemas/` to `services/api/v1/{service}/`
2. Update imports in the service to use `services.api.v1.{service}`
3. Update any other services that import from the migrated service
4. Run tests to ensure no regressions
5. Remove old schema directories
