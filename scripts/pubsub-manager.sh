#!/bin/bash
# Unified PubSub Management Script
# Handles both local emulator and GCP production setup

set -e

# Configuration
PROJECT_ID="${PUBSUB_PROJECT_ID:-briefly-dev}"
EMULATOR_HOST="${PUBSUB_EMULATOR_HOST:-localhost:8085}"
EMULATOR_PORT="8085"
CONTAINER_NAME="pubsub-emulator"
IMAGE="gcr.io/google.com/cloudsdktool/google-cloud-cli:latest"

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

check_docker_running() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        return 1
    fi
    return 0
}

check_health() {
    if curl -s "http://${EMULATOR_HOST}" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

start_emulator() {
    log_info "Starting Pub/Sub emulator..."
    
    # Check Docker first
    if ! check_docker_running; then
        return 1
    fi
    
    # Check if container already exists
    if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        # Container exists, check if running
        if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
            log_success "Container ${CONTAINER_NAME} is already running"
            return 0
        else
            log_info "Container ${CONTAINER_NAME} exists but not running, starting it..."
            docker start ${CONTAINER_NAME}
        fi
    else
        log_info "Creating new Pub/Sub emulator container..."
        docker run -d \
            --name ${CONTAINER_NAME} \
            -p ${EMULATOR_PORT}:8085 \
            -e PUBSUB_PROJECT_ID=${PROJECT_ID} \
            ${IMAGE} \
            gcloud beta emulators pubsub start \
            --host-port=0.0.0.0:8085 \
            --project=${PROJECT_ID}
    fi
    
    # Wait for emulator to be ready
    log_info "Waiting for emulator to be ready..."
    local attempts=0
    local max_attempts=180  # 3 minutes for Pub/Sub emulator (large image)
    
    while [ $attempts -lt $max_attempts ]; do
        if check_health; then
            log_success "Pub/Sub emulator is ready!"
            return 0
        fi
        attempts=$((attempts + 1))
        sleep 2
        
        # Show progress every 10 seconds
        if [ $((attempts % 5)) -eq 0 ]; then
            log_info "Still waiting... (${attempts}s elapsed)"
        fi
    done
    
    log_error "Pub/Sub emulator failed to start within ${max_attempts} seconds"
    return 1
}

stop_emulator() {
    log_info "Stopping Pub/Sub emulator..."
    
    if docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        docker stop ${CONTAINER_NAME}
        log_success "Pub/Sub emulator stopped"
    else
        log_warning "Pub/Sub emulator is not running"
    fi
}

cleanup_emulator() {
    log_info "Cleaning up Pub/Sub emulator container..."
    
    if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        docker rm ${CONTAINER_NAME}
        log_success "Pub/Sub emulator container removed"
    else
        log_warning "Pub/Sub emulator container not found"
    fi
}

create_topics() {
    log_info "Creating Pub/Sub topics..."
    
    # Wait a bit for emulator to be fully ready
    sleep 2
    
    # Create required topics
    local topics=("email-backfill" "calendar-updates" "contact-updates")
    
    for topic in "${topics[@]}"; do
        log_info "Creating topic: ${topic}"
        
        # Use gcloud to create topic (if available)
        if command -v gcloud >/dev/null 2>&1; then
            # Set emulator environment
            export PUBSUB_EMULATOR_HOST=${EMULATOR_HOST}
            
            if gcloud pubsub topics create ${topic} --project=${PROJECT_ID} >/dev/null 2>&1; then
                log_success "Created topic: ${topic}"
            else
                log_warning "Topic ${topic} may already exist or failed to create"
            fi
        else
            # Fallback to REST API if gcloud not available
            log_info "gcloud CLI not available, using REST API for topic: ${topic}"
            local url="http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/topics/${topic}"
            
            if curl -s -X PUT -H 'Content-Type: application/json' "${url}" >/dev/null 2>&1; then
                log_success "Created topic: ${topic}"
            else
                log_warning "Topic ${topic} may already exist or failed to create"
            fi
        fi
    done
    
    log_success "Pub/Sub topics creation completed"
}

create_subscriptions() {
    log_info "Creating Pub/Sub subscriptions..."
    
    # Create router subscriptions
    log_info "Creating router subscriptions..."
    local router_subs=(
        "email-router-subscription:email-backfill"
        "calendar-router-subscription:calendar-updates"
        "contact-router-subscription:contact-updates"
    )
    
    for sub_info in "${router_subs[@]}"; do
        IFS=':' read -r sub_name topic_name <<< "${sub_info}"
        log_info "Creating subscription: ${sub_name}"
        
        if command -v gcloud >/dev/null 2>&1; then
            export PUBSUB_EMULATOR_HOST=${EMULATOR_HOST}
            if gcloud pubsub subscriptions create ${sub_name} --topic=${topic_name} --project=${PROJECT_ID} >/dev/null 2>&1; then
                log_success "Created subscription: ${sub_name}"
            else
                log_warning "Subscription ${sub_name} may already exist"
            fi
        else
            # Fallback to REST API
            local url="http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions/${sub_name}"
            local data="{\"topic\": \"projects/${PROJECT_ID}/topics/${topic_name}\"}"
            
            if curl -s -X PUT -H 'Content-Type: application/json' "${url}" -d "${data}" >/dev/null 2>&1; then
                log_success "Created subscription: ${sub_name}"
            else
                log_warning "Subscription ${sub_name} may already exist"
            fi
        fi
    done
    
    # Create vespa-loader subscriptions
    log_info "Creating vespa-loader subscriptions..."
    local vespa_subs=(
        "vespa-loader-email-backfill:email-backfill"
        "vespa-loader-calendar-updates:calendar-updates"
        "vespa-loader-contact-updates:contact-updates"
    )
    
    for sub_info in "${vespa_subs[@]}"; do
        IFS=':' read -r sub_name topic_name <<< "${sub_info}"
        log_info "Creating subscription: ${sub_name}"
        
        if command -v gcloud >/dev/null 2>&1; then
            export PUBSUB_EMULATOR_HOST=${EMULATOR_HOST}
            if gcloud pubsub subscriptions create ${sub_name} --topic=${topic_name} --project=${PROJECT_ID} >/dev/null 2>&1; then
                log_success "Created subscription: ${sub_name}"
            else
                log_warning "Subscription ${sub_name} may already exist"
            fi
        else
            # Fallback to REST API
            local url="http://${EMULATOR_HOST}/v1/projects/${PROJECT_ID}/subscriptions/${sub_name}"
            local data="{\"topic\": \"projects/${PROJECT_ID}/topics/${topic_name}\"}"
            
            if curl -s -X PUT -H 'Content-Type: application/json' "${url}" -d "${data}" >/dev/null 2>&1; then
                log_success "Created subscription: ${sub_name}"
            else
                log_warning "Subscription ${sub_name} may already exist"
            fi
        fi
    done
    
    log_success "Pub/Sub subscriptions creation completed"
}

setup_topics_and_subscriptions() {
    log_info "Setting up Pub/Sub topics and subscriptions..."
    create_topics
    create_subscriptions
    log_success "Pub/Sub setup completed successfully!"
}

show_status() {
    log_info "Pub/Sub Emulator Status:"
    echo "  Project ID: ${PROJECT_ID}"
    echo "  Host: ${EMULATOR_HOST}"
    echo "  Container: ${CONTAINER_NAME}"
    
    if check_health; then
        log_success "Status: Running"
        
        # Show container info
        if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "^${CONTAINER_NAME}"; then
            echo ""
            log_info "Container Details:"
            docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "^${CONTAINER_NAME}"
        fi
        
        # Show topics if gcloud is available
        if command -v gcloud >/dev/null 2>&1; then
            echo ""
            log_info "Topics:"
            export PUBSUB_EMULATOR_HOST=${EMULATOR_HOST}
            gcloud pubsub topics list --project=${PROJECT_ID} 2>/dev/null || log_warning "Could not list topics"
            
            echo ""
            log_info "Subscriptions:"
            gcloud pubsub subscriptions list --project=${PROJECT_ID} 2>/dev/null || log_warning "Could not list subscriptions"
        fi
    else
        log_error "Status: Not running"
    fi
}

show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  (no args)  Start emulator if not running, health check"
    echo "  start      Start emulator and setup topics/subscriptions"
    echo "  stop       Stop the emulator"
    echo "  cleanup    Stop and remove the emulator container"
    echo "  status     Show current status"
    echo "  setup      Setup topics and subscriptions only"
    echo "  --help     Show this help message"
    echo ""
    echo "Environment:"
    echo "  PUBSUB_PROJECT_ID: ${PROJECT_ID}"
    echo "  PUBSUB_EMULATOR_HOST: ${EMULATOR_HOST}"
    echo "  CONTAINER_NAME: ${CONTAINER_NAME}"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start emulator if needed"
    echo "  $0 start             # Start emulator and setup everything"
    echo "  $0 setup             # Setup topics/subscriptions only"
    echo "  $0 status            # Show current status"
    echo "  $0 stop              # Stop emulator"
    echo "  $0 cleanup           # Remove emulator container"
}

# Main script logic
case "${1:-}" in
    start|--start)
        start_emulator
        if [ $? -eq 0 ]; then
            setup_topics_and_subscriptions
            show_status
        fi
        ;;
    stop|--stop)
        stop_emulator
        ;;
    cleanup|--cleanup)
        stop_emulator
        cleanup_emulator
        ;;
    status|--status)
        show_status
        ;;
    setup|--setup)
        if check_health; then
            setup_topics_and_subscriptions
        else
            log_error "Emulator is not running. Please start it first with: $0 start"
            exit 1
        fi
        ;;
    --help|-h|help)
        show_help
        ;;
    *)
        # Default behavior: health check and start if needed
        if check_health; then
            log_success "Pub/Sub emulator is already running"
            show_status
        else
            log_info "Pub/Sub emulator is not running"
            start_emulator
            if [ $? -eq 0 ]; then
                setup_topics_and_subscriptions
                show_status
            fi
        fi
        ;;
esac
