#!/bin/bash
# Vespa Management Script - Consolidated from multiple scripts
# Manages Vespa container, deploys Briefly application, and manages Python services

set -e

# Configuration
VESPA_CONTAINER_NAME="vespa"
VESPA_HOSTNAME="vespa-container"
VESPA_IMAGE="vespaengine/vespa"
VESPA_PORTS=("8080:8080" "19092:19092")
VESPA_ENDPOINT="http://localhost:8080"



# App configuration
APP_PACKAGE_DIR="vespa"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Global variable for log tailing
LOG_TAIL_PID=""

# Cleanup function
cleanup() {
    if [[ -n "$LOG_TAIL_PID" ]]; then
        kill $LOG_TAIL_PID 2>/dev/null || true
        log_info "Stopped log monitoring"
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

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



# Check Vespa container health
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

# Check if Vespa application is deployed and responding
check_vespa_status() {
    log_info "Checking Vespa status..."
    
    # First check if container is running
    if ! check_vespa_container_health; then
        log_error "Vespa container is not running"
        return 1
    fi
    
    log_success "Vespa container is running"
    
    # Check if HTTP is responding (this will fail until app is deployed)
    if curl -s "$VESPA_ENDPOINT/" > /dev/null 2>&1; then
        log_success "Vespa HTTP server is responding (application deployed)"
        return 0
    else
        log_info "Vespa is running in config server mode (waiting for application deployment)"
        return 0
    fi
}

# Check Python service health
check_python_service_health() {
    local port=$1
    if curl -s "http://localhost:${port}/health" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Start Vespa container
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
            -e VESPA_IGNORE_NOT_ENOUGH_MEMORY=true \
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





# Stop Vespa Python services (legacy function, kept for compatibility)
stop_vespa_services() {
    log_info "Stopping Vespa Python services..."
    log_warning "Python services are not managed by this script"
}

# Create application package
create_app_package() {
    log_info "Creating Vespa application package..."
    
    cd "$REPO_ROOT"
    
    # Check if required files exist
    if [[ ! -f "$APP_PACKAGE_DIR/services.xml" ]] || \
       [[ ! -f "$APP_PACKAGE_DIR/hosts.xml" ]] || \
       [[ ! -d "$APP_PACKAGE_DIR/schemas" ]]; then
        log_error "Missing required Vespa configuration files"
        log_info "Required files:"
        log_info "  - $APP_PACKAGE_DIR/services.xml"
        log_info "  - $APP_PACKAGE_DIR/hosts.xml"
        log_info "  - $APP_PACKAGE_DIR/schemas/"
        return 1
    fi
    
    # Create package in a known location
    PACKAGE_PATH="/tmp/briefly-vespa-app.zip"
    
    # Clean up any existing package
    rm -f "$PACKAGE_PATH"
    
    # Create zip package directly from the vespa directory
    cd "$APP_PACKAGE_DIR"
    zip -r "$PACKAGE_PATH" . > /dev/null
    
    if [[ -f "$PACKAGE_PATH" ]]; then
        log_success "Application package created: $PACKAGE_PATH"
        printf "%s" "$PACKAGE_PATH"
    else
        log_error "Failed to create package"
        return 1
    fi
}

# Deploy application to Vespa
deploy_package() {
    local package_path="$1"
    
    log_info "Deploying Briefly application to Vespa..."
    log_info "Package path: $package_path"
    
    # Check if package exists
    if [[ ! -f "$package_path" ]]; then
        log_error "Package file does not exist: $package_path"
        return 1
    fi
    
    # Use config server workflow (prepare -> activate)
    log_info "Using config server workflow (prepare -> activate)..."
    
    # Start tailing logs in background to show deployment progress
    log_info "Starting real-time log monitoring..."
    docker logs "$VESPA_CONTAINER_NAME" --follow --tail 0 &
    LOG_TAIL_PID=$!
    
    # Copy package to container and deploy
    log_info "Copying package to Vespa container..."
    if docker cp "$package_path" "$VESPA_CONTAINER_NAME:/tmp/app-package.zip"; then
        log_success "Package copied successfully"
    else
        log_error "Failed to copy package to container"
        kill $LOG_TAIL_PID 2>/dev/null || true
        return 1
    fi
    
    log_info "Preparing application deployment..."
    local prepare_output
    prepare_output=$(docker exec "$VESPA_CONTAINER_NAME" vespa-deploy prepare /tmp/app-package.zip 2>&1)
    local prepare_exit_code=$?
    
    # Check if prepare succeeded
    if [[ $prepare_exit_code -eq 0 ]] && [[ "$prepare_output" != *"Usage:"* ]] && [[ "$prepare_output" != *"Available Commands:"* ]]; then
        log_success "Application prepared successfully"
    else
        log_error "Failed to prepare application"
        log_info "Prepare output: $prepare_output"
        kill $LOG_TAIL_PID 2>/dev/null || true
        return 1
    fi
    
    log_info "Activating application..."
    local activate_output
    activate_output=$(docker exec "$VESPA_CONTAINER_NAME" vespa-deploy activate 2>&1)
    local activate_exit_code=$?
    
    # Check if activate succeeded
    if [[ $activate_exit_code -eq 0 ]] && [[ "$activate_output" != *"Usage:"* ]] && [[ "$activate_output" != *"Available Commands:"* ]]; then
        log_success "Application activated successfully!"
        # Stop log tailing
        kill $LOG_TAIL_PID 2>/dev/null || true
        return 0
    else
        log_error "Failed to activate application"
        log_info "Activate output: $activate_output"
        # Stop log tailing
        kill $LOG_TAIL_PID 2>/dev/null || true
        return 1
    fi
}

# Wait for application to be ready
wait_for_app_ready() {
    log_info "Waiting for Briefly application to be ready..."
    
    local timeout=60
    local start_time=$(date +%s)
    
    # Start tailing logs in background
    log_info "Starting log monitoring..."
    docker logs "$VESPA_CONTAINER_NAME" --follow --tail 0 &
    local log_tail_pid=$!
    
    # Cleanup function to stop log tailing
    cleanup_logs() {
        if [[ -n "$log_tail_pid" ]]; then
            kill "$log_tail_pid" 2>/dev/null || true
        fi
    }
    
    # Set trap to cleanup on exit
    trap cleanup_logs EXIT
    
    while [[ $(($(date +%s) - start_time)) -lt $timeout ]]; do
        # Check if search endpoint is available
        if curl -s -X POST \
            -H "Content-Type: application/json" \
            -d '{"yql": "select * from briefly_document where true", "hits": 0}' \
            "$VESPA_ENDPOINT/search/" > /dev/null 2>&1; then
            log_success "Search endpoint is working!"
            cleanup_logs
            return 0
        fi
        
        log_info "Still waiting... ($(($(date +%s) - start_time))s elapsed"
        sleep 2
    done
    
    cleanup_logs
    log_error "Application did not become ready within $timeout seconds"
    return 1
}

# Test search endpoints
test_search_endpoints() {
    log_info "Testing Briefly search endpoints..."
    
    # Test basic search
    if curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"yql": "select * from briefly_document where true", "hits": 0}' \
        "$VESPA_ENDPOINT/search/" > /dev/null; then
        log_success "Search endpoint is working!"
        return 0
    else
        log_error "Search endpoint test failed"
        return 1
    fi
}

# Stop Vespa container only
stop_vespa_services() {
    log_info "Stopping Vespa container..."
    
    if docker ps --format "table {{.Names}}" | grep -q "^${VESPA_CONTAINER_NAME}$"; then
        log_info "Stopping Vespa container..."
        docker stop "${VESPA_CONTAINER_NAME}"
        log_success "Vespa container stopped"
    else
        log_warning "Vespa container is not running"
    fi
    
    log_success "Vespa container stopped"
}

# Cleanup Vespa
cleanup_vespa() {
    log_info "Cleaning up Vespa container..."
    
    if docker ps -a --format "table {{.Names}}" | grep -q "^${VESPA_CONTAINER_NAME}$"; then
        docker rm "${VESPA_CONTAINER_NAME}"
        log_success "Vespa container removed"
    else
        log_warning "Vespa container not found"
    fi
}

# Clear all data from Vespa
clear_vespa_data() {
    log_info "Clearing all data from Vespa..."
    
    # Check if Vespa is running
    if ! check_vespa_container_health; then
        log_error "Vespa container is not running. Start it first with: $0 --start"
        exit 1
    fi
    
    # Check if application is deployed
    if ! curl -s "$VESPA_ENDPOINT/" > /dev/null 2>&1; then
        log_error "Briefly application is not deployed. Deploy it first with: $0 --deploy"
        exit 1
    fi
    
    log_info "This will delete ALL documents from Vespa. Are you sure? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled"
        exit 0
    fi
    
    log_info "Clearing all documents from Vespa..."
    
    # Use Vespa's document API to clear all documents
    # First, get a list of all documents using a working query
    local search_response
    search_response=$(curl -s -X POST "$VESPA_ENDPOINT/search/" \
        -H "Content-Type: application/json" \
        -d '{"yql": "select * from briefly_document where user_id contains \"trybriefly@outlook.com\"", "hits": 200}')
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to query Vespa for documents"
        exit 1
    fi
    
    # Extract document IDs from the response
    local document_ids
    document_ids=$(echo "$search_response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    children = data.get('root', {}).get('children', [])
    for child in children:
        # Use the doc_id field and construct the full Vespa document ID
        doc_id = child.get('fields', {}).get('doc_id', '')
        if doc_id:
            # Construct full Vespa document ID: id:briefly:briefly_document::{doc_id}
            full_doc_id = f\"id:briefly:briefly_document::{doc_id}\"
            print(full_doc_id)
except Exception as e:
    print(f'Error parsing response: {e}', file=sys.stderr)
    sys.exit(1)
")
    
    if [[ -z "$document_ids" ]]; then
        log_info "No documents found in Vespa"
        return 0
    fi
    
    local deleted_count=0
    local error_count=0
    
    # Delete each document
    while IFS= read -r doc_id; do
        if [[ -n "$doc_id" ]]; then
            log_info "Deleting document: $doc_id"
            
            local delete_response
            delete_response=$(curl -s -X DELETE "$VESPA_ENDPOINT/document/v1/briefly/briefly_document/docid/$doc_id")
            
            if [[ $? -eq 0 ]] && [[ "$delete_response" == *'"pathId": "/document/v1/briefly/briefly_document/docid/'* ]]; then
                ((deleted_count++))
                log_success "Deleted: $doc_id"
            else
                ((error_count++))
                log_error "Failed to delete: $doc_id"
                log_info "Response: $delete_response"
            fi
        fi
    done <<< "$document_ids"
    
    log_success "Data clearing completed!"
    log_info "Documents deleted: $deleted_count"
    if [[ $error_count -gt 0 ]]; then
        log_warning "Errors encountered: $error_count"
    fi
    
    # Verify the data is cleared
    log_info "Verifying data is cleared..."
    local verify_response
    verify_response=$(curl -s -X POST "$VESPA_ENDPOINT/search/" \
        -H "Content-Type: application/json" \
        -d '{"yql": "select * from briefly_document where user_id contains \"trybriefly@outlook.com\"", "hits": 1}')
    
    local remaining_count
    remaining_count=$(echo "$verify_response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    total_count = data.get('root', {}).get('fields', {}).get('totalCount', 0)
    print(total_count)
except Exception as e:
    print('0')
")
    
    if [[ "$remaining_count" == "0" ]]; then
        log_success "✅ All data successfully cleared from Vespa"
    else
        log_warning "⚠️  Some data may remain. Total count: $remaining_count"
    fi
}

# Show status
show_status() {
    log_info "Vespa Services Status:"
    echo "  Container: ${VESPA_CONTAINER_NAME}"
    echo "  Image: ${VESPA_IMAGE}"
    echo "  Ports: ${VESPA_PORTS[*]}"
    echo "  Endpoint: ${VESPA_ENDPOINT}"
    
    if check_vespa_container_health; then
        log_success "Vespa Container: Running"
        echo ""
        log_info "Container Details:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "^${VESPA_CONTAINER_NAME}"
        
        # Check if application is deployed
        if curl -s "$VESPA_ENDPOINT/" > /dev/null 2>&1; then
            log_success "Briefly Application: Deployed ✅"
        else
            log_warning "Briefly Application: Not deployed"
        fi
        

    else
        log_error "Vespa Container: Not running"
    fi
    

}

# Deploy Briefly application
deploy_briefly() {
    log_info "🚀 Starting Briefly application deployment..."
    
    # Check prerequisites
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v zip &> /dev/null; then
        log_error "zip is required but not installed"
        exit 1
    fi
    
    # Ensure Vespa is running
    if ! check_vespa_status; then
        log_info "Starting Vespa container..."
        if ! start_vespa_container; then
            log_error "Failed to start Vespa container"
            exit 1
        fi
    fi
    
    # Create application package
    PACKAGE_PATH=$(create_app_package)
    if [[ $? -ne 0 ]] || [[ -z "$PACKAGE_PATH" ]]; then
        log_error "Failed to create application package"
        exit 1
    fi
    
    log_info "Package created at: $PACKAGE_PATH"
    
    # Deploy application
    if ! deploy_package "$PACKAGE_PATH"; then
        exit 1
    fi
    
    # Wait for application to be ready
    if ! wait_for_app_ready; then
        log_warning "Application deployed but not fully ready"
        log_info "You may need to wait a bit longer or check Vespa logs"
    fi
    
    # Test endpoints
    if test_search_endpoints; then
        log_success "🎉 Briefly application deployed successfully!"
        echo
        log_info "🔍 Search endpoints are now available:"
        log_info "   - Search: $VESPA_ENDPOINT/search/"
        log_info "   - Documents: $VESPA_ENDPOINT/document/v1/briefly/briefly_document/"
        log_info "   - Status: $VESPA_ENDPOINT/application/v2/status"
        echo
        log_info "🧪 You can now test the chat demo:"
        log_info "   python services/demos/vespa_chat.py"
    else
        log_error "❌ Failed to deploy Briefly application"
        exit 1
    fi
}

# Start Vespa container only
start_all() {
    log_info "Starting Vespa container..."
    
    # Start Vespa container
    if ! start_vespa_container; then
        log_error "Failed to start Vespa container"
        exit 1
    fi
    
    log_success "Vespa container started successfully!"
    show_status
}

# Main script logic
case "${1:-}" in
    --start)
        start_all
        ;;
    --deploy)
        deploy_briefly
        ;;
    --stop)
        stop_vespa_services
        ;;
    --cleanup)
        stop_vespa_services
        cleanup_vespa
        ;;
    --clear-data)
        clear_vespa_data
        ;;
    --status)
        show_status
        ;;
    --restart)
        log_info "Restarting Vespa container..."
        stop_vespa_services
        sleep 2
        start_all
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no args)  Start Vespa container if not running, health check"
        echo "  --start    Start Vespa container only"
        echo "  --deploy   Deploy the Briefly application to Vespa"
        echo "  --stop     Stop Vespa container only"
        echo "  --cleanup  Stop and remove the Vespa container"
        echo "  --clear-data Clear all data from Vespa (useful for testing)"
        echo "  --restart  Restart Vespa container only"
        echo "  --status   Show current status"
        echo "  --help     Show this help message"
        echo ""
        echo "Services:"
        echo "  Vespa Engine (Docker): ${VESPA_PORTS[*]}"
        echo "  Briefly Application: ${VESPA_ENDPOINT}"
        ;;
    *)
        # Default behavior: health check and start container if needed
        log_info "Checking Vespa container health..."
        
        if ! check_vespa_container_health; then
            log_info "Vespa container is not running"
            if ! start_vespa_container; then
                log_error "Failed to start Vespa container"
                exit 1
            fi
            log_success "Vespa container started successfully!"
        else
            log_success "Vespa container is already running and healthy!"
        fi
        
        show_status
        ;;
esac
