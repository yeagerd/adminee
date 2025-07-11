#!/bin/bash

# Setup script for GCP Secret Manager and service accounts
# Run this script to configure secrets and permissions for Briefly deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 &> /dev/null; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    PROJECT_ID=$(gcloud config get-value project)
    if [ -z "$PROJECT_ID" ]; then
        log_error "No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
    
    log_info "Using project: $PROJECT_ID"
}

# Enable required APIs
enable_apis() {
    log_info "Enabling required APIs..."
    
    gcloud services enable secretmanager.googleapis.com
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    gcloud services enable containerregistry.googleapis.com
    
    log_info "APIs enabled successfully"
}

# Create service accounts
create_service_accounts() {
    log_info "Creating service accounts..."
    
    # Backend service account
    if ! gcloud iam service-accounts describe "briefly-backend@${PROJECT_ID}.iam.gserviceaccount.com" &> /dev/null; then
        gcloud iam service-accounts create briefly-backend \
            --display-name="Briefly Backend Services" \
            --description="Service account for Briefly backend services"
        log_info "Created briefly-backend service account"
    else
        log_warn "Service account briefly-backend already exists"
    fi
    
    # Grant permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:briefly-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
    
    log_info "Service accounts configured"
}

# Create secrets in Secret Manager
create_secrets() {
    log_info "Creating secrets in Secret Manager..."
    
    # List of secrets to create
    declare -a secrets=(
        "nextauth-url"
        "nextauth-secret"
        "azure-ad-client-id"
        "azure-ad-client-secret"
        "azure-ad-tenant-id"
        "db-url-user-management"
        "db-url-office"
        "db-url-chat"
        "redis-url"
        "token-encryption-salt"
        "openai-api-key"
        "pinecone-api-key"
        "pinecone-environment"
    )
    
    for secret in "${secrets[@]}"; do
        if ! gcloud secrets describe "$secret" &> /dev/null; then
            # Create secret with placeholder value
            echo "PLACEHOLDER_${secret^^}" | gcloud secrets create "$secret" --data-file=-
            log_info "Created secret: $secret (with placeholder value)"
        else
            log_warn "Secret $secret already exists"
        fi
    done
    
    log_warn "Remember to update secret values with real data:"
    log_warn "gcloud secrets versions add SECRET_NAME --data-file=path/to/secret/file"
}

# Grant Cloud Build access to secrets
setup_cloudbuild_permissions() {
    log_info "Setting up Cloud Build permissions..."
    
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    
    # Grant Cloud Build service account access to secrets
    declare -a build_secrets=(
        "nextauth-url"
        "nextauth-secret"
        "azure-ad-client-id"
        "azure-ad-client-secret"
        "azure-ad-tenant-id"
    )
    
    for secret in "${build_secrets[@]}"; do
        gcloud secrets add-iam-policy-binding "$secret" \
            --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor"
    done
    
    log_info "Cloud Build permissions configured"
}

# Grant Cloud Run service account access to runtime secrets
setup_cloudrun_permissions() {
    log_info "Setting up Cloud Run permissions..."
    
    # Runtime secrets for backend services
    declare -a runtime_secrets=(
        "db-url-user-management"
        "db-url-office"
        "db-url-chat"
        "redis-url"
        "token-encryption-salt"
        "openai-api-key"
        "pinecone-api-key"
        "pinecone-environment"
    )
    
    for secret in "${runtime_secrets[@]}"; do
        gcloud secrets add-iam-policy-binding "$secret" \
            --member="serviceAccount:briefly-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor"
    done
    
    log_info "Cloud Run permissions configured"
}

# Create sample environment file
create_sample_env() {
    log_info "Creating sample environment file..."
    
    cat > .env.gcp.sample << 'EOF'
# GCP Secret Manager Configuration
# Copy this file to .env.gcp and fill in your actual values

# NextAuth Configuration
NEXTAUTH_URL=https://your-domain.com
NEXTAUTH_SECRET=your_nextauth_secret_here

# Azure AD (if using)
AZURE_AD_CLIENT_ID=your_azure_client_id
AZURE_AD_CLIENT_SECRET=your_azure_client_secret
AZURE_AD_TENANT_ID=your_azure_tenant_id

# Database URLs
DB_URL_USER_MANAGEMENT=postgresql://user:pass@host:port/db_user
DB_URL_OFFICE=postgresql://user:pass@host:port/db_office
DB_URL_CHAT=postgresql://user:pass@host:port/db_chat

# Redis
REDIS_URL=redis://redis-host:6379

# Security
TOKEN_ENCRYPTION_SALT=your_encryption_salt_here

# AI Services
OPENAI_API_KEY=sk-your_openai_key_here
PINECONE_API_KEY=your_pinecone_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment
EOF
    
    log_info "Sample environment file created: .env.gcp.sample"
}

# Main execution
main() {
    log_info "Starting GCP Secret Manager setup for Briefly..."
    
    check_prerequisites
    enable_apis
    create_service_accounts
    create_secrets
    setup_cloudbuild_permissions
    setup_cloudrun_permissions
    create_sample_env
    
    log_info "Setup completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. Update secret values with real data using:"
    echo "   gcloud secrets versions add SECRET_NAME --data-file=path/to/secret/file"
    echo "2. Build and deploy using:"
    echo "   gcloud builds submit --config=cloudbuild.yaml"
    echo "3. Check the .env.gcp.sample file for reference values"
}

# Run main function
main "$@" 