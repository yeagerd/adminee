# Email Sync Service

This service handles email webhook notifications (Gmail, Microsoft) and publishes them to pubsub topics for downstream processing.

## Architecture

- **Framework**: FastAPI with Uvicorn (migrated from Flask)
- **Dependency Management**: pyproject.toml (migrated from requirements.txt)
- **Execution**: Run from repository root using `uv`
- **Containerization**: Docker with Python 3.12

## Local Development

### Prerequisites
- Python 3.12+
- `uv` package manager
- Docker and Docker Compose

### Setup
1. Install dependencies from repository root:
   ```bash
   uv sync
   ```

2. Copy `.env.example` to `.env` and fill in required values.

3. Run the FastAPI app from repository root:
   ```bash
   uv run uvicorn services.email_sync.app:app --host=0.0.0.0 --port=8080 --reload
   ```

## Local Development with Docker Compose

### Quick Start
1. Build and start all services:
   ```bash
   docker-compose -f docker-compose.email_sync.yml up --build
   ```

2. The email_sync service will be available at http://localhost:8080
3. The PubSub emulator will be available at localhost:8085

### Services
- **email_sync**: FastAPI service running on port 8080
- **pubsub**: Google Cloud Pub/Sub emulator running on port 8085

## Environment Variables
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID (default: local-project)
- `PUBSUB_EMULATOR_HOST`: Host for local pubsub emulator (default: pubsub:8085)
- `GMAIL_WEBHOOK_SECRET`: Secret for Gmail webhook validation (default: dev-gmail-secret)
- `MICROSOFT_WEBHOOK_SECRET`: Secret for Microsoft webhook validation (default: dev-microsoft-secret)

## Message Schemas
See `schemas.py` for pubsub message formats.

## Running Tests

Run all tests from repository root:
```bash
uv run pytest services/email_sync/tests/
```

## Integration Testing

### Quick Test
1. Start docker-compose as above.
2. Test the health endpoint:
   ```bash
   curl http://localhost:8080/healthz
   ```

3. Send test webhooks (see examples below).
4. Monitor logs for published and processed messages.

### Example: Send Gmail Notification
```bash
curl -X POST http://localhost:8080/gmail/webhook \
  -H 'X-Gmail-Webhook-Secret: dev-gmail-secret' \
  -H 'Content-Type: application/json' \
  -d '{"history_id": "12345", "email_address": "user@example.com"}'
```

### Example: Send Microsoft Notification
```bash
curl -X POST http://localhost:8080/microsoft/webhook \
  -H 'X-Microsoft-Signature: dev-microsoft-secret' \
  -H 'Content-Type: application/json' \
  -d '{"value": [{"changeType": "created", "resource": "me/messages/1"}]}'
```

### Monitoring Backend Activity

#### Real-time Logs
```bash
# Follow logs in real-time
docker-compose -f docker-compose.email_sync.yml logs -f email_sync

# Or follow both services
docker-compose -f docker-compose.email_sync.yml logs -f
```

#### Recent Logs
```bash
# Last 20 lines
docker logs briefly-email_sync-1 --tail 20

# All logs
docker logs briefly-email_sync-1
```

#### Pub/Sub Emulator Logs
```bash
docker logs briefly-pubsub-1 --tail 20
```

#### Interactive Debugging
```bash
# Get a shell inside the container
docker exec -it briefly-email_sync-1 /bin/bash
```

## API Documentation

### Endpoints
- `POST /gmail/webhook` — Receives Gmail push notifications
- `POST /microsoft/webhook` — Receives Microsoft Graph webhook notifications  
- `GET /healthz` — Health check endpoint

### Authentication
- **Gmail**: Requires `X-Gmail-Webhook-Secret` header
- **Microsoft**: Requires `X-Microsoft-Signature` header

See code for payload schemas and detailed authentication requirements.

## Test Data Injection

A comprehensive test script is available to inject realistic test data:

```bash
# Run from within the container (when services are running)
docker exec -e PUBSUB_EMULATOR_HOST=pubsub:8085 briefly-email_sync-1 \
  python services/email_sync/scripts/inject_test_data.py --all
```

The script can:
- Create topics and subscriptions
- Publish Gmail webhook notifications
- Publish Microsoft webhook notifications  
- Publish email data for processing
- Listen for downstream events

## Observability & Monitoring

- **Metrics**: Use `record_metric` in `observability.py` to log and collect metrics
- **Tracing**: OpenTelemetry integration for distributed tracing
- **Health checks**: Use `/healthz` endpoint for liveness/readiness probes
- **Logging**: Structured logging with structlog

## Deployment & Runbook

- Build and deploy the email_sync service container to your environment
- Ensure environment variables and secrets are set for all providers
- Monitor logs for errors and alerts (pubsub failures, API errors, subscription issues)
- Use the health check endpoint for liveness/readiness probes
- See `docker-compose.email_sync.yml` for local development and testing setup

## Security & Compliance

- **Secret management**: Use environment variables or integrate with GCP Secret Manager
- **Input validation**: Pydantic models for request validation
- **Rate limiting**: Add rate limiting middleware for endpoint protection
- **Audit logging**: Structured logging for sensitive operations
- **PII redaction**: Use redaction utilities to sanitize logs and outputs

## Migration Notes

This service was migrated from Flask to FastAPI for consistency with other services in the project. Key changes:
- Flask → FastAPI with Uvicorn
- requirements.txt → pyproject.toml
- Flask Blueprint → FastAPI APIRouter
- Relative imports → Absolute imports from repo root
- Python 3.11 → Python 3.12 