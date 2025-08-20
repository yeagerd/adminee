#!/bin/bash

# Generate OpenAPI schemas for all services
# This script runs each service's FastAPI application to generate OpenAPI schemas

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Service configuration
SERVICES="chat meetings office shipments email_sync vector_db"
SERVICE_PATHS="services/chat services/meetings services/office services/shipments services/email_sync services/vector_db"

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "info") echo -e "${BLUE}ℹ️  $message${NC}" ;;
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
    esac
}

# Function to check if a service exists and has FastAPI app
check_service() {
    local service_name=$1
    local service_path=$2
    
    if [[ ! -d "$PROJECT_ROOT/$service_path" ]]; then
        print_status "warning" "Service directory not found: $service_path"
        return 1
    fi
    
    # Check for different possible main.py locations
    local main_file=""
    if [[ -f "$PROJECT_ROOT/$service_path/main.py" ]]; then
        main_file="$PROJECT_ROOT/$service_path/main.py"
    elif [[ -f "$PROJECT_ROOT/$service_path/app/main.py" ]]; then
        main_file="$PROJECT_ROOT/$service_path/app/main.py"
    else
        print_status "warning" "Main file not found: $service_path/main.py or $service_path/app/main.py"
        return 1
    fi
    
    return 0
}

# Function to create openapi directory
create_openapi_dir() {
    local service_path=$1
    local openapi_dir="$PROJECT_ROOT/$service_path/openapi"
    
    if [[ ! -d "$openapi_dir" ]]; then
        mkdir -p "$openapi_dir"
        print_status "info" "Created openapi directory: $openapi_dir"
    fi
}

# Function to find FastAPI app variable name
find_app_name() {
    local service_path=$1
    
    # Determine the correct main.py path
    local main_file=""
    if [[ -f "$PROJECT_ROOT/$service_path/main.py" ]]; then
        main_file="$PROJECT_ROOT/$service_path/main.py"
    elif [[ -f "$PROJECT_ROOT/$service_path/app/main.py" ]]; then
        main_file="$PROJECT_ROOT/$service_path/app/main.py"
    else
        return 1
    fi
    
    # Look for common FastAPI app variable names and extract just the variable name
    local app_line=$(grep -E "^(app|fastapi_app|api)\s*=\s*FastAPI\(" "$main_file" | head -1)
    if [[ -n "$app_line" ]]; then
        # Extract the variable name (everything before the first space)
        local app_name=$(echo "$app_line" | awk '{print $1}')
        echo "$app_name"
    else
        return 1
    fi
}

# Function to generate schema for a service
generate_schema() {
    local service_name=$1
    local service_path=$2
    
    print_status "info" "Generating schema for $service_name service..."
    
    # Check service exists
    if ! check_service "$service_name" "$service_path"; then
        return 1
    fi
    
    # Create openapi directory
    create_openapi_dir "$service_path"
    
    # Find FastAPI app name
    local app_name
    if ! app_name=$(find_app_name "$service_path"); then
        print_status "error" "Could not find FastAPI app variable in $service_path/main.py"
        return 1
    fi
    
    print_status "info" "Found FastAPI app: $app_name"
    
    # Generate schema using Python directly
    local output_file="$PROJECT_ROOT/$service_path/openapi/schema.json"
    local temp_output
    
    # Determine the correct import path
    local import_path="services.$service_name.main"
    if [[ -f "$PROJECT_ROOT/$service_path/app/main.py" ]]; then
        import_path="services.$service_name.app.main"
    fi
    
    # Run Python from project root to ensure proper module resolution
    if temp_output=$(cd "$PROJECT_ROOT" && python -c "
import sys
import json

try:
    from $import_path import $app_name
    schema = $app_name.openapi()
    print(json.dumps(schema, indent=2))
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1); then
        # Save schema to file
        echo "$temp_output" > "$output_file"
        print_status "success" "Schema generated for $service_name at $output_file"
        return 0
    else
        print_status "error" "Failed to generate schema for $service_name: $temp_output"
        return 1
    fi
}

# Function to generate all schemas
generate_all_schemas() {
    local results=()
    local successful=0
    local total=0
    
    print_status "info" "Starting OpenAPI schema generation for all services..."
    echo "=================================================================="
    
    # Convert strings to arrays
    local services_array=($SERVICES)
    local paths_array=($SERVICE_PATHS)
    
    for i in "${!services_array[@]}"; do
        local service_name="${services_array[$i]}"
        local service_path="${paths_array[$i]}"
        
        if generate_schema "$service_name" "$service_path"; then
            results+=("✅ $service_name")
            ((successful++))
        else
            results+=("❌ $service_name")
        fi
        
        ((total++))
        echo
    done
    
    # Print summary
    echo "=================================================================="
    print_status "info" "Schema Generation Summary"
    echo "=================================================================="
    
    for result in "${results[@]}"; do
        echo "$result"
    done
    
    echo
    echo "Total: $total services"
    echo "Success rate: $successful/$total ($(($successful * 100 / $total))%)"
    
    if [[ $successful -eq $total ]]; then
        print_status "success" "All schemas generated successfully!"
        return 0
    else
        print_status "warning" "Some schemas failed to generate"
        echo
        print_status "info" "Troubleshooting tips:"
        echo "   - Check that each service has a valid FastAPI app in main.py"
        echo "   - Ensure all dependencies are installed"
        echo "   - Check service-specific error messages above"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [SERVICE_NAME]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verbose  Enable verbose output"
    echo
    echo "Arguments:"
    echo "  SERVICE_NAME   Generate schema for specific service only"
    echo "                 Available services: ${!SERVICES[*]}"
    echo
    echo "Examples:"
    echo "  $0                    # Generate schemas for all services"
    echo "  $0 chat              # Generate schema for chat service only"
    echo "  $0 --verbose         # Generate all schemas with verbose output"
}

# Main function
main() {
    local verbose=false
    local specific_service=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -*)
                print_status "error" "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -n "$specific_service" ]]; then
                    print_status "error" "Multiple services specified. Use only one service name."
                    exit 1
                fi
                specific_service="$1"
                shift
                ;;
        esac
    done
    
    # Enable verbose output if requested
    if [[ "$verbose" == "true" ]]; then
        set -x
    fi
    
    # Check if Python and FastAPI are available
    if ! command -v python &> /dev/null; then
        print_status "error" "Python is not installed or not in PATH"
        exit 1
    fi
    
    if ! python -c "import fastapi" &> /dev/null; then
        print_status "error" "FastAPI is not installed. Please install it first."
        exit 1
    fi
    
    # Generate schemas
    if [[ -n "$specific_service" ]]; then
        # Generate schema for specific service
        local services_array=($SERVICES)
        local paths_array=($SERVICE_PATHS)
        local service_found=false
        local service_path=""
        
        for i in "${!services_array[@]}"; do
            if [[ "${services_array[$i]}" == "$specific_service" ]]; then
                service_found=true
                service_path="${paths_array[$i]}"
                break
            fi
        done
        
        if [[ "$service_found" == "true" ]]; then
            if generate_schema "$specific_service" "$service_path"; then
                print_status "success" "Schema generated successfully for $specific_service"
                exit 0
            else
                print_status "error" "Failed to generate schema for $specific_service"
                exit 1
            fi
        else
            print_status "error" "Unknown service: $specific_service"
            echo "Available services: $SERVICES"
            exit 1
        fi
    else
        # Generate schemas for all services
        generate_all_schemas
    fi
}

# Run main function with all arguments
main "$@"
