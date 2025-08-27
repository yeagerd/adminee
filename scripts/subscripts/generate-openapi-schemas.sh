#!/bin/bash

# Generate OpenAPI schemas for all services
# This script runs each service's FastAPI application to generate OpenAPI schemas

set -e  # Exit on any error

# Function to handle script exit and provide debugging info
cleanup_and_debug() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo "ERROR: Script failed with exit code $exit_code" >&2
        echo "ERROR: Last command that failed: $BASH_COMMAND" >&2
        echo "ERROR: Current working directory: $(pwd)" >&2
        echo "ERROR: Environment variables:" >&2
        echo "  - PROJECT_ROOT: ${PROJECT_ROOT:-'not set'}" >&2
        echo "  - PWD: $(pwd)" >&2
        echo "  - Python: $(which python 2>/dev/null || echo 'not found')" >&2
        echo "  - Git root: $(git rev-parse --show-toplevel 2>/dev/null || echo 'not found')" >&2
    fi
    exit $exit_code
}

# Set trap to run cleanup function on exit
trap cleanup_and_debug EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory - use git to find the repo root
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git -C "$script_dir/.." rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$script_dir/../.." && pwd)")"

# Service configuration
# Services to exclude from OpenAPI generation (no meaningful schemas or not FastAPI apps)
EXCLUDED_SERVICES="common email_sync demos briefly.egg-info __pycache__ api"

# Auto-discover services
discover_services() {
    local services=()
    local paths=()
    
    for service_dir in "$PROJECT_ROOT"/services/*/; do
        if [[ -d "$service_dir" ]]; then
            local service_name=$(basename "$service_dir")
            
            # Check if service should be excluded
            if [[ " $EXCLUDED_SERVICES " =~ " $service_name " ]]; then
                echo "DEBUG: Excluding service: $service_name"
                continue
            fi
            
            # Check if service has a main.py file
            if [[ -f "$service_dir/main.py" ]] || [[ -f "$service_dir/app/main.py" ]]; then
                services+=("$service_name")
                paths+=("services/$service_name")
                echo "DEBUG: Including service: $service_name"
            else
                echo "DEBUG: Skipping service (no main.py): $service_name"
            fi
        fi
    done
    
    # Export arrays for use in the script
    SERVICES="${services[*]}"
    SERVICE_PATHS="${paths[*]}"
    
    echo "DEBUG: Discovered services: $SERVICES"
    echo "DEBUG: Service paths: $SERVICE_PATHS"
}

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



    # Look for common FastAPI app variable patterns
    # Pattern 1: Direct FastAPI instantiation
    local app_line=$(grep -E "^(app|fastapi_app|api)\s*=\s*FastAPI\(" "$main_file" | head -1)
    if [[ -n "$app_line" ]]; then
        local app_name=$(echo "$app_line" | awk '{print $1}')
        echo "$app_name"
        return 0
    fi

    # Pattern 2: App proxy or other patterns (like user service)
    app_line=$(grep -E "^(app|fastapi_app|api)\s*=\s*" "$main_file" | head -1)
    if [[ -n "$app_line" ]]; then
        local app_name=$(echo "$app_line" | awk '{print $1}')
        echo "$app_name"
        return 0
    fi

    # Pattern 3: Look for uvicorn or ASGI app references
    app_line=$(grep -E "uvicorn\.run\(" "$main_file" | grep -o '"[^"]*:app"' | sed 's/".*://; s/"//')
    if [[ -n "$app_line" ]]; then
        echo "$app_line"
        return 0
    fi

    # Default fallback
    echo "app"
    return 0
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
    echo "DEBUG: Running Python from $PROJECT_ROOT"
    echo "DEBUG: Import path: $import_path"
    echo "DEBUG: App name: $app_name"
    echo "DEBUG: Python executable: $(which python)"
    echo "DEBUG: Virtual env Python: $PROJECT_ROOT/.venv/bin/python"
    
    if temp_output=$(cd "$PROJECT_ROOT" && .venv/bin/python -c "
import sys
import json
import traceback
import os

try:
    print(f'DEBUG: Python path: {sys.path}', file=sys.stderr)
    print(f'DEBUG: Current working directory: {os.getcwd()}', file=sys.stderr)
    from $import_path import $app_name
    print(f'DEBUG: Successfully imported $app_name', file=sys.stderr)
    schema = $app_name.openapi()
    print(json.dumps(schema, indent=2))
except Exception as e:
    print(f'ERROR: Failed to generate schema for $service_name', file=sys.stderr)
    print(f'ERROR: Exception: {e}', file=sys.stderr)
    print(f'ERROR: Traceback:', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
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
    
    # Debug: Show initial values
    echo "DEBUG: Initial values - successful=$successful, total=$total"
    
    print_status "info" "Starting OpenAPI schema generation for all services..."
    echo "=================================================================="
    
    # Discover services if not already done
    if [[ -z "$SERVICES" ]]; then
        discover_services
    fi
    
    # Convert strings to arrays
    local services_array=($SERVICES)
    local paths_array=($SERVICE_PATHS)
    
    for i in "${!services_array[@]}"; do
        local service_name="${services_array[$i]}"
        local service_path="${paths_array[$i]}"
        
        echo "Processing service $((i+1))/${#services_array[@]}: $service_name"
        
        if generate_schema "$service_name" "$service_path"; then
            results+=("✅ $service_name")
            successful=$((successful + 1))
            echo "✅ Successfully processed $service_name (successful=$successful)"
        else
            results+=("❌ $service_name")
            echo "❌ Failed to process $service_name - check error messages above"
        fi
        
        total=$((total + 1))
        echo "DEBUG: Completed service $service_name - total=$total, successful=$successful"
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
    if [[ $total -gt 0 ]]; then
        echo "Success rate: $successful/$total ($(($successful * 100 / $total))%)"
    else
        echo "Success rate: 0/0 (0%)"
    fi
    
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
    
    # Discover available services
    discover_services
    
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
    
    # Check if Python is available
    if ! command -v python &> /dev/null; then
        print_status "error" "Python is not installed or not in PATH"
        exit 1
    fi
    
    # Try to activate virtual environment if it exists
    if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
        print_status "info" "Activating virtual environment..."
        source "$PROJECT_ROOT/.venv/bin/activate"
        print_status "success" "Virtual environment activated"
    elif [[ -f "$PROJECT_ROOT/.venv/Scripts/activate" ]]; then
        print_status "info" "Activating virtual environment (Windows)..."
        source "$PROJECT_ROOT/.venv/Scripts/activate"
        print_status "success" "Virtual environment activated"
    else
        print_status "warning" "No virtual environment found at .venv/"
        print_status "info" "Continuing with system Python..."
    fi
    
    # Check if FastAPI is available
    if ! python -c "import fastapi" &> /dev/null; then
        print_status "error" "FastAPI is not installed. Please install it first."
        print_status "info" "Try: cd $PROJECT_ROOT && uv sync --all-packages --all-extras --active"
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
