#!/bin/bash
# Redis Management Script
# Manages Redis container for local development

set -e

# Configuration
REDIS_CONTAINER_NAME="redis"
REDIS_HOSTNAME="redis-container"
REDIS_IMAGE="redis:7-alpine"
REDIS_PORT="6379"
REDIS_ENDPOINT="localhost:${REDIS_PORT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" >&2
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" >&2
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

# Check if Docker is running
check_docker_running() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        return 1
    fi
    return 0
}

# Check Redis container health
check_redis_container_health() {
    if docker ps --format "table {{.Names}}" | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        local container_info
        container_info=$(docker inspect --format='{{.State.Status}}' "${REDIS_CONTAINER_NAME}" 2>/dev/null)
        
        if [[ "$container_info" == "running" ]]; then
            local start_time
            start_time=$(docker inspect --format='{{.State.StartedAt}}' "${REDIS_CONTAINER_NAME}" 2>/dev/null)
            
            if [[ -n "$start_time" ]]; then
                return 0
            fi
        fi
    fi
    return 1
}

# Check if Redis is responding
check_redis_status() {
    log_info "Checking Redis status..."
    
    # First check if container is running
    if ! check_redis_container_health; then
        log_error "Redis container is not running"
        return 1
    fi
    
    log_success "Redis container is running"
    
    # Check if Redis is responding to ping
    if docker exec "${REDIS_CONTAINER_NAME}" redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is responding to ping (ready)"
        return 0
    else
        log_info "Redis container is running but not responding to ping yet"
        return 0
    fi
}

# Start Redis container
start_redis_container() {
    log_info "Starting Redis container..."
    
    if ! check_docker_running; then
        return 1
    fi
    
    if docker ps -a --format "table {{.Names}}" | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        if docker ps --format "table {{.Names}}" | grep -q "^${REDIS_CONTAINER_NAME}$"; then
            log_success "Redis container is already running"
            return 0
        else
            log_info "Starting existing Redis container..."
            docker start "${REDIS_CONTAINER_NAME}"
        fi
    else
        log_info "Creating new Redis container..."
        docker run -d \
            --name "${REDIS_CONTAINER_NAME}" \
            --hostname "${REDIS_HOSTNAME}" \
            -p "${REDIS_PORT}:6379" \
            "${REDIS_IMAGE}"
    fi
    
    log_info "Waiting for Redis container to be ready..."
    local attempts=0
    local max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        if check_redis_container_health; then
            # Wait a bit more for Redis to fully initialize
            sleep 2
            
            # Test Redis ping
            if docker exec "${REDIS_CONTAINER_NAME}" redis-cli ping > /dev/null 2>&1; then
                log_success "Redis container is ready and responding!"
                return 0
            fi
        fi
        attempts=$((attempts + 1))
        sleep 2
    done
    
    log_error "Redis container failed to start within ${max_attempts} seconds"
    return 1
}

# Stop Redis container
stop_redis_container() {
    log_info "Stopping Redis container..."
    
    if docker ps --format "table {{.Names}}" | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        docker stop "${REDIS_CONTAINER_NAME}"
        log_success "Redis container stopped"
    else
        log_warning "Redis container is not running"
    fi
}

# Cleanup Redis container
cleanup_redis() {
    log_info "Cleaning up Redis container..."
    
    if docker ps -a --format "table {{.Names}}" | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        docker rm "${REDIS_CONTAINER_NAME}"
        log_success "Redis container removed"
    else
        log_warning "Redis container not found"
    fi
}

# Test Redis connection
test_redis_connection() {
    log_info "Testing Redis connection..."
    
    if docker exec "${REDIS_CONTAINER_NAME}" redis-cli ping | grep -q "PONG"; then
        log_success "Redis connection test successful!"
        return 0
    else
        log_error "Redis connection test failed"
        return 1
    fi
}

# Show status
show_status() {
    log_info "Redis Services Status:"
    echo "  Container: ${REDIS_CONTAINER_NAME}"
    echo "  Image: ${REDIS_IMAGE}"
    echo "  Port: ${REDIS_PORT}"
    echo "  Endpoint: ${REDIS_ENDPOINT}"
    
    if check_redis_container_health; then
        log_success "Redis Container: Running"
        echo ""
        log_info "Container Details:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "^${REDIS_CONTAINER_NAME}"
        
        # Test Redis connection
        if docker exec "${REDIS_CONTAINER_NAME}" redis-cli ping | grep -q "PONG"; then
            log_success "Redis Connection: Responding ✅"
        else
            log_warning "Redis Connection: Not responding"
        fi
    else
        log_error "Redis Container: Not running"
    fi
}

# Start Redis (container only)
start_all() {
    log_info "Starting Redis container..."
    
    # Start Redis container
    if ! start_redis_container; then
        log_error "Failed to start Redis container"
        exit 1
    fi
    
    log_success "Redis container started successfully!"
    show_status
}

# Main script logic
case "${1:-}" in
    --start)
        start_all
        ;;
    --deploy)
        log_info "Redis does not require application deployment"
        log_info "Starting Redis container if needed..."
        start_all
        ;;
    --stop)
        stop_redis_container
        ;;
    --cleanup)
        stop_redis_container
        cleanup_redis
        ;;
    --test)
        if check_redis_container_health; then
            test_redis_connection
        else
            log_error "Redis container is not running. Start it first with: $0 --start"
            exit 1
        fi
        ;;
    --status)
        show_status
        ;;
    --restart)
        log_info "Restarting Redis container..."
        stop_redis_container
        sleep 2
        start_all
        ;;
    --auto)
        # Explicit auto mode: start container if needed, then show status
        log_info "🚀 Redis Management: Starting container and checking status..."
        
        # Start Redis container if not running
        if ! check_redis_container_health; then
            log_info "Redis container is not running, starting it..."
            if ! start_redis_container; then
                log_error "Failed to start Redis container"
                exit 1
            fi
            log_success "Redis container started successfully!"
        else
            log_success "Redis container is already running and healthy!"
        fi
        
        # Show final status
        echo
        log_info "📊 Final Status Check:"
        show_status
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no args)  Start Redis container if not running, then show status"
        echo "  --auto     Same as no args: start container, then show status"
        echo "  --start    Start Redis container only"
        echo "  --deploy   Start Redis container (no deployment needed)"
        echo "  --stop     Stop Redis container only"
        echo "  --cleanup  Stop and remove the Redis container"
        echo "  --test     Test Redis connection"
        echo "  --restart  Restart Redis container only"
        echo "  --status   Show current status"
        echo "  --help     Show this help message"
        echo ""
        echo "Services:"
        echo "  Redis Engine (Docker): ${REDIS_PORT}"
        echo "  Redis Endpoint: ${REDIS_ENDPOINT}"
        ;;
    *)
        # Default behavior: start container if needed, then show status
        log_info "🚀 Redis Management: Starting container and checking status..."
        
        # Start Redis container if not running
        if ! check_redis_container_health; then
            log_info "Redis container is not running, starting it..."
            if ! start_redis_container; then
                log_error "Failed to start Redis container"
                exit 1
            fi
            log_success "Redis container started successfully!"
        else
            log_success "Redis container is already running and healthy!"
        fi
        
        # Show final status
        echo
        log_info "📊 Final Status Check:"
        show_status
        ;;
esac
