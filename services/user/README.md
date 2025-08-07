# User Management Service

This service provides user management, authentication, and profile functionality for Briefly. It uses **cursor-based pagination** for all list endpoints to ensure consistent results and better performance.

## API Documentation

For detailed API documentation including cursor-based pagination examples, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

## OpenTelemetry Configuration

This document outlines how to configure OpenTelemetry for the User Management Service, both for deployment on Google Cloud Run and for local development.

---

## OpenTelemetry Configuration for Google Cloud Run

### IAM Permissions
The service account used by your Cloud Run service needs permission to write traces.
- Navigate to the IAM page in the Google Cloud Console.
- Find the service account your Cloud Run service uses (by default, it's `[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`).
- Grant it the "Cloud Trace Agent" role (`roles/cloudtrace.agent`).

### Environment Variables
Deploy your service with the following environment variables:
- `OTEL_TRACES_EXPORTER=gcp_trace`
- `OTEL_SERVICE_NAME=user-service`
- `OTEL_PYTHON_TRACER_PROVIDER=sdk_tracer_provider` (This is required for the GCP Trace Exporter)

### Deployment Command
Example `gcloud run deploy` command:
```bash
gcloud run deploy user-service \
  --image gcr.io/[PROJECT_ID]/[USER_SERVICE_IMAGE_NAME] \
  --platform managed \
  --region [YOUR_REGION] \
  --allow-unauthenticated \
  --set-env-vars="OTEL_TRACES_EXPORTER=gcp_trace" \
  --set-env-vars="OTEL_SERVICE_NAME=user-service" \
  --set-env-vars="OTEL_PYTHON_TRACER_PROVIDER=sdk_tracer_provider"
```
Replace `[PROJECT_ID]`, `[USER_SERVICE_IMAGE_NAME]`, and `[YOUR_REGION]` with your specific values. The `user-service` typically runs on port 8001, which should be configured in your `Dockerfile.user-service`.

---

## Local Development with OpenTelemetry

For local development, you can configure OpenTelemetry to print traces directly to your console. This is useful for verifying that instrumentation is working without sending data to Google Cloud Trace.

Use the following command to run your service locally with console tracing:
```bash
OTEL_TRACES_EXPORTER=console \
OTEL_SERVICE_NAME=local-user-service \
opentelemetry-instrument uvicorn services.user.main:app --reload --host 0.0.0.0 --port 8001
```
When you make a request to your local service, you will see trace data printed as JSON in your terminal.
---

## API Endpoint Patterns

- **User-facing endpoints:**
  - Use `/me` (e.g., `/users/me`, `/users/me/preferences`)
  - Require user authentication (JWT/session)
  - Extract user from token, not from path/query

- **Internal/service endpoints:**
  - Use `/internal` prefix (e.g., `/internal/users/id`, `/internal/users/`)
  - Require API key/service authentication
  - Used for service-to-service and background job calls
