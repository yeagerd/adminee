# Docker Patterns and Best Practices

This document explains the consistent patterns used across all Dockerfiles in this project, including GCP Secret Manager integration.

## Environment Variable Strategy

### Frontend Service (Next.js)
**Pattern**: Build-time + Runtime variables
**Reasoning**: Next.js embeds `NEXT_PUBLIC_*` variables into static assets during build

#### Local/CI Development
```dockerfile
# Build-time arguments with dummy defaults for CI
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="pk_test_dummy_key_for_build_time_only"
ARG CLERK_SECRET_KEY="sk_test_dummy_secret_for_build_time_only"

# Convert to environment variables for build process
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV CLERK_SECRET_KEY=$CLERK_SECRET_KEY

# Build requires these variables
RUN npm run build
```

#### GCP Production Deployment
**Cloud Build**: Use secret substitutions for build-time variables
```yaml
# cloudbuild.yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: 
  - 'build'
  - '-f'
  - 'Dockerfile.frontend'
  - '--build-arg'
  - 'NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${_CLERK_PUBLISHABLE_KEY}'
  - '--build-arg'
  - 'CLERK_SECRET_KEY=${_CLERK_SECRET_KEY}'
  - '-t'
  - 'gcr.io/$PROJECT_ID/frontend'
  - '.'
substitutions:
  _CLERK_PUBLISHABLE_KEY: '${_CLERK_PUBLISHABLE_KEY}'
  _CLERK_SECRET_KEY: '${_CLERK_SECRET_KEY}'
availableSecrets:
  secretManager:
  - versionName: projects/$PROJECT_ID/secrets/clerk-publishable-key/versions/latest
    env: '_CLERK_PUBLISHABLE_KEY'
  - versionName: projects/$PROJECT_ID/secrets/clerk-secret-key/versions/latest
    env: '_CLERK_SECRET_KEY'
```

**Cloud Run**: Mount additional runtime secrets
```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/secrets: |
          {
            "clerk-secret-key": {
              "name": "clerk-secret-key",
              "items": [{"key": "latest", "path": "CLERK_SECRET_KEY"}]
            }
          }
```

### Backend Services (Python/FastAPI)
**Pattern**: Runtime-only variables via Secret Manager
**Reasoning**: Python services read environment variables when they start, not during build

#### Local Development
```dockerfile
# NO build-time arguments needed
# Runtime environment variables provided via docker-compose.yml

# Standard Python setup
FROM python:3.11-slim-bullseye
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

#### GCP Production Deployment
**Option 1: Secret Manager SDK Integration**
```python
# services/common/secrets.py
from google.cloud import secretmanager
import os

def get_secret(secret_id: str) -> str:
    """Retrieve secret from GCP Secret Manager"""
    if os.getenv('ENVIRONMENT') == 'local':
        return os.getenv(secret_id, '')
    
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Usage in settings
DB_URL_USER_MANAGEMENT = get_secret("db-url-user-management")
CLERK_SECRET_KEY = get_secret("clerk-secret-key")
```

**Option 2: Cloud Run Secret Mounts**
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/secrets: |
          {
            "db-url-user-management": {
              "name": "db-url-user-management",
              "items": [{"key": "latest", "path": "DB_URL_USER_MANAGEMENT"}]
            },
            "clerk-secret-key": {
              "name": "clerk-secret-key", 
              "items": [{"key": "latest", "path": "CLERK_SECRET_KEY"}]
            }
          }
```

## GCP Secret Manager Setup

### Creating Secrets
```bash
# Create secrets in Secret Manager
gcloud secrets create clerk-publishable-key --data-file=-
gcloud secrets create clerk-secret-key --data-file=-
gcloud secrets create db-url-user-management --data-file=-
gcloud secrets create redis-url --data-file=-

# Grant access to Cloud Build and Cloud Run
gcloud secrets add-iam-policy-binding clerk-publishable-key \
    --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding clerk-secret-key \
    --member="serviceAccount:${CLOUD_RUN_SA}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Service Account Configuration
```bash
# Create service account for Cloud Run
gcloud iam service-accounts create briefly-backend \
    --display-name="Briefly Backend Services"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:briefly-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# For GKE: Enable Workload Identity
