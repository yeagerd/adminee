#!/bin/bash
# Type generation script for Unix systems
# Generates TypeScript types from OpenAPI schemas

set -e

# Help function
show_help() {
    cat << 'EOF'
Usage: $0 [OPTIONS]

Generate TypeScript types from OpenAPI schemas for all services.

OPTIONS:
    -h, --help              Show this help message
    -d, --schemas-dir DIR   Directory containing OpenAPI schemas (default: ../openapi-schemas)
    -o, --output-dir DIR    Output directory for generated types (default: ./types/api)
    -s, --skip-validation  Skip schema validation
    -c, --skip-cleanup     Skip duplicate type cleanup
    -v, --verbose          Enable verbose output

ENVIRONMENT VARIABLES:
    OPENAPI_SCHEMAS_DIR    Directory containing OpenAPI schemas
    TYPES_OUTPUT_DIR       Output directory for generated types
    SKIP_VALIDATION        Skip schema validation if set to "true"
    SKIP_CLEANUP          Skip duplicate type cleanup if set to "true"

EXAMPLES:
    $0                                    # Generate types with default settings
    $0 -d ./schemas -o ./types           # Use custom directories
    $0 --skip-validation                 # Skip schema validation
    SKIP_CLEANUP=true $0                 # Skip cleanup via environment variable

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--schemas-dir)
            OPENAPI_SCHEMAS_DIR="$2"
            shift 2
            ;;
        -o|--output-dir)
            TYPES_OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--skip-validation)
            SKIP_VALIDATION="true"
            shift
            ;;
        -c|--skip-cleanup)
            SKIP_CLEANUP="true"
            shift
            ;;
        -v|--verbose)
            set -x
            shift
            ;;
        *)
            echo "❌ Error: Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Cleanup function to remove temporary files on exit
