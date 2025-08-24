# Move Contact Discovery/Management/API to New Contacts Service

## Overview
Move the contact discovery, management, and API functionality from the User Service to a new dedicated Contacts Service. This will improve service separation, reduce User Service complexity, and provide a focused service for contact-related operations.

## Current State Analysis

### Contact Functionality in User Service
- **Contact Discovery Service**: `services/user/services/contact_discovery_service.py`
  - Processes events from email, calendar, document, and todo sources
  - Discovers contacts from various event types
  - Maintains in-memory contact cache
  - Publishes contact events to PubSub for Vespa integration
  
- **Contact Discovery Consumer**: `services/user/services/contact_discovery_consumer.py`
  - Subscribes to multiple PubSub topics (emails, calendars, contacts, documents, todos)
  - Processes events for contact discovery
  - Integrates with ContactDiscoveryService
  
- **Contact Models**: `services/common/models/email_contact.py`
  - `EmailContact` - Core contact data model with event tracking
  - `EmailContactUpdate` - Update model for contacts
  - `EmailContactSearchResult` - Search result wrapper
  - `EmailContactEventCount` - Event type counters
  
- **Contact Tests**: `services/user/tests/test_contact_discovery_service.py`
  - Comprehensive test coverage for contact discovery functionality

### Current Integration Points
- **PubSub Topics**: Subscribes to emails, calendars, contacts, documents, todos
- **Event Processing**: Processes `EmailEvent`, `CalendarEvent`, `DocumentEvent`, `TodoEvent`
- **Vespa Integration**: Publishes `ContactEvent` for Vespa indexing
- **Frontend Usage**: Office Service provides contact management via `/contacts` endpoints
- **No Direct API**: User Service doesn't expose contact endpoints directly

### Dependencies and References
- **Common Models**: Uses `services/common/models/email_contact.py`
- **Common Events**: Uses `services/common/events/` for event processing
- **Common PubSub**: Uses `services/common/pubsub_client.py`
- **Frontend Types**: `frontend/types/api/office/models/Contact*` for Office Service integration

## Target State
- **New Contacts Service**: Dedicated service for all contact operations
- **Contact API Endpoints**: RESTful API for contact CRUD operations
- **Contact Discovery**: Event-driven contact discovery from various sources
- **Contact Management**: Full contact lifecycle management
- **Database Storage**: Persistent contact storage with SQLModel/SQLAlchemy
- **Service Integration**: Clean integration with other services via API keys

## Migration Strategy

### Phase 1: Create New Contacts Service Structure
- [x] Create `services/contacts/` directory structure
- [x] Create `services/contacts/pyproject.toml` with dependencies
- [x] Create `services/contacts/main.py` with FastAPI app
- [x] Create `services/contacts/settings.py` using `services.common.settings`
- [x] Create `services/contacts/database.py` for database connection
- [x] Create `services/contacts/models/` directory for database models
- [x] Create `services/contacts/schemas/` directory for Pydantic schemas
- [x] Create `services/contacts/routers/` directory for API endpoints
- [x] Create `services/contacts/services/` directory for business logic
- [x] Create `services/contacts/tests/` directory for tests

### Phase 2: Move and Adapt Contact Models
- [x] Move `EmailContact` model to `services/contacts/models/contact.py`
- [x] Create SQLModel table model for `Contact` with proper database fields
- [x] Move `EmailContactUpdate` to `services/contacts/schemas/contact.py`
- [x] Move `EmailContactSearchResult` to `services/contacts/schemas/contact.py`
- [x] Move `EmailContactEventCount` to `services/contacts/models/contact.py`
- [x] Update models to use SQLModel for database persistence
- [x] Add database indexes for common query patterns (user_id, email, relevance_score)
- [x] Create database migration scripts using Alembic

### Phase 3: Move Contact Discovery Service
- [x] Move `ContactDiscoveryService` to `services/contacts/services/contact_discovery_service.py`
- [x] Update service to use database models instead of in-memory cache
- [x] Integrate with database session management
- [x] Update contact creation/update logic for database persistence
- [x] Maintain event processing capabilities for contact discovery
- [x] Update relevance score calculation for database-stored contacts

