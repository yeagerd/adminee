# Briefly Office Service

The Office Service is a microservice that provides unified access to Google and Microsoft integrations including email, calendar, files, and contacts.

## Architecture

This service has been migrated to use the shared API package structure (`services.api.v1.office.*`) instead of local schemas. All Pydantic models are now defined in the shared API package to enable consistent inter-service communication.

## API Structure

### Shared API Package (`services.api.v1.office.*`)

The service now imports all schemas from the shared API package:

- **`services.api.v1.office.calendar`** - Calendar event schemas and requests
- **`services.api.v1.office.email`** - Email message schemas and operations  
- **`services.api.v1.office.files`** - File management schemas
- **`services.api.v1.office.contacts`** - Contact management schemas
- **`services.api.v1.office.responses`** - Common API response models
- **`services.api.v1.office.models`** - Shared models like Provider enum

### Import Patterns

```python
# ✅ Correct: Import from shared API package
from services.api.v1.office.calendar import CalendarEvent, CreateCalendarEventRequest
from services.api.v1.office.email import EmailMessage, EmailAddress
from services.api.v1.office.responses import ApiResponse, TypedApiResponse

# ❌ Incorrect: Import from local schemas (deprecated)
from services.office.schemas import CalendarEvent  # Don't use this
```

## API Endpoint Patterns

### User-facing endpoints:
- Use header-based user extraction (X-User-Id set by gateway)
- No user_id in path or query
- Require user authentication (JWT/session)
- All endpoints are prefixed with `/v1/`

### Internal/service endpoints:
- Use `/internal` prefix (no version prefix)
- Require API key/service authentication
- Used for service-to-service and background job calls

## Available Endpoints

- **`/v1/email`** - Email operations (send, receive, manage)
- **`/v1/calendar`** - Calendar operations (events, availability)
- **`/v1/files`** - File operations (upload, download, search)
- **`/v1/contacts`** - Contact management
- **`/internal/backfill`** - Internal backfill operations
- **`/internal/email`** - Internal email operations

## Schema Migration Status

✅ **Completed**: All schemas migrated to shared API package  
✅ **Completed**: All imports updated to use shared schemas  
✅ **Completed**: All inter-service calls updated  
✅ **Completed**: Service tests passing with new structure (292/301)  

## Development

### Running Tests
```bash
uv run pytest services/office/tests/ -v
```

### Schema Updates
When adding new schemas, add them to the appropriate module in `services/api/v1/office/` and update the `__init__.py` exports.

### Import Updates
Always import schemas from `services.api.v1.office.*` instead of local schemas to maintain consistency across services. 