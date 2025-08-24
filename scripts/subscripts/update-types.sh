#!/bin/bash

# Development script for updating TypeScript types from OpenAPI schemas
# This script is used by developers to manually regenerate types during development

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory - use git to find the repo root
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git -C "$script_dir/.." rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$script_dir/../.." && pwd)")"

# Verify we have a valid project root
if [[ ! -d "$PROJECT_ROOT/services" ]] || [[ ! -d "$PROJECT_ROOT/frontend" ]]; then
    echo "ERROR: Could not find valid project root. PROJECT_ROOT=$PROJECT_ROOT" >&2
    echo "ERROR: Current directory: $(pwd)" >&2
    echo "ERROR: Script location: ${BASH_SOURCE[0]}" >&2
    exit 1
fi

# Debug output (only in verbose mode)
if [[ "${verbose:-false}" == "true" ]]; then
    echo "DEBUG: BASH_SOURCE[0] = ${BASH_SOURCE[0]}"
    echo "DEBUG: dirname = $(dirname "${BASH_SOURCE[0]}")"
    echo "DEBUG: PROJECT_ROOT = $PROJECT_ROOT"
    echo "DEBUG: PWD = $(pwd)"
    echo "DEBUG: services dir exists = $([[ -d "$PROJECT_ROOT/services" ]] && echo 'yes' || echo 'no')"
    echo "DEBUG: frontend dir exists = $([[ -d "$PROJECT_ROOT/frontend" ]] && echo 'yes' || echo 'no')"
fi

# Function to print colored output
print_status() {
    local level=$1
    local message=$2
    
    case $level in
        "info")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
        "success")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "error")
            echo -e "${RED}❌ $message${NC}"
            ;;
    esac
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [SERVICE_NAME]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -f, --force    Force regeneration even if no changes detected"
    echo "  -c, --clean    Clean generated types before regeneration"
    echo "  -v, --verbose  Enable verbose output"
    echo
    echo "Arguments:"
    echo "  SERVICE_NAME   Update types for specific service only (optional)"
    echo
    echo "Examples:"
    echo "  $0                    # Update types for all services"
    echo "  $0 chat              # Update types for chat service only"
    echo "  $0 --force           # Force regeneration for all services"
    echo "  $0 --clean           # Clean and regenerate all types"
    echo "  $0 chat --verbose    # Update chat service with verbose output"
}

# Function to clean generated types
clean_types() {
    local service_name=$1
    
    if [[ -n "$service_name" ]]; then
        local types_dir="$PROJECT_ROOT/frontend/types/api/$service_name"
        if [[ -d "$types_dir" ]]; then
            print_status "info" "Cleaning types for $service_name..."
            rm -rf "$types_dir"
            print_status "success" "Cleaned types for $service_name"
        fi
    else
        print_status "info" "Cleaning all generated types..."
        rm -rf "$PROJECT_ROOT/frontend/types/api"
        print_status "success" "Cleaned all generated types"
    fi
}

# Function to check if types need updating
check_types_need_update() {
    local service_name=$1
    local schema_file="$PROJECT_ROOT/services/$service_name/openapi/schema.json"
    local types_dir="$PROJECT_ROOT/frontend/types/api/$service_name"
    
    if [[ ! -f "$schema_file" ]]; then
        return 1  # Schema doesn't exist, needs update
    fi
    
    if [[ ! -d "$types_dir" ]]; then
        return 0  # Types don't exist, needs update
    fi
    
    # Check if schema is newer than types
    if [[ "$schema_file" -nt "$types_dir" ]]; then
        return 0  # Schema is newer, needs update
    fi
    
    return 1  # No update needed
}

