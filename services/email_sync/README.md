# Email Sync Service

This service handles email webhook notifications (Gmail, Microsoft) and publishes them to pubsub topics for downstream processing.

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in required values.
3. Run the Flask app:
   ```
   flask run --host=0.0.0.0 --port=8080
   ```

## Local Development with Docker Compose

1. Build and start all services:
   ```
   docker-compose up --build
   ```
2. The email_sync service will be available at http://localhost:8080
3. The PubSub emulator will be available at localhost:8085

## Environment Variables
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `PUBSUB_EMULATOR_HOST`: Host for local pubsub emulator (e.g., localhost:8085)
- `GMAIL_WEBHOOK_SECRET`: Secret for Gmail webhook validation

## Message Schemas
See `schemas.py` for pubsub message formats. 

## Running Tests

Run all tests with:
```
pytest
``` 

## Integration Testing

- To run the full pipeline locally:
  1. Start docker-compose as above.
  2. Use curl or Postman to POST to the webhook endpoints (see below).
  3. Inspect logs for published and processed messages.

### Example: Send Gmail Notification
```
curl -X POST http://localhost:8080/gmail/webhook \
  -H 'X-Gmail-Webhook-Secret: dev-gmail-secret' \
  -H 'Content-Type: application/json' \
  -d '{"history_id": "12345", "email_address": "user@example.com"}'
```

### Example: Send Microsoft Notification
```
curl -X POST http://localhost:8080/microsoft/webhook \
  -H 'X-Microsoft-Signature: dev-microsoft-secret' \
  -H 'Content-Type: application/json' \
  -d '{"value": [{"changeType": "created", "resource": "me/messages/1"}]}'
```

- Check logs for downstream processing and event publishing. 

## API Documentation

### Endpoints
- `POST /gmail/webhook` — Receives Gmail push notifications
- `POST /microsoft/webhook` — Receives Microsoft Graph webhook notifications
- `GET /healthz` — Health check endpoint

See code for payload schemas and authentication headers.

## Observability & Monitoring

- Metrics: Use `record_metric` in `observability.py` to log and collect metrics. Integrate with Prometheus or Stackdriver as needed.
- Tracing: Use `@trace_function` decorator for distributed tracing (OpenTelemetry stub included).
- Health checks: Use `/healthz` endpoint for liveness/readiness probes.
- Extend logging and alerting for production monitoring and dashboards.

## Deployment & Runbook

- Build and deploy the email_sync service container to your environment.
- Ensure environment variables and secrets are set for all providers.
- Monitor logs for errors and alerts (pubsub failures, API errors, subscription issues).
- Use the health check endpoint for liveness/readiness probes.
- See `docker-compose.yml` for local development and testing setup. 

## Security & Compliance

- Secret management: Use environment variables or integrate with GCP Secret Manager.
- Input validation: Use `validate_input` in `security.py` for all incoming data.
- Rate limiting: Add Flask-Limiter or similar for endpoint protection.
- Audit logging: Use `audit_log` for sensitive operations.
- PII redaction: Use `redact_pii` to sanitize logs and outputs.
- See `security.py` for stubs and extension points. 