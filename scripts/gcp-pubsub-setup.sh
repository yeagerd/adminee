#!/bin/bash
# GCP PubSub Production Setup Script
# Use this when deploying to GCP (not for local development)

set -e

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT_ID:-briefly-prod}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_gcloud() {
    if ! command -v gcloud >/dev/null 2>&1; then
        log_error "gcloud CLI is not installed or not in PATH"
        log_error "Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
        return 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud"
        log_error "Please run: gcloud auth login"
        return 1
    fi
    
    # Check if project is set
    if [ -z "$PROJECT_ID" ]; then
        log_error "GOOGLE_CLOUD_PROJECT_ID environment variable not set"
        log_error "Please set it or use --project flag"
        return 1
    fi
    
    return 0
}

create_topics() {
    log_info "Creating Pub/Sub topics..."
    
    local topics=(
        # Core data types
        "emails"
        "calendars" 
        # Office document types
        "word_documents"
        "word_fragments"
        "sheet_documents"
        "sheet_fragments"
        "presentation_documents"
        "presentation_fragments"
        "task_documents"
        # Todo types
        "todos"
        # Internal tool types
        "llm_chats"
        "shipment_events"
        "meeting_polls"
        "bookings"
    )
    
    for topic in "${topics[@]}"; do
        log_info "Creating topic: ${topic}"
        if gcloud pubsub topics create ${topic} --project=${PROJECT_ID} --quiet 2>/dev/null; then
            log_success "Created topic: ${topic}"
        else
            log_warning "Topic ${topic} may already exist"
        fi
    done
    
    log_success "All topics created successfully"
}

create_subscriptions() {
    log_info "Creating Pub/Sub subscriptions..."
    
    # Create router subscriptions
    log_info "Creating router subscriptions..."
    local router_subs=(
        "email-router-subscription:emails"
        "calendar-router-subscription:calendars"
    )
    
    for sub_info in "${router_subs[@]}"; do
        IFS=':' read -r sub_name topic_name <<< "${sub_info}"
        log_info "Creating subscription: ${sub_name}"
        
        if gcloud pubsub subscriptions create ${sub_name} --topic=${topic_name} --project=${PROJECT_ID} --quiet 2>/dev/null; then
            log_success "Created subscription: ${sub_name}"
        else
            log_warning "Subscription ${sub_name} may already exist"
        fi
    done
    
    # Create vespa-loader subscriptions
    log_info "Creating vespa-loader subscriptions..."
    local vespa_subs=(
        "vespa-loader-emails:emails"
        "vespa-loader-calendars:calendars"
    )
    
    for sub_info in "${vespa_subs[@]}"; do
        IFS=':' read -r sub_name topic_name <<< "${sub_info}"
        log_info "Creating subscription: ${sub_name}"
        
        if gcloud pubsub subscriptions create ${sub_name} --topic=${topic_name} --project=${PROJECT_ID} --quiet 2>/dev/null; then
            log_success "Created subscription: ${sub_name}"
        else
            log_warning "Subscription ${sub_name} may already exist"
        fi
    done
    
    log_success "All subscriptions created successfully"
}

cleanup_topics() {
    log_info "Cleaning up Pub/Sub topics..."
    
    local topics=(
        # Core data types
        "emails"
        "calendars" 
        # Office document types
        "word_documents"
        "word_fragments"
        "sheet_documents"
        "sheet_fragments"
        "presentation_documents"
        "presentation_fragments"
        "task_documents"
        # Todo types
        "todos"
        # Internal tool types
        "llm_chats"
        "shipment_events"
        "meeting_polls"
        "bookings"
    )
    
    for topic in "${topics[@]}"; do
        log_info "Deleting topic: ${topic}"
        if gcloud pubsub topics delete ${topic} --project=${PROJECT_ID} --quiet 2>/dev/null; then
            log_success "Deleted topic: ${topic}"
        else
            log_warning "Topic ${topic} may not exist or failed to delete"
        fi
    done
    
    log_success "Topics cleanup completed"
}

cleanup_subscriptions() {
    log_info "Cleaning up Pub/Sub subscriptions..."
    
    local subs=(
        "email-router-subscription"
        "calendar-router-subscription"
        "vespa-loader-emails"
        "vespa-loader-calendars"
    )
    
    for sub in "${subs[@]}"; do
        log_info "Deleting subscription: ${sub}"
        if gcloud pubsub subscriptions delete ${sub} --project=${PROJECT_ID} --quiet 2>/dev/null; then
            log_success "Deleted subscription: ${sub}"
        else
            log_warning "Subscription ${sub} may not exist or failed to delete"
        fi
    done
    
    log_success "Subscriptions cleanup completed"
}

list_topics_and_subscriptions() {
    log_info "Listing Pub/Sub resources..."
    
    echo ""
    log_info "Topics:"
    gcloud pubsub topics list --project=${PROJECT_ID} --format="table(name,messageRetentionDuration)" 2>/dev/null || log_warning "Could not list topics"
    
    echo ""
    log_info "Subscriptions:"
    gcloud pubsub subscriptions list --project=${PROJECT_ID} --format="table(name,topic,ackDeadlineSeconds)" 2>/dev/null || log_warning "Could not list subscriptions"
}

setup_all() {
    log_info "Setting up complete Pub/Sub infrastructure..."
    
    if ! check_gcloud; then
        exit 1
    fi
    
    create_topics
    create_subscriptions
    list_topics_and_subscriptions
    
    log_success "🎉 Pub/Sub setup completed successfully!"
    log_info "Your services should now be able to publish and consume messages."
}

cleanup_all() {
    log_warning "⚠️  This will delete ALL topics and subscriptions!"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up Pub/Sub infrastructure..."
        
        if ! check_gcloud; then
            exit 1
        fi
        
        cleanup_subscriptions
        cleanup_topics
        
        log_success "Cleanup completed successfully!"
    else
        log_info "Cleanup cancelled."
    fi
}

show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  create      Create all topics and subscriptions"
    echo "  cleanup     Delete all topics and subscriptions"
    echo "  list        List all topics and subscriptions"
    echo "  --help      Show this help message"
    echo ""
    echo "Environment:"
    echo "  GOOGLE_CLOUD_PROJECT_ID: ${PROJECT_ID}"
    echo ""
    echo "Examples:"
    echo "  $0 create             # Create all topics and subscriptions"
    echo "  $0 cleanup            # Delete all topics and subscriptions"
    echo "  $0 list               # List all resources"
    echo ""
    echo "Prerequisites:"
    echo "  - gcloud CLI installed and authenticated"
    echo "  - GOOGLE_CLOUD_PROJECT_ID environment variable set"
    echo "  - Appropriate permissions on the GCP project"
}

# Main script logic
case "${1:-}" in
    create|--create)
        setup_all
        ;;
    cleanup|--cleanup)
        cleanup_all
        ;;
    list|--list)
        if ! check_gcloud; then
            exit 1
        fi
        list_topics_and_subscriptions
        ;;
    --help|-h|help)
        show_help
        ;;
    *)
        log_error "Unknown option: ${1:-}"
        echo ""
        show_help
        exit 1
        ;;
esac