### Phase 4: Move Contact Discovery Consumer
- [x] Move `ContactDiscoveryConsumer` to `services/contacts/services/contact_discovery_consumer.py`
- [x] Update consumer to work with new service structure
- [x] Maintain PubSub topic subscriptions (emails, calendars, documents, todos)
- [x] Update event processing to use new contact discovery service
- [x] Ensure proper error handling and logging

### Phase 5: Create Contact API Endpoints
- [x] Create `services/contacts/routers/contacts.py` with RESTful endpoints
- [x] Implement `GET /contacts` - List user contacts with search/filtering
- [x] Implement `GET /contacts/{contact_id}` - Get specific contact
- [x] Implement `POST /contacts` - Create new contact
- [x] Implement `PUT /contacts/{contact_id}` - Update contact
- [x] Implement `DELETE /contacts/{contact_id}` - Delete contact
- [x] Implement `GET /contacts/search` - Search contacts by query
- [x] Implement `GET /contacts/stats` - Get contact statistics
- [x] Add proper authentication and authorization middleware
- [x] Add request validation and error handling

### Phase 6: Create Contact Management Service
- [x] Create `services/contacts/services/contact_service.py` for business logic
- [x] Implement contact CRUD operations
- [x] Implement contact search and filtering
- [x] Implement contact relevance scoring
- [x] Implement contact statistics and analytics
- [x] Add contact deduplication logic
- [x] Add contact import/export capabilities

### Phase 7: Update Service Configuration
- [x] Add Contacts Service to `scripts/start-all-services.sh` (port 8007)
- [x] Add Contacts Service to `scripts/postgres-start.sh` database creation
- [x] Add Contacts Service to `scripts/check-db-status.sh` database URLs
- [x] Add Contacts Service to `scripts/run-migrations.sh` migration support
- [x] Update `.example.env` with Contacts Service environment variables
- [x] Create `env.postgres.local` entry for Contacts Service database password
- [x] Add Contacts Service to port checks and health checks

### Phase 8: Update Environment Variables
- [x] Add `DB_URL_CONTACTS` to `.example.env`
- [x] Add `CONTACTS_SERVICE_URL` to `.example.env`
- [x] Add `API_FRONTEND_CONTACTS_KEY` to `.example.env`
- [x] Add `API_CONTACTS_USER_KEY` to `.example.env`
- [x] Add `API_CONTACTS_OFFICE_KEY` to `.example.env`
- [x] Add `API_CONTACTS_CHAT_KEY` to `.example.env`
- [x] Add `API_CONTACTS_MEETINGS_KEY` to `.example.env`
- [x] Add `API_CONTACTS_SHIPMENTS_KEY` to `.example.env`

### Phase 9: Update Database Configuration
- [x] Add `briefly_contacts` database creation in PostgreSQL setup
- [x] Create `briefly_contacts_service` user with proper permissions
- [x] Update database URL patterns for Contacts Service
- [x] Create initial database migration for contact tables
- [x] Add database health checks to Contacts Service

### Phase 10: Update Service Dependencies
- [x] Update User Service to remove contact discovery dependencies
- [x] Update Office Service to use Contacts Service API instead of internal logic
- [x] Update Chat Service to use Contacts Service for contact lookups
- [x] Update Meetings Service to use Contacts Service for attendee information
- [x] Update Shipments Service to use Contacts Service for contact data
- [x] Ensure all services use API key authentication for Contacts Service

### Phase 11: Update Frontend Integration
- [x] Update `frontend/api/clients/` to use Contacts Service endpoints
- [x] Create `frontend/api/clients/contacts-client.ts` for Contacts Service
- [x] Update `frontend/types/api/` to use Contacts Service schemas
- [x] Update Office Service frontend integration to use Contacts Service
- [x] Ensure contact management UI works with new service
- [x] Update contact search and filtering functionality

