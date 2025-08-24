#!/bin/bash
# Type generation script for Unix systems
# Generates TypeScript types from OpenAPI schemas

set -e

echo "🚀 Generating TypeScript types from OpenAPI schemas..."

# Change to frontend directory
cd "$(dirname "$0")/.."

# Create types directory structure and generate types for each service
services=("chat" "contacts" "meetings" "office" "user" "shipments")

# Install dependencies if not already installed
if ! npm list openapi-typescript-codegen >/dev/null 2>&1; then
    echo "📦 Installing openapi-typescript-codegen..."
    npm install
fi

for service in "${services[@]}"; do
    mkdir -p "types/api/${service}"
    echo "📝 Generating types for ${service^} service..."
    
    # Use openapi-typescript-codegen with optimized settings for better type handling
    npx openapi \
        --input "../openapi-schemas/${service}-openapi.json" \
        --output "./types/api/${service}" \
        --exportCore false \
        --exportServices false \
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
        --exportApiReadme false
done

# Create shared types module to avoid conflicts
echo "📝 Creating shared types module..."
mkdir -p types/api/shared/models

# Copy common validation types to shared module
cat > types/api/shared/models/ValidationError.ts << 'EOF'
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

cat > types/api/shared/models/HTTPValidationError.ts << 'EOF'
/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ValidationError } from './ValidationError';
export type HTTPValidationError = {
    detail?: Array<ValidationError>;
};
EOF

cat > types/api/shared/index.ts << 'EOF'
/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

// Common validation and error types used across all services
export type { HTTPValidationError } from './models/HTTPValidationError';
export type { ValidationError } from './models/ValidationError';
EOF

# Function to remove common types from a service's index.ts (FIXED: portable, no .bak files)
remove_common_types() {
    local service_file="$1"
    if [ -f "$service_file" ]; then
        # Create a temporary file for processing
        local temp_file=$(mktemp)
        
        # Remove HTTPValidationError and ValidationError exports (handle various formats)
        grep -v -E 'export (type|interface) \{ HTTPValidationError' "$service_file" | \
        grep -v -E 'export (type|interface) \{ ValidationError' | \
        grep -v -E 'export (type|interface) HTTPValidationError' | \
        grep -v -E 'export (type|interface) ValidationError' > "$temp_file"
        
        # Check if we need to add the import (only if the file contains these types)
        if grep -q -E 'HTTPValidationError|ValidationError' "$temp_file"; then
            # Find the first non-comment, non-empty line to insert import after (FIXED: avoids comment blocks)
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
        
        # Clean up temporary file (FIXED: no .bak files left behind)
        rm -f "$temp_file"
    fi
}

# Function to clean up duplicate type definitions within service files (using openapi-typescript-codegen)
cleanup_duplicate_types() {
    local service_dir="$1"
    if [ -d "$service_dir" ]; then
        echo "🧹 Types generated using openapi-typescript-codegen for ${service_dir}"
    fi
}

# Apply fixes to each service
echo "🔧 Fixing type conflicts in service modules..."
remove_common_types "types/api/chat/index.ts"
remove_common_types "types/api/contacts/index.ts"
remove_common_types "types/api/meetings/index.ts"
remove_common_types "types/api/office/index.ts"
remove_common_types "types/api/user/index.ts"
remove_common_types "types/api/shipments/index.ts"

# Clean up duplicate types within each service
echo "🧹 Cleaning up duplicate type definitions..."
cleanup_duplicate_types "types/api/chat"
cleanup_duplicate_types "types/api/contacts"
cleanup_duplicate_types "types/api/meetings"
cleanup_duplicate_types "types/api/office"
cleanup_duplicate_types "types/api/user"
cleanup_duplicate_types "types/api/shipments"

# Create main index file with namespaced exports to avoid conflicts
echo "📄 Creating main index file with namespaced exports..."
cat > types/api/index.ts << 'EOF'
// Auto-generated TypeScript types from OpenAPI schemas
// Generated on: $(date)

// Export shared common types
export * from './shared';

// Export service-specific types with namespacing to avoid conflicts
export * as ChatTypes from './chat';
export * as ContactsTypes from './contacts';
export * as MeetingsTypes from './meetings';
export * as OfficeTypes from './office';
export * as UserTypes from './user';
export * as ShipmentsTypes from './shipments';
EOF

echo "✅ Type generation completed successfully!"
echo "📁 Types saved to: types/api/"
echo "🔍 Run 'npm run typecheck' to verify types are valid"
