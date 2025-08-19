# Office Router Service

Central routing service for office data distribution in the Briefly platform.

## Overview

The Office Router Service acts as a message broker and router between various office-related services. It consumes messages from Google Cloud PubSub topics and routes them to appropriate downstream services based on data type and configuration.

## Features

- **Data Routing**: Routes email, calendar, and contact data to downstream services
- **PubSub Integration**: Consumes messages from Google Cloud PubSub topics
- **Concurrent Processing**: Routes to multiple services simultaneously
- **Health Monitoring**: Tracks downstream service health and routing statistics
- **API Key Authentication**: Secure inter-service communication
- **Configurable Endpoints**: Flexible downstream service configuration

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PubSub Topic  │───▶│  Office Router   │───▶│ Downstream      │
│                 │    │                  │    │ Services        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   HTTP API       │
                       │   Endpoints      │
                       └──────────────────┘
```

## Supported Data Types

### Email Data
- Routes to: Vespa, Shipments, Contacts, Notifications
- Fields: id, user_id, provider, subject, body, from, to, cc, bcc, etc.

### Calendar Data
- Routes to: Vespa, Shipments, Contacts, Notifications
- Fields: id, user_id, provider, subject, start_time, end_time, attendees, etc.

### Contact Data
- Routes to: Vespa, Shipments, Contacts, Notifications
- Fields: id, user_id, provider, display_name, email_addresses, phone_numbers, etc.

## Downstream Services

- **Vespa**: Vector database for document indexing/search
- **Shipments**: Shipment-related processing
- **Contacts**: Contact management
- **Notifications**: Notification delivery

## API Endpoints

### Health & Status
- `GET /health` - Service health check
- `GET /status` - Detailed service status and downstream service health

### Data Routing
- `POST /route/email` - Route email data (requires API key)
- `POST /route/calendar` - Route calendar data (requires API key)
- `POST /route/contact` - Route contact data (requires API key)

## Configuration

### Environment Variables

```bash
# Service Configuration
OFFICE_ROUTER_PORT=8006
OFFICE_ROUTER_HOST=0.0.0.0

# API Keys
API_FRONTEND_OFFICE_ROUTER_KEY=your-frontend-key
API_OFFICE_ROUTER_USER_KEY=your-user-key
API_OFFICE_ROUTER_OFFICE_KEY=your-office-key

# Downstream Service Endpoints
VESPA_ENDPOINT=http://localhost:8080
SHIPMENTS_ENDPOINT=http://localhost:8004
CONTACTS_ENDPOINT=http://localhost:8002
NOTIFICATIONS_ENDPOINT=http://localhost:8003

# PubSub Configuration
PUBSUB_PROJECT_ID=briefly-dev
PUBSUB_EMULATOR_HOST=localhost:8085
PUBSUB_EMAIL_TOPIC=email-backfill
PUBSUB_CALENDAR_TOPIC=calendar-updates
```

## Development

### Prerequisites
- Python 3.12+
- Google Cloud PubSub (or emulator)
- Access to downstream services

### Setup
```bash
# Install dependencies
uv pip install -e services/office_router

# Run service
uv run python -m uvicorn services.office_router.main:app --port 8006 --reload

# Run tests
uv run python -m pytest services/office_router/tests/ -v
```

### Running with All Services
```bash
# Start all services including office_router
./scripts/start-all-services.sh
```

## Testing

The service includes comprehensive tests covering:
- Health check endpoints
- Service status endpoints
- API key authentication
- Data routing endpoints

Run tests with:
```bash
uv run python -m pytest services/office_router/tests/ -v
```

## Monitoring

The service provides:
- Request logging middleware
- Health check endpoints
- Downstream service health monitoring
- Routing statistics and error tracking

## Security

- API key authentication for all routing endpoints
- Configurable CORS settings
- Secure inter-service communication

## Dependencies

- FastAPI - Web framework
- Uvicorn - ASGI server
- Google Cloud PubSub - Message queuing
- aiohttp - Async HTTP client
- Pydantic - Data validation
- Structlog - Structured logging
- OpenTelemetry - Distributed tracing