### Phase 12: Update Event Processing
- [x] Ensure Contacts Service can process all relevant event types
- [x] Update event processing to store contacts in database
- [x] Maintain PubSub integration for contact updates
- [x] Ensure Vespa integration continues to work
- [x] Update event consumers to use new contact data structure

### Phase 13: Update Tests
- [x] Move contact tests to `services/contacts/tests/`
- [x] Update test imports and dependencies
- [x] Create integration tests for Contacts Service API
- [x] Test contact discovery from various event types
- [x] Test contact CRUD operations via API
- [x] Test contact search and filtering
- [x] Test service-to-service authentication
- [x] Ensure all existing contact functionality is covered

### Phase 14: Revise API keys

- [ x] Add `API_CONTACTS_CHAT_KEY` to `.example.env`
- [x] Add `API_CONTACTS_MEETINGS_KEY` to `.example.env`
- [x] Add `API_CONTACTS_SHIPMENTS_KEY` to `.example.env`

### Phase 14: Update Documentation
- [ ] Update `documentation/new-service-guide.md` if needed
- [ ] Create `services/contacts/README.md` with service documentation
- [ ] Update API documentation for contact endpoints
- [ ] Update service architecture documentation
- [ ] Update deployment and configuration guides

### Phase 15: Cleanup User Service
- [ ] Remove `services/user/services/contact_discovery_service.py`
- [ ] Remove `services/user/services/contact_discovery_consumer.py`
- [ ] Remove `services/user/tests/test_contact_discovery_service.py`
- [ ] Remove contact-related imports from User Service
- [ ] Update User Service to remove contact dependencies
- [ ] Ensure User Service tests still pass

### Phase 16: Update Common Models
- [ ] Move `services/common/models/email_contact.py` to Contacts Service
- [ ] Update any remaining references to use Contacts Service models
- [ ] Ensure no breaking changes to other services
- [ ] Update common model imports across the codebase

### Phase 17: Integration Testing
- [ ] Test contact discovery from email events
- [ ] Test contact discovery from calendar events
- [ ] Test contact discovery from document events
- [ ] Test contact discovery from todo events
- [ ] Test contact API endpoints
- [ ] Test service-to-service communication
- [ ] Test contact search and filtering
- [ ] Test contact relevance scoring

### Phase 20: Post-Migration Cleanup
- [ ] Remove old contact code from User Service
- [ ] Clean up any unused dependencies
- [ ] Update service documentation
- [ ] Archive old contact-related code
- [ ] Monitor service performance and stability

## Technical Implementation Details

### Service Structure
```
services/contacts/
├── __init__.py
├── main.py                    # FastAPI app entry point
├── pyproject.toml            # Service dependencies
├── settings.py               # Configuration management
├── database.py               # Database connection setup
├── models/
│   ├── __init__.py
│   └── contact.py            # SQLModel contact models
├── schemas/
│   ├── __init__.py
│   ├── contact.py            # Pydantic contact schemas
│   └── api.py                # API request/response models
├── routers/
│   ├── __init__.py
│   └── contacts.py           # Contact API endpoints
├── services/
│   ├── __init__.py
│   ├── contact_service.py    # Contact business logic
│   ├── contact_discovery_service.py  # Event processing
│   └── contact_discovery_consumer.py # PubSub consumer
├── tests/
│   ├── __init__.py
│   ├── test_contact_service.py
│   ├── test_contact_discovery_service.py
│   └── test_contact_api.py
└── alembic/                  # Database migrations
    ├── alembic.ini
    ├── env.py
    └── versions/
```