# Function to update types for a service
update_service_types() {
    local service_name=$1
    local force=$2
    
    local schema_file="$PROJECT_ROOT/services/$service_name/openapi/schema.json"
    local types_dir="$PROJECT_ROOT/frontend/types/api/$service_name"
    
    if [[ ! -f "$schema_file" ]]; then
        print_status "warning" "No OpenAPI schema found for $service_name, skipping..."
        return 1
    fi
    
    if [[ "$force" != "true" ]] && ! check_types_need_update "$service_name"; then
        print_status "info" "Types for $service_name are up to date, skipping..."
        return 0
    fi
    
    print_status "info" "Updating types for $service_name..."
    
    # Create types directory if it doesn't exist
    mkdir -p "$types_dir"
    
    # Generate types using openapi-typescript-codegen (no Java dependency)
    cd "$PROJECT_ROOT/frontend"
    
    # Use openapi-typescript-codegen with optimized settings for better type handling
    if npx --no-install openapi-typescript-codegen \
        --input "$schema_file" \
        --output "$types_dir" \
        --exportServices false \
        --exportCore false \
        --exportClient false \
        --exportModels true \
        --exportUtils false \
        --exportServer false \
        --exportTest false \
        --exportReadme false \
        --exportApi false \
        --exportApiCore false \
        --exportApiClient false \
        --exportApiServer false \
        --exportApiUtils false \
        --exportApiTest false \
        --exportApiReadme false; then
        print_status "success" "Types updated for $service_name (using openapi-typescript-codegen)"
        
        # Clean up duplicate types if Python is available
        if command -v python3 &> /dev/null; then
            print_status "info" "Cleaning up duplicate types for $service_name..."
            if python3 -c "
import re
import sys
from pathlib import Path

def cleanup_duplicate_types(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split content into lines for processing
        lines = content.split('\n')
        result_lines = []
        seen_types = set()
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this line starts a type/interface declaration
            type_match = re.match(r'^(export\s+)?(type|interface)\s+([A-Za-z_][A-Za-z0-9_]*)', line)
            
            if type_match:
                type_name = type_match.group(3)
                
                if type_name in seen_types:
                    # This is a duplicate - skip until we find the end
                    i += 1
                    
                    # Skip lines until we find the end of this type definition
                    brace_count = 0
                    if '{' in line:
                        brace_count += line.count('{')
                    
                    while i < len(lines) and brace_count > 0:
                        current_line = lines[i]
                        brace_count += current_line.count('{')
                        brace_count -= current_line.count('}')
                        i += 1
                    
                    # Also check for semicolon (single-line types)
                    if i < len(lines) and ';' in lines[i-1]:
                        continue
                    
                    continue
                else:
                    # First occurrence - keep it
                    seen_types.add(type_name)
            
            result_lines.append(line)
            i += 1
        
        # Clean up empty lines and write the cleaned content back
        cleaned_lines = [line for line in result_lines if line.strip() or line == '']
        with open(file_path, 'w') as f:
            f.write('\n'.join(cleaned_lines))
            
    except Exception as e:
        print(f'Error processing {file_path}: {e}', file=sys.stderr)
        return False
    
    return True

def cleanup_service_directory(service_dir):
    service_path = Path(service_dir)
    if not service_path.is_dir():
        print(f'Service directory not found: {service_dir}', file=sys.stderr)
        return False
    
    # Find all TypeScript files in the service directory
    ts_files = list(service_path.rglob('*.ts'))
    
    if not ts_files:
        print(f'No TypeScript files found in {service_dir}')
        return True
    
    print(f'Processing {len(ts_files)} TypeScript files in {service_dir}')
    
    success = True
    for ts_file in ts_files:
        if not cleanup_duplicate_types(str(ts_file)):
            success = False
    
    return success

# Process the service directory
if cleanup_service_directory('$types_dir'):
    print('✅ Duplicate type cleanup completed successfully')
    sys.exit(0)
else:
    print('❌ Duplicate type cleanup failed', file=sys.stderr)
    sys.exit(1)
"; then
            print_status "success" "Duplicate types cleaned for $service_name"
        else
            print_status "warning" "Duplicate type cleanup failed for $service_name (continuing anyway)"
        fi
    else
        print_status "warning" "Python3 not available, skipping duplicate type cleanup for $service_name"
    fi
    else
        print_status "error" "Failed to update types for $service_name"
        return 1
    fi
    
    return 0
}

# Function to update all service types
update_all_types() {
    local force=$1
    local results=()
    local successful=0
    local total=0
    
    print_status "info" "Starting type update for all services..."
    echo "=================================================================="
    
    # Services to exclude from frontend type generation (same as generate-openapi-schemas.sh)
    local EXCLUDED_SERVICES="common email_sync demos briefly.egg-info __pycache__"
    
    # Get list of services that have OpenAPI schemas
    local services=()
    echo "DEBUG: Looking for services in: $PROJECT_ROOT/services/*/"
    echo "DEBUG: Current working directory: $(pwd)"
    echo "DEBUG: PROJECT_ROOT: $PROJECT_ROOT"
    
    for service_dir in "$PROJECT_ROOT"/services/*/; do
        echo "DEBUG: Checking service directory: $service_dir"
        if [[ -d "$service_dir" ]]; then
            local service_name=$(basename "$service_dir")
            echo "DEBUG: Found service directory: $service_dir (service: $service_name)"
            
            # Check if service should be excluded from frontend type generation
            if [[ " $EXCLUDED_SERVICES " =~ " $service_name " ]]; then
                echo "DEBUG: Excluding service from frontend types: $service_name"
                continue
            fi
            
            if [[ -f "$service_dir/openapi/schema.json" ]]; then
                echo "DEBUG: Service $service_name has OpenAPI schema and will generate frontend types"
                services+=("$service_name")
            else
                echo "DEBUG: Service $service_name missing OpenAPI schema: $service_dir/openapi/schema.json"
            fi
        else
            echo "DEBUG: Not a directory: $service_dir"
        fi
    done
    
    echo "DEBUG: Total services with OpenAPI schemas: ${#services[@]}"
    print_status "info" "Discovered ${#services[@]} services with OpenAPI schemas"
    
    # Debug: Show initial values
    echo "DEBUG: Initial values - successful=$successful, total=$total"
    
    for service_name in "${services[@]}"; do
        echo "Processing service: $service_name"
        
        if update_service_types "$service_name" "$force"; then
            results+=("✅ $service_name")
            successful=$((successful + 1))
            echo "✅ Successfully processed $service_name (successful=$successful)"
        else
            results+=("❌ $service_name")
            echo "❌ Failed to process $service_name"
        fi
        
        total=$((total + 1))
        echo "DEBUG: Completed service $service_name - total=$total, successful=$successful"
        echo
    done
    
    # Print summary
    echo "=================================================================="
    print_status "info" "Type Update Summary"
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
        print_status "success" "All types updated successfully!"
        return 0
    else
        print_status "warning" "Some type updates failed"
        return 1
    fi
}

# Main function
main() {
    local force=false
    local clean=false
    local verbose=false
    local specific_service=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--force)
                force=true
                shift
                ;;
            -c|--clean)
                clean=true
                shift
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
    
    # Check if we're in the right directory
    if [[ ! -d "$PROJECT_ROOT/frontend" ]]; then
        print_status "error" "This script must be run from the project root directory"
        exit 1
    fi
    
    # Check if Node.js and npm are available
    if ! command -v node &> /dev/null; then
        print_status "error" "Node.js is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_status "error" "npm is not installed or not in PATH"
        exit 1
    fi
    
    # Check if openapi-typescript-codegen is installed
    cd "$PROJECT_ROOT/frontend"
    if ! npx --no-install openapi-typescript-codegen --version &> /dev/null; then
        print_status "error" "openapi-typescript-codegen is not installed locally. Please run 'cd frontend && npm i -D openapi-typescript-codegen' first."
        exit 1
    fi
    
    # Clean types if requested
    if [[ "$clean" == "true" ]]; then
        clean_types "$specific_service"
    fi
    
    # Update types
    if [[ -n "$specific_service" ]]; then
        # Update types for specific service
        if update_service_types "$specific_service" "$force"; then
            print_status "success" "Types updated successfully for $specific_service"
            exit 0
        else
            print_status "error" "Failed to update types for $specific_service"
            exit 1
        fi
    else
        # Update types for all services
        update_all_types "$force"
    fi
}

# Run main function with all arguments
main "$@"