gcloud iam service-accounts add-iam-policy-binding \
    briefly-backend@${PROJECT_ID}.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[briefly/briefly-backend]"
```

## Security Considerations

### Build-time Variables (ARG/ENV)
- ✅ **Use when**: Build process requires the variable (Next.js, asset compilation)
- ⚠️ **Security**: Values are visible in image layers
- 🔧 **Mitigation**: 
  - Use dummy values as defaults
  - Inject real secrets via Cloud Build substitutions
  - Never commit real secrets to git

### Runtime Variables (Secret Manager)
- ✅ **Use when**: Service reads variables at startup
- ✅ **Security**: Not embedded in image layers
- ✅ **Flexibility**: Can be rotated without rebuilding images
- ✅ **Audit**: Full audit trail in GCP

## Deployment Patterns

### Local Development
```bash
# Use dummy values or local .env files
docker-compose up -d
```

### CI/CD Pipeline
```bash
# Cloud Build with secret substitutions
gcloud builds submit --config=cloudbuild.yaml
```

### Production Deployment
```bash
# Cloud Run with secret mounts
gcloud run deploy briefly-frontend \
  --image=gcr.io/$PROJECT_ID/frontend \
  --update-secrets=CLERK_SECRET_KEY=clerk-secret-key:latest

gcloud run deploy briefly-user-service \
  --image=gcr.io/$PROJECT_ID/user-service \
  --update-secrets=DB_URL_USER_MANAGEMENT=db-url-user-management:latest \
  --service-account=briefly-backend@${PROJECT_ID}.iam.gserviceaccount.com
```

## Environment-Specific Configuration

### Dockerfile Support for Multiple Environments
```dockerfile
# Add environment detection
ENV ENVIRONMENT=production
ENV GOOGLE_CLOUD_PROJECT=""

# Runtime secret resolution happens in application code
# No secrets embedded in Docker images
```

### Application Configuration
```python
# config/settings.py
import os
from .config_secrets import get_secret

class Settings:
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'local')
        
        # Use Secret Manager in production, env vars locally
        if self.environment == 'production':
            self.db_url = get_secret('db-url-user-management')
            self.clerk_secret = get_secret('clerk-secret-key')
        else:
            self.db_url = os.getenv('DB_URL_USER_MANAGEMENT')
            self.clerk_secret = os.getenv('CLERK_SECRET_KEY')
```

## Testing

All builds should work without real secrets:
```bash
# Local development with dummy values
docker build -f Dockerfile.frontend -t test-frontend .
docker build -f Dockerfile.user-service -t test-user .

# CI/CD testing with Secret Manager
gcloud builds submit --config=cloudbuild-test.yaml
```

## Consistent Dockerfile Structure

All Dockerfiles follow this pattern:

```dockerfile
# Service description comment
FROM base-image

# Environment variables for build system (if needed)
ENV BUILD_SYSTEM_VARS=value

# Build-time arguments (frontend only)
ARG VAR_NAME="default_value"
ENV VAR_NAME=$VAR_NAME

# System dependencies
RUN apt-get update && install packages

# Application dependencies
COPY requirements.txt .
RUN install dependencies

# Application code
COPY service_code/ ./service_code/

# Runtime configuration
ENV PYTHONPATH=/app  # or similar

# Documentation comment about runtime variables
# Note: Runtime environment variables provided via docker-compose.yml

# Health check and startup
EXPOSE port
HEALTHCHECK --interval=30s CMD health_check
CMD ["startup_command"]
```

## Production Deployment

1. **Frontend**: Override build args with real values
2. **Backend**: Provide runtime environment variables
3. **All**: Use docker-compose with production environment files 