#!/bin/bash

# Unified script for generating OpenAPI schemas and TypeScript types
# This script handles the complete workflow from schema generation to type creation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Default flags
SCHEMA_ONLY=false
TYPES_ONLY=false
CLEAN_ONLY=false
VERBOSE=true

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help         Show this help message"
    echo "  -s, --schema-only  Generate OpenAPI schemas only"
    echo "  -t, --types-only   Generate TypeScript types only"
    echo "  -c, --clean-only   Clean generated files only"
    echo "  -q, --quiet        Disable verbose output"
    echo
    echo "Default behavior (no flags): Generate schemas, types, validation, and version matrix"
    echo
    echo "Examples:"
    echo "  $0                    # Full workflow: schemas + types + validation + version matrix"
    echo "  $0 --schema-only      # Generate OpenAPI schemas only"
    echo "  $0 --types-only       # Generate TypeScript types only"
    echo "  $0 --clean-only       # Clean generated files only"
    echo "  $0 --quiet            # Full workflow with quiet output"
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -s|--schema-only)
                SCHEMA_ONLY=true
                shift
                ;;
            -t|--types-only)
                TYPES_ONLY=true
                shift
                ;;
            -c|--clean-only)
                CLEAN_ONLY=true
                shift
                ;;
            -q|--quiet)
                VERBOSE=false
                shift
                ;;
            *)
                print_status "error" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Function to generate OpenAPI schemas
generate_schemas() {
    print_status "info" "Generating OpenAPI schemas for all services..."
    
    if [[ "$VERBOSE" == "true" ]]; then
        ./scripts/subscripts/generate-openapi-schemas.sh
    else
        ./scripts/subscripts/generate-openapi-schemas.sh > /dev/null 2>&1
    fi
    
    print_status "success" "OpenAPI schemas generated successfully"
}

# Function to clean generated files
clean_generated() {
    print_status "info" "Cleaning generated files..."
    
    # Clean OpenAPI schemas in services
    if [[ -d "openapi-schemas" ]]; then
        rm -rf openapi-schemas
        print_status "info" "Cleaned openapi-schemas directory"
    fi
    
    # Clean frontend types
    if [[ -d "frontend/types/api" ]]; then
        rm -rf frontend/types/api
        print_status "info" "Cleaned frontend/types/api directory"
    fi
    
    print_status "success" "Generated files cleaned successfully"
}

# Function to generate TypeScript types
generate_types() {
    print_status "info" "Generating TypeScript types from OpenAPI schemas..."
    
    cd frontend
    if [[ "$VERBOSE" == "true" ]]; then
        ../scripts/subscripts/update-types.sh
    else
        ../scripts/subscripts/update-types.sh > /dev/null 2>&1
    fi
    cd ..
    
    print_status "success" "TypeScript types generated successfully"
}

# Function to validate generated types
validate_types() {
    print_status "info" "Validating generated types..."
    
    if [[ "$VERBOSE" == "true" ]]; then
        ./scripts/subscripts/validate-types.sh
    else
        ./scripts/subscripts/validate-types.sh > /dev/null 2>&1
    fi
    
    print_status "success" "Type validation completed successfully"
}

# Function to generate version compatibility matrix
generate_version_matrix() {
    print_status "info" "Generating version compatibility matrix..."
    
    if [[ "$VERBOSE" == "true" ]]; then
        python3 ./scripts/subscripts/generate-version-matrix.py
    else
        python3 ./scripts/subscripts/generate-version-matrix.py > /dev/null 2>&1
    fi
    
    print_status "success" "Version compatibility matrix generated successfully"
}

# Function to run full workflow
run_full_workflow() {
    print_status "info" "Running complete type generation workflow..."
    
    # Step 1: Generate OpenAPI schemas
    generate_schemas
    
    # Step 2: Generate TypeScript types
    generate_types
    
    # Step 3: Validate types
    validate_types
    
    # Step 4: Generate version compatibility matrix
    generate_version_matrix
    
    print_status "success" "Complete workflow finished successfully!"
    print_status "info" "Generated files are ready for use"
}

# Main execution
main() {
    # Parse command line arguments
    parse_args "$@"
    
    # Ensure we're in the project root
    cd "$PROJECT_ROOT"
    
    print_status "info" "Starting type generation workflow..."
    print_status "info" "Project root: $PROJECT_ROOT"
    
    # Check for conflicting flags
    local flag_count=0
    [[ "$SCHEMA_ONLY" == "true" ]] && ((flag_count++))
    [[ "$TYPES_ONLY" == "true" ]] && ((flag_count++))
    [[ "$CLEAN_ONLY" == "true" ]] && ((flag_count++))
    
    if [[ $flag_count -gt 1 ]]; then
        print_status "error" "Only one operation flag can be specified at a time"
        exit 1
    fi
    
    # Execute based on flags
    if [[ "$CLEAN_ONLY" == "true" ]]; then
        clean_generated
    elif [[ "$SCHEMA_ONLY" == "true" ]]; then
        generate_schemas
    elif [[ "$TYPES_ONLY" == "true" ]]; then
        generate_types
    else
        # Default: run full workflow
        run_full_workflow
    fi
    
    print_status "success" "Operation completed successfully!"
    print_status "info" "Current directory: $(pwd)"
}

# Run main function with all arguments
main "$@"