cleanup() {
    local exit_code=$?
    
    # Remove any temporary files that might have been created by this script
    if [ -n "$TEMP_FILES" ]; then
        for temp_file in $TEMP_FILES; do
            if [ -f "$temp_file" ]; then
                rm -f "$temp_file" 2>/dev/null || true
            fi
        done
    fi
    
    # Clean up any remaining backup files
    find types/api -name "*.bak" -type f -delete 2>/dev/null || true
    
    exit $exit_code
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Variable to track temporary files
TEMP_FILES=""

echo "🚀 Generating TypeScript types from OpenAPI schemas..."

# Change to frontend directory
cd "$(dirname "$0")/.."

# Check if required tools are available
check_requirements() {
    local missing_tools=()
    
    if ! command -v npm >/dev/null 2>&1; then
        missing_tools+=("npm")
    fi
    
    if ! command -v npx >/dev/null 2>&1; then
        missing_tools+=("npx")
    fi
    
    if ! command -v awk >/dev/null 2>&1; then
        missing_tools+=("awk")
    fi
    
    if ! command -v grep >/dev/null 2>&1; then
        missing_tools+=("grep")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo "❌ Error: Missing required tools: ${missing_tools[*]}"
        echo "Please install the missing tools and try again."
        exit 1
    fi
}

# Check requirements before proceeding
check_requirements

# Configuration
: "${OPENAPI_SCHEMAS_DIR:=../openapi-schemas}"
: "${TYPES_OUTPUT_DIR:=./types/api}"
: "${SKIP_VALIDATION:=false}"
: "${SKIP_CLEANUP:=false}"

# Define services configuration
declare -A services=(
    ["chat"]="chat-openapi.json"
    ["contacts"]="contacts-openapi.json"
    ["meetings"]="meetings-openapi.json"
    ["office"]="office-openapi.json"
    ["user"]="user-openapi.json"
    ["shipments"]="shipments-openapi.json"
)

# Function to get service display name (capitalized)
get_service_display_name() {
    local service_name="$1"
    echo "$service_name" | sed 's/^./\U&/'
}

# Function to remove common types from a service's index.ts
remove_common_types() {
    local service_file="$1"
    if [ -f "$service_file" ]; then
        # Create a temporary file for processing
        local temp_file=$(mktemp)
        TEMP_FILES="$TEMP_FILES $temp_file"
        
        # Remove HTTPValidationError and ValidationError exports (handle various formats)
        grep -v -E 'export (type|interface) \{ HTTPValidationError' "$service_file" | \
        grep -v -E 'export (type|interface) \{ ValidationError' | \
        grep -v -E 'export (type|interface) HTTPValidationError' | \
        grep -v -E 'export (type|interface) ValidationError' > "$temp_file"
        
        # Check if we need to add the import (only if the file contains these types)
        if grep -q -E 'HTTPValidationError|ValidationError' "$temp_file"; then
            # Find the first non-comment, non-empty line to insert import after
            local insert_line=$(awk '
                /^[[:space:]]*$/ { next }
                /^[[:space:]]*\/\// { next }
                /^[[:space:]]*\/\*/ { next }
                /^[[:space:]]*\*/ { next }
                { print NR; exit }
            ' "$temp_file")
            
            if [ -n "$insert_line" ]; then
                # Insert import after the first non-comment line
                awk -v line="$insert_line" -v import="import type { HTTPValidationError, ValidationError } from \"../shared\";" '
                    NR == line { print; print import; next }
                    { print }
                ' "$temp_file" > "$service_file"
            else
                # If no suitable line found, prepend to the beginning
                echo "import type { HTTPValidationError, ValidationError } from \"../shared\";" > "$service_file"
                cat "$temp_file" >> "$service_file"
            fi
        else
            # No validation types found, just copy the cleaned file
            cp "$temp_file" "$service_file"
        fi
    fi
}

# Function to clean up duplicate type definitions within service files
cleanup_duplicate_types() {
    local service_dir="$1"
    if [ -d "$service_dir" ]; then
        # Find all TypeScript files in the service directory
        find "$service_dir" -name "*.ts" -type f | while read -r file; do
            # Create a temporary file for processing
            local temp_file=$(mktemp)
            TEMP_FILES="$TEMP_FILES $temp_file"
            
            # Remove duplicate type definitions (keep only the first occurrence)
            awk '
                # Track seen type names
                BEGIN { seen_types[""] = 0 }
                
                # Match type/interface declarations
                /^(export )?(type|interface) [A-Za-z_][A-Za-z0-9_]*/ {
                    type_name = $2 == "export" ? $3 : $2
                    if (seen_types[type_name]++) {
                        # Skip this duplicate type definition
                        in_type = 1
                        next
                    }
                }
                
                # Track when we exit a type definition
                /^}/ && in_type {
                    in_type = 0
                    next
                }
                
                # Skip lines while in a duplicate type
                in_type { next }
                
                # Print all other lines
                { print }
            ' "$file" > "$temp_file"
            
            # Replace original file with cleaned version
            cp "$temp_file" "$file"
        done
    fi
}

# Function to process all services
process_services() {
    local operation="$1"
    local description="$2"
    
    echo "$description..."
    local total_services=${#services[@]}
    local current=0
    
    for service_name in "${!services[@]}"; do
        current=$((current + 1))
        local display_name=$(get_service_display_name "$service_name")
        echo "  [$current/$total_services] 📝 Processing $display_name service..."
        
        case "$operation" in
            "generate")
                local schema_file="${services[$service_name]}"
                local output_dir="$TYPES_OUTPUT_DIR/$service_name"
                
                if ! npx openapi --input "$OPENAPI_SCHEMAS_DIR/$schema_file" --output "$output_dir" --exportCore false --exportServices false; then
                    echo "❌ Error: Failed to generate types for $display_name service"
                    return 1
                fi
                ;;
            "fix_conflicts")
                remove_common_types "$TYPES_OUTPUT_DIR/$service_name/index.ts"
                ;;
            "cleanup_duplicates")
                cleanup_duplicate_types "$TYPES_OUTPUT_DIR/$service_name"
                ;;
            *)
                echo "❌ Error: Unknown operation: $operation"
                return 1
                ;;
        esac
    done
    
    echo "✅ Completed $description for all $total_services services"
}

# Validate OpenAPI schema files exist
validate_schemas() {
    local schema_dir="$OPENAPI_SCHEMAS_DIR"
    
    if [ ! -d "$schema_dir" ]; then
        echo "❌ Error: OpenAPI schemas directory not found: $schema_dir"
        echo "Please ensure the openapi-schemas directory exists and contains the required JSON files."
        exit 1
    fi
    
    # Check each service schema
    for service_name in "${!services[@]}"; do
        local schema_file="${services[$service_name]}"
        if [ ! -f "$schema_dir/$schema_file" ]; then
            echo "❌ Error: Required OpenAPI schema not found: $schema_file"
            echo "Please ensure all required schema files are present in $schema_dir"
            exit 1
        fi
    done
    
    echo "✅ All required OpenAPI schemas found"
}

