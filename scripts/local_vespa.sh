#!/bin/bash
# Local Vespa Services Management Script

set -e

# Configuration
VESPA_CONTAINER_NAME="vespa"
VESPA_HOSTNAME="vespa-container"
VESPA_IMAGE="vespaengine/vespa"
VESPA_PORTS=("8080:8080" "19092:19092")

# Service ports
VESPA_LOADER_PORT="9001"
VESPA_QUERY_PORT="9002"

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

check_vespa_container_health() {
    if docker ps --format "table {{.Names}}" | grep -q "^${VESPA_CONTAINER_NAME}$"; then
        local container_info
        container_info=$(docker inspect --format='{{.State.Status}}' "${VESPA_CONTAINER_NAME}" 2>/dev/null)
        
        if [[ "$container_info" == "running" ]]; then
            local start_time
            start_time=$(docker inspect --format='{{.State.StartedAt}}' "${VESPA_CONTAINER_NAME}" 2>/dev/null)
            
            if [[ -n "$start_time" ]]; then
                return 0
            fi
        fi
    fi
    return 1
}

check_python_service_health() {
    local port=$1
    if curl -s "http://localhost:${port}/health" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

start_vespa_container() {
    log_info "Starting Vespa container..."
    
    if ! check_docker_running; then
        return 1
    fi
    
    if docker ps -a --format "table {{.Names}}" | grep -q "^${VESPA_CONTAINER_NAME}$"; then
        if docker ps --format "table {{.Names}}" | grep -q "^${VESPA_CONTAINER_NAME}$"; then
            log_success "Vespa container is already running"
            return 0
        else
            log_info "Starting existing Vespa container..."
            docker start "${VESPA_CONTAINER_NAME}"
        fi
    else
        log_info "Creating new Vespa container..."
        docker run -d \
            --name "${VESPA_CONTAINER_NAME}" \
            --hostname "${VESPA_HOSTNAME}" \
            -p "${VESPA_PORTS[0]}" \
            -p "${VESPA_PORTS[1]}" \
            "${VESPA_IMAGE}"
    fi
    
    log_info "Waiting for Vespa container to be ready..."
    local attempts=0
    local max_attempts=60
    
    while [ $attempts -lt $max_attempts ]; do
        if check_vespa_container_health; then
            log_success "Vespa container is ready!"
            return 0
        fi
        attempts=$((attempts + 1))
        sleep 2
    done
    
    log_error "Vespa container failed to start within ${max_attempts} seconds"
    return 1
}

start_python_service() {
    local service_name=$1
    local port=$2
    local module=$3
    local directory=$4
    
    log_info "Starting ${service_name} on port ${port}..."
    
    if check_python_service_health "$port" "$service_name"; then
        log_success "${service_name} is already running on port ${port}"
        return 0
    fi
    
    local service_dir
    service_dir=$(pwd)/services/${directory}
    
    if [[ ! -d "$service_dir" ]]; then
        log_error "Service directory not found: ${service_dir}"
        return 1
    fi
    
    cd "$service_dir"
    nohup python -m uvicorn "${module}" --host 0.0.0.0 --port "${port}" --reload >/dev/null 2>&1 &
    local pid=$!
    
    sleep 3
    
    if check_python_service_health "$port" "$service_name"; then
        log_success "${service_name} started successfully (PID: ${pid})"
        return 0
    else
        log_error "${service_name} failed to start"
        return 1
    fi
}

stop_vespa_services() {
    log_info "Stopping Vespa services..."
    
    for port in "$VESPA_LOADER_PORT" "$VESPA_QUERY_PORT"; do
        local pid
        pid=$(lsof -ti:"$port" 2>/dev/null || true)
        if [[ -n "$pid" ]]; then
            log_info "Stopping service on port ${port} (PID: ${pid})"
            kill "$pid" 2>/dev/null || true
        fi
    done
    
    if docker ps --format "table {{.Names}}" | grep -q "^${VESPA_CONTAINER_NAME}$"; then
        log_info "Stopping Vespa container..."
        docker stop "${VESPA_CONTAINER_NAME}"
        log_success "Vespa container stopped"
    else
        log_warning "Vespa container is not running"
    fi
    
    log_success "All Vespa services stopped"
}

cleanup_vespa() {
    log_info "Cleaning up Vespa container..."
    
    if docker ps -a --format "table {{.Names}}" | grep -q "^${VESPA_CONTAINER_NAME}$"; then
        docker rm "${VESPA_CONTAINER_NAME}"
        log_success "Vespa container removed"
    else
        log_warning "Vespa container not found"
    fi
}

show_status() {
    log_info "Vespa Services Status:"
    echo "  Container: ${VESPA_CONTAINER_NAME}"
    echo "  Image: ${VESPA_IMAGE}"
    echo "  Ports: ${VESPA_PORTS[*]}"
    
    if check_vespa_container_health; then
        log_success "Vespa Container: Running"
        echo ""
        log_info "Container Details:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "^${VESPA_CONTAINER_NAME}"
    else
        log_error "Vespa Container: Not running"
    fi
    
    echo ""
    log_info "Python Services:"
    
    if check_python_service_health "$VESPA_LOADER_PORT" "Vespa Loader"; then
        log_success "  Vespa Loader Service: http://localhost:${VESPA_LOADER_PORT} ✅"
    fi
    
    if check_python_service_health "$VESPA_QUERY_PORT" "Vespa Query"; then
        log_success "  Vespa Query Service: http://localhost:${VESPA_QUERY_PORT} ✅"
    fi
}

# Main script logic
case "${1:-}" in
    --stop)
        stop_vespa_services
        ;;
    --cleanup)
        stop_vespa_services
        cleanup_vespa
        ;;
    --status)
        show_status
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no args)  Start Vespa services if not running, health check"
        echo "  --stop     Stop all Vespa services"
        echo "  --cleanup  Stop and remove the Vespa container"
        echo "  --status   Show current status"
        echo "  --help     Show this help message"
        echo ""
        echo "Services:"
        echo "  Vespa Engine (Docker): ${VESPA_PORTS[*]}"
        echo "  Vespa Loader Service: http://localhost:${VESPA_LOADER_PORT}"
        echo "  Vespa Query Service: http://localhost:${VESPA_QUERY_PORT}"
        ;;
    *)
        # Default behavior: health check and start if needed
        log_info "Checking Vespa services health..."
        
        local all_healthy=true
        
        if ! check_vespa_container_health; then
            log_info "Vespa container is not running"
            if ! start_vespa_container; then
                log_error "Failed to start Vespa container"
                exit 1
            fi
            all_healthy=false
        fi
        
        if ! check_python_service_health "$VESPA_LOADER_PORT" "Vespa Loader"; then
            log_info "Vespa Loader Service is not running"
            if ! start_python_service "Vespa Loader" "$VESPA_LOADER_PORT" "main:app" "vespa_loader"; then
                log_error "Failed to start Vespa Loader Service"
                exit 1
            fi
            all_healthy=false
        fi
        
        if ! check_python_service_health "$VESPA_QUERY_PORT" "Vespa Query"; then
            log_info "Vespa Query Service is not running"
            if ! start_python_service "Vespa Query" "$VESPA_QUERY_PORT" "main:app" "vespa_query"; then
                log_error "Failed to start Vespa Query Service"
                exit 1
            fi
            all_healthy=false
        fi
        
        if [[ "$all_healthy" == true ]]; then
            log_success "All Vespa services are already running and healthy!"
        else
            log_success "Vespa services started successfully!"
        fi
        
        show_status
        ;;
esac