### Database Schema
```sql
-- contacts table
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR NOT NULL,
    email_address VARCHAR NOT NULL,
    display_name VARCHAR,
    given_name VARCHAR,
    family_name VARCHAR,
    event_counts JSONB DEFAULT '{}',
    total_event_count INTEGER DEFAULT 0,
    last_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    first_seen TIMESTAMP WITH TIME ZONE NOT NULL,
    relevance_score FLOAT DEFAULT 0.0,
    relevance_factors JSONB DEFAULT '{}',
    source_services TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_contacts_user_id ON contacts(user_id);
CREATE INDEX idx_contacts_email ON contacts(email_address);
CREATE INDEX idx_contacts_relevance ON contacts(relevance_score DESC);
CREATE INDEX idx_contacts_last_seen ON contacts(last_seen DESC);
CREATE UNIQUE INDEX idx_contacts_user_email ON contacts(user_id, email_address);
```

### API Endpoints
```
GET    /v1/contacts                    # List contacts with filtering
GET    /v1/contacts/{contact_id}       # Get specific contact
POST   /v1/contacts                    # Create new contact
PUT    /v1/contacts/{contact_id}       # Update contact
DELETE /v1/contacts/{contact_id}       # Delete contact
GET    /v1/contacts/search             # Search contacts
GET    /v1/contacts/stats              # Get contact statistics
GET    /health                         # Health check
GET    /ready                          # Readiness check
```

### Service Dependencies
```toml
[project]
name = "briefly-contacts"
version = "0.1.0"
description = "Briefly Contacts Service - Contact discovery and management"
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
    "google-cloud-pubsub>=2.18.0,<3.0.0",
    "redis>=5.0.0,<6.0.0",
    "alembic>=1.12.0,<2.0.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.4.0,<8.0.0",
    "pytest-asyncio>=0.21.0,<1.0.0",
    "httpx>=0.25.0,<1.0.0",
]
```

### Environment Variables
```bash
# Database
DB_URL_CONTACTS=postgresql://briefly_contacts_service:$TODO@localhost:5432/briefly_contacts

# Service URLs
CONTACTS_SERVICE_URL=http://127.0.0.1:8007

# API Keys
API_FRONTEND_CONTACTS_KEY=$TODO
API_CONTACTS_USER_KEY=$TODO
API_CONTACTS_OFFICE_KEY=$TODO
API_CONTACTS_CHAT_KEY=$TODO
API_CONTACTS_MEETINGS_KEY=$TODO
API_CONTACTS_SHIPMENTS_KEY=$TODO

# PubSub Configuration
PUBSUB_PROJECT_ID=briefly-dev
PUBSUB_EMULATOR_HOST=localhost:8085
```

### Service Integration Points
- **User Service**: For user authentication and profile data
- **Office Service**: For contact management UI and operations
- **Chat Service**: For contact lookups during conversations
- **Meetings Service**: For attendee contact information
- **Shipments Service**: For contact data in shipping operations
- **Vespa Loader**: For contact indexing and search

## Benefits of Migration
- **Service Separation**: Clear separation of contact concerns from user management
- **Scalability**: Dedicated service can scale independently
- **Maintainability**: Focused service with single responsibility
- **Performance**: Optimized database queries and caching for contacts
- **Flexibility**: Easier to add contact-specific features and integrations
- **Testing**: Isolated testing environment for contact functionality
- **Deployment**: Independent deployment and versioning

## Risks and Mitigation
- **Breaking Changes**: Careful migration planning and backward compatibility
- **Data Migration**: Comprehensive testing of contact data integrity
- **Service Dependencies**: Clear API contracts and error handling
- **Performance Impact**: Monitor and optimize database queries
- **Integration Complexity**: Thorough testing of all service interactions

## Dependencies
- PostgreSQL database setup
- Redis for caching (if needed)
- PubSub for event processing
- Service-to-service authentication
- Frontend integration updates
- Comprehensive testing infrastructure

## Success Criteria
- [ ] All contact functionality moved to new service
- [ ] Contact API endpoints working correctly
- [ ] Contact discovery from events functioning
- [ ] Service integration working properly
- [ ] Frontend contact management working
- [ ] All tests passing
- [ ] Performance meeting requirements
- [ ] Documentation updated
- [ ] User Service cleaned up
- [ ] No breaking changes to existing functionality
