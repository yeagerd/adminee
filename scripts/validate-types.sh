#!/bin/bash

# Validation script for generated TypeScript types
# This script checks that types can be imported and used correctly

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
    echo "  -v, --verbose  Enable verbose output"
    echo "  -s, --strict   Enable strict TypeScript checking"
    echo
    echo "Arguments:"
    echo "  SERVICE_NAME   Validate types for specific service only (optional)"
    echo
    echo "Examples:"
    echo "  $0                    # Validate types for all services"
    echo "  $0 chat              # Validate types for chat service only"
    echo "  $0 --strict          # Validate with strict TypeScript checking"
    echo "  $0 chat --verbose    # Validate chat service with verbose output"
}

# Function to validate types for a service
validate_service_types() {
    local service_name=$1
    local strict=$2
    local verbose=$3
    
    local types_dir="$PROJECT_ROOT/frontend/types/api/$service_name"
    
    if [[ ! -d "$types_dir" ]]; then
        print_status "warning" "No types directory found for $service_name, skipping..."
        return 1
    fi
    
    print_status "info" "Validating types for $service_name..."
    
    # Check if types directory has content
    if [[ ! "$(ls -A "$types_dir")" ]]; then
        print_status "error" "Types directory for $service_name is empty"
        return 1
    fi
    
    # Check for essential type files
    local has_models=false
    local has_services=false
    local has_index=false
    
    if [[ -d "$types_dir/models" ]]; then
        has_models=true
        if [[ "$verbose" == "true" ]]; then
            print_status "info" "  ✓ Models directory found"
        fi
    fi
    
    if [[ -d "$types_dir/services" ]]; then
        has_services=true
        if [[ "$verbose" == "true" ]]; then
            print_status "info" "  ✓ Services directory found"
        fi
    fi
    
    if [[ -f "$types_dir/index.ts" ]]; then
        has_index=true
        if [[ "$verbose" == "true" ]]; then
            print_status "info" "  ✓ Index file found"
        fi
    fi
    
    if [[ "$has_models" == "false" ]] || [[ "$has_services" == "false" ]] || [[ "$has_index" == "false" ]]; then
        print_status "error" "Missing essential type files for $service_name"
        return 1
    fi
    
    # Run TypeScript compilation check
    cd "$PROJECT_ROOT/frontend"
    
    # Check if TypeScript is available
    if ! npx tsc --version &> /dev/null; then
        print_status "error" "TypeScript not available in frontend directory"
        return 1
    fi
    
    local tsconfig_file="tsconfig.json"
    if [[ "$strict" == "true" ]]; then
        # Create a temporary strict tsconfig for validation
        tsconfig_file="tsconfig.strict.json"
        cat > "$tsconfig_file" << EOF
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true
  },
  "include": ["types/api/$service_name/**/*"],
  "exclude": ["node_modules", "dist", "build"]
}
EOF
    fi
    
    if npx tsc --project "$tsconfig_file" --noEmit --skipLibCheck; then
        print_status "success" "Types for $service_name compiled successfully"
        
        # Clean up temporary tsconfig if created
        if [[ "$strict" == "true" ]] && [[ -f "$tsconfig_file" ]]; then
            rm "$tsconfig_file"
        fi
        
        return 0
    else
        print_status "error" "Types for $service_name failed to compile"
        
        # Clean up temporary tsconfig if created
        if [[ "$strict" == "true" ]] && [[ -f "$tsconfig_file" ]]; then
            rm "$tsconfig_file"
        fi
        
        return 1
    fi
}

# Function to validate all service types
validate_all_types() {
    local strict=$1
    local verbose=$2
    local results=()
    local successful=0
    local total=0
    
    print_status "info" "Starting type validation for all services..."
    echo "=================================================================="
    
    # Get list of services that have generated types
    local services=()
    for types_dir in "$PROJECT_ROOT"/frontend/types/api/*/; do
        if [[ -d "$types_dir" ]]; then
            local service_name=$(basename "$types_dir")
            services+=("$service_name")
        fi
    done
    
    if [[ ${#services[@]} -eq 0 ]]; then
        print_status "warning" "No generated types found. Run './scripts/update-types.sh' first."
        return 1
    fi
    
    for service_name in "${services[@]}"; do
        if validate_service_types "$service_name" "$strict" "$verbose"; then
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
    print_status "info" "Type Validation Summary"
    echo "=================================================================="
    
    for result in "${results[@]}"; do
        echo "$result"
    done
    
    echo
    echo "Total: $total services"
    echo "Success rate: $successful/$total ($(($successful * 100 / $total))%)"
    
    if [[ $successful -eq $total ]]; then
        print_status "success" "All types validated successfully!"
        return 0
    else
        print_status "warning" "Some type validations failed"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    local verbose=$1
    
    print_status "info" "Running integration tests..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Check if tests can import generated types
    local test_file="test-types-integration.ts"
    cat > "$test_file" << 'EOF'
// Integration test file to verify generated types can be imported and used
import type { 
    ChatRequest, 
    UserResponse, 
    MeetingPoll, 
    CalendarEvent, 
    PackageOut 
} from './types/api';

// Test that types can be imported
const testTypes = {
    ChatRequest: typeof ChatRequest,
    UserResponse: typeof UserResponse,
    MeetingPoll: typeof MeetingPoll,
    CalendarEvent: typeof CalendarEvent,
    PackageOut: typeof PackageOut
};

console.log('✅ All types imported successfully:', Object.keys(testTypes));
EOF
    
    if npx tsc --noEmit --skipLibCheck "$test_file"; then
        print_status "success" "Integration test passed - types can be imported"
        
        # Clean up test file
        rm "$test_file"
        return 0
    else
        print_status "error" "Integration test failed - types cannot be imported"
        
        # Clean up test file
        rm "$test_file"
        return 1
    fi
}

# Main function
main() {
    local strict=false
    local verbose=false
    local specific_service=""
    local run_integration=false
    
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
            -s|--strict)
                strict=true
                shift
                ;;
            -i|--integration)
                run_integration=true
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
    
    # Check if Node.js and TypeScript are available
    if ! command -v node &> /dev/null; then
        print_status "error" "Node.js is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v npx &> /dev/null; then
        print_status "error" "npx is not installed or not in PATH"
        exit 1
    fi
    
    # Run integration tests if requested
    if [[ "$run_integration" == "true" ]]; then
        if run_integration_tests "$verbose"; then
            print_status "success" "Integration tests completed successfully"
        else
            print_status "error" "Integration tests failed"
            exit 1
        fi
        return 0
    fi
    
    # Validate types
    if [[ -n "$specific_service" ]]; then
        # Validate types for specific service
        if validate_service_types "$specific_service" "$strict" "$verbose"; then
            print_status "success" "Types validated successfully for $specific_service"
            exit 0
        else
            print_status "error" "Failed to validate types for $specific_service"
            exit 1
        fi
    else
        # Validate types for all services
        validate_all_types "$strict" "$verbose"
    fi
}

# Run main function with all arguments
main "$@"