# Validate schemas before proceeding
if [ "$SKIP_VALIDATION" = "false" ]; then
    validate_schemas
fi

# Clean existing types to ensure a fresh generation
echo "🧹 Cleaning existing types..."
if [ -d "types/api" ]; then
    rm -rf types/api
    echo "✅ Removed existing types directory"
else
    echo "ℹ️  No existing types directory found"
fi
fi

# Create types directory structure
echo "📁 Creating types directory structure..."
mkdir -p "$TYPES_OUTPUT_DIR/shared"
for service_name in "${!services[@]}"; do
    mkdir -p "$TYPES_OUTPUT_DIR/$service_name"
done

# Install dependencies if not already installed
if ! npm list openapi-typescript-codegen >/dev/null 2>&1; then
    echo "📦 Installing openapi-typescript-codegen..."
    npm install
fi

# Generate types for each service - only models, no core/services
if ! process_services "generate" "📝 Generating types for all services"; then
    echo "❌ Error: Type generation failed"
    exit 1
fi

# Create shared types module to avoid conflicts
echo "📝 Creating shared types module..."
mkdir -p "$TYPES_OUTPUT_DIR/shared/models"

# Copy common validation types to shared module
cat > "$TYPES_OUTPUT_DIR/shared/models/ValidationError.ts" << 'EOF'
/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ValidationError = {
    loc: Array<(string | number)>;
    msg: string;
    type: string;
};
EOF

cat > "$TYPES_OUTPUT_DIR/shared/models/HTTPValidationError.ts" << 'EOF'
/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ValidationError } from './ValidationError';
export type HTTPValidationError = {
    detail?: Array<ValidationError>;
};
EOF

cat > "$TYPES_OUTPUT_DIR/shared/index.ts" << 'EOF'
/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

// Common validation and error types used across all services
export type { HTTPValidationError } from './models/HTTPValidationError';
export type { ValidationError } from './models/ValidationError';
EOF

# Apply fixes to each service
if ! process_services "fix_conflicts" "🔧 Fixing type conflicts in service modules"; then
    echo "❌ Error: Failed to fix type conflicts"
    exit 1
fi

# Clean up duplicate types within each service
if [ "$SKIP_CLEANUP" = "true" ]; then
    echo "⏭️  Skipping duplicate type cleanup (--skip-cleanup flag set)"
else
    if ! process_services "cleanup_duplicates" "🧹 Cleaning up duplicate type definitions"; then
        echo "❌ Error: Failed to cleanup duplicate types"
        exit 1
    fi
fi

# Create main index file with namespaced exports to avoid conflicts
echo "📄 Creating main index file with namespaced exports..."
{
    echo "// Auto-generated TypeScript types from OpenAPI schemas"
    echo "// Generated on: $(date)"
    echo ""
    echo "// Export shared common types"
    echo "export * from './shared';"
    echo ""
    echo "// Export service-specific types with namespacing to avoid conflicts"
    
    # Generate exports for each service
    for service_name in "${!services[@]}"; do
        local export_name=$(get_service_display_name "$service_name")
        echo "export * as ${export_name}Types from './$service_name';"
    done
} > "$TYPES_OUTPUT_DIR/index.ts"

# Validate generated types
echo "🔍 Validating generated types..."
if command -v npx >/dev/null 2>&1 && [ -f "package.json" ]; then
    if npm run typecheck >/dev/null 2>&1; then
        echo "✅ Type validation passed"
    else
        echo "⚠️  Type validation failed - you may need to run 'npm run typecheck' to see detailed errors"
    fi
else
    echo "ℹ️  Skipping type validation (npx or package.json not available)"
fi

echo "✅ Type generation completed successfully!"
echo "📁 Types saved to: $TYPES_OUTPUT_DIR/"
echo "🔍 Run 'npm run typecheck' to verify types are valid"

# Print summary
echo ""
echo "📊 Summary:"
echo "  • Generated types for ${#services[@]} services:"
for service_name in "${!services[@]}"; do
    local display_name=$(get_service_display_name "$service_name")
    echo "    - $display_name"
done
echo "  • Created shared validation types"
echo "  • Applied type conflict fixes"
if [ "$SKIP_CLEANUP" != "true" ]; then
    echo "  • Cleaned up duplicate type definitions"
else
    echo "  • Skipped duplicate type cleanup"
fi
echo "  • Generated namespaced exports in index.ts"
echo ""
echo "🚀 Ready to use! Import types like:"
echo "   import { ChatTypes, UserTypes } from './types/api';"
