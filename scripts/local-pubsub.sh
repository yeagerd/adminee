#!/bin/bash
# Local Pub/Sub Emulator Management Script

set -e

# Configuration
PROJECT_ID="briefly-dev"
EMULATOR_HOST="localhost:8085"
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

setup_topics() {
    log_info "Setting up Pub/Sub topics..."
    
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
            log_warning "gcloud CLI not available, topic ${topic} may need manual creation"
        fi
    done
    
    log_success "Pub/Sub topics setup completed"
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
        fi
    else
        log_error "Status: Not running"
    fi
}

# Main script logic
case "${1:-}" in
    --stop)
        stop_emulator
        ;;
    --cleanup)
        stop_emulator
        cleanup_emulator
        ;;
    --status)
        show_status
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no args)  Start emulator if not running, health check"
        echo "  --stop     Stop the emulator"
        echo "  --cleanup  Stop and remove the emulator container"
        echo "  --status   Show current status"
        echo "  --help     Show this help message"
        echo ""
        echo "Environment:"
        echo "  PROJECT_ID: ${PROJECT_ID}"
        echo "  EMULATOR_HOST: ${EMULATOR_HOST}"
        echo "  CONTAINER_NAME: ${CONTAINER_NAME}"
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
                setup_topics
                show_status
            fi
        fi
        ;;
esac
