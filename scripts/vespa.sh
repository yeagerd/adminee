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

# Helper function to convert email to internal user ID
resolve_email_to_user_id() {
    local email="$1"
    local user_service_url="http://localhost:8001"
    
    log_info "Resolving email $email to internal user ID..."
    
    # Call the user service to get the internal user ID
    local response
    response=$(curl -s "$user_service_url/v1/internal/users/exists?email=$email")
    
    if [[ $? -eq 0 && "$response" != *'"message"'* ]]; then
        # Extract user ID from response
        local user_id
        user_id=$(echo "$response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    user_id = data.get('user_id', '')
    print(user_id)
except Exception as e:
    print('')
")
        
        if [[ -n "$user_id" ]]; then
            log_success "Resolved email $email to user ID: $user_id"
            echo "$user_id"
            return 0
        fi
    fi
    
    log_error "Failed to resolve email $email to user ID"
    return 1
}

# Get all Vespa group IDs (user IDs) that have documents
get_vespa_group_ids() {
    log_info "Discovering all Vespa group IDs with documents..."
    
    # For now, use the known group ID since the visiting API approach isn't working
    # In the future, we could implement a more sophisticated discovery mechanism
    local known_group_id="AAAAAAAAAAAAAAAAAAAAAG_WiRzTkk4vuAr97CA2Dc4"
    
    # Verify this group actually has documents
    local search_response
    search_response=$(curl -s -X POST "$VESPA_ENDPOINT/search/" \
        -H "Content-Type: application/json" \
        -d "{\"yql\": \"select * from briefly_document where true\", \"hits\": 1, \"streaming.groupname\": \"$known_group_id\"}")
    
    local document_count
    document_count=$(echo "$search_response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    total_count = data.get('root', {}).get('fields', {}).get('totalCount', 0)
    print(total_count)
except Exception as e:
    print('0')
")
    
    if [[ "$document_count" != "0" ]]; then
        log_info "Found group ID with $document_count documents: $known_group_id"
        echo "$known_group_id"
        return 0
    else
        log_info "No documents found for known group ID: $known_group_id"
        return 1
    fi
}

# Helper function to clear data for a specific group ID
clear_vespa_data_for_group_id() {
    local group_id="$1"
    local force_flag="$2"
    
    log_info "Clearing all documents from Vespa for group ID: $group_id..."
    
    # For streaming mode, use Vespa's visiting API to clear all documents for the user group
    log_info "Using Vespa visiting API to clear all documents for user group: $group_id"
    
    # Use the visiting API to delete all documents in the group
    # The selection and cluster parameters are required for visiting API deletions
    local visit_response
    visit_response=$(curl -s -X DELETE "$VESPA_ENDPOINT/document/v1/briefly/briefly_document/group/$group_id/?selection=true&cluster=briefly")
    
    if [[ $? -eq 0 ]]; then
        # Check if the response contains an error message
        if [[ "$visit_response" == *'"message"'* ]]; then
            log_error "Failed to clear documents for user group: $group_id"
            log_error "Vespa returned an error: $visit_response"
            return 1
        else
            log_success "Successfully cleared all documents for user group: $group_id"
            log_info "Response: $visit_response"
            return 0
        fi
    else
        log_error "Failed to clear documents for user group: $group_id"
        log_error "HTTP request failed with response: $visit_response"
        return 1
    fi
}

# Clear all data from Vespa
clear_vespa_data() {
    local user_input="trybriefly@outlook.com"  # Default user input (email or ID)
    local force_flag=false
    local user_id=""
    
    # Parse arguments to find user input and --force flag
    for arg in "$@"; do
        if [[ "$arg" == "--force" ]]; then
            force_flag=true
        elif [[ "$arg" != "--clear-data" && "$arg" != "--force" ]]; then
            # This is the user input (email or ID)
            user_input="$arg"
        fi
    done
    
    log_info "Input provided: $user_input"
    
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
    
    # Check if --all-users flag is present
    local all_users_flag=false
    for arg in "$@"; do
        if [[ "$arg" == "--all-users" ]]; then
            all_users_flag=true
            break
        fi
    done
    
    if [[ "$all_users_flag" == true ]]; then
        # Clear data for all discovered users
        log_info "All-users flag detected - discovering and clearing all group IDs..."
        
        local group_ids
        group_ids=($(get_vespa_group_ids))
        
        if [[ $? -ne 0 ]]; then
            log_info "No group IDs found in Vespa"
            return 0
        fi
        
        log_info "Found ${#group_ids[@]} group IDs to clear:"
        for group_id in "${group_ids[@]}"; do
            log_info "  - $group_id"
        done
        
        # Clear data for each group ID
        for group_id in "${group_ids[@]}"; do
            log_info "Clearing data for group ID: $group_id"
            clear_vespa_data_for_group_id "$group_id" "$force_flag"
        done
        
        log_success "Data clearing completed for all ${#group_ids[@]} group IDs!"
        return 0
    else
        # Single user operation - resolve email to user ID
        local user_id=""
        
        if [[ "$user_input" == *"@"* ]]; then
            # This looks like an email, try to resolve to user ID
            log_info "Email provided, resolving to user ID..."
            user_id=$(resolve_email_to_user_id "$user_input")
            if [[ $? -ne 0 ]]; then
                log_error "Failed to resolve email to user ID. Cannot proceed."
                exit 1
            fi
        else
            # Assume it's already a user ID
            user_id="$user_input"
        fi
        
        log_info "Clearing all data from Vespa for user ID: $user_id (input: $user_input)"
        
        # Clear data for the specific user ID
        clear_vespa_data_for_group_id "$user_id" "$force_flag"
    fi
    

}

# Clear all data from Vespa for all users
clear_all_vespa_data() {
    log_info "Clearing all data from Vespa for ALL users..."
    
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
    
    log_info "This will delete ALL documents from Vespa for ALL users. Are you sure? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled"
        exit 0
    fi
    
    # First, try to discover all users by looking for documents with different user IDs
    # Since we can't query all users at once in streaming mode, we'll try some common ones
    local common_users=("trybriefly@outlook.com" "admin@briefly.com" "test@example.com")
    local all_users=()
    
    # Check which users actually have data
    for user in "${common_users[@]}"; do
        local user_response
        user_response=$(curl -s -X POST "$VESPA_ENDPOINT/search/" \
            -H "Content-Type: application/json" \
            -d "{\"yql\": \"select * from briefly_document where true\", \"hits\": 1, \"streaming.groupname\": \"$user\"}")
        
        local user_count
        user_count=$(echo "$user_response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    total_count = data.get('root', {}).get('fields', {}).get('totalCount', 0)
    print(total_count)
except Exception as e:
    print('0')
")
        
        if [[ "$user_count" != "0" ]]; then
            all_users+=("$user")
            log_info "Found user with data: $user ($user_count documents)"
        fi
    done
    
    if [[ ${#all_users[@]} -eq 0 ]]; then
        log_info "No users with data found"
        return 0
    fi
    
    # Clear data for each user
    for user in "${all_users[@]}"; do
        log_info "Clearing data for user: $user"
        clear_vespa_data_for_user "$user"
    done
    
    log_success "Data clearing completed for all users!"
}

# Helper function to clear data for a specific user (without confirmation)
clear_vespa_data_for_user() {
    local user_id="$1"
    
    log_info "Clearing data for user: $user_id..."
    
    # For streaming mode, use Vespa's visiting API to clear all documents for the user group
    log_info "Using Vespa visiting API to clear all documents for user group: $user_id"
    
    # Use the visiting API to delete all documents in the group
    # The selection and cluster parameters are required for visiting API deletions
    local visit_response
    visit_response=$(curl -s -X DELETE "$VESPA_ENDPOINT/document/v1/briefly/briefly_document/group/$user_id/?selection=true&cluster=briefly")
    
    if [[ $? -eq 0 ]]; then
        # Check if the response contains an error message
        if [[ "$visit_response" == *'"message"'* ]]; then
            log_error "Failed to clear documents for user group: $user_id"
            log_error "Vespa returned an error: $visit_response"
            return 1
        else
            log_success "Successfully cleared all documents for user group: $user_id"
            log_info "Response: $visit_response"
            return 0
        fi
    else
        log_error "Failed to clear documents for user group: $user_id"
        log_error "HTTP request failed with response: $visit_response"
        return 1
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
        clear_vespa_data "$@"
        ;;
    --clear-data-all-users)
        clear_vespa_data "$2" "--all-users"
        ;;

    --clear-all-data)
        clear_all_vespa_data
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
        echo "  --clear-data [--force] Clear all data from Vespa (useful for testing)"
        echo "  --clear-data-all-users Clear all data from Vespa for ALL discovered users"
        echo "  --clear-all-data Clear all data from Vespa for ALL users"
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
