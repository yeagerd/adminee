#!/bin/bash
# Type generation script for Unix systems
# Generates TypeScript types from OpenAPI schemas

set -e

echo "🚀 Generating TypeScript types from OpenAPI schemas..."

# Change to frontend directory
cd "$(dirname "$0")/.."

# Create types directory structure
mkdir -p types/api/{chat,contacts,meetings,office,user,shipments,shared}

# Install dependencies if not already installed
if ! npm list openapi-typescript-codegen >/dev/null 2>&1; then
    echo "📦 Installing openapi-typescript-codegen..."
    npm install
fi

# Generate types for each service - only models, no core/services
echo "📝 Generating types for Chat service..."
npx openapi --input ../openapi-schemas/chat-openapi.json --output ./types/api/chat --exportCore false --exportServices false

echo "📝 Generating types for Contacts service..."
npx openapi --input ../openapi-schemas/contacts-openapi.json --output ./types/api/contacts --exportCore false --exportServices false

echo "📝 Generating types for Meetings service..."
npx openapi --input ../openapi-schemas/meetings-openapi.json --output ./types/api/meetings --exportCore false --exportServices false

echo "📝 Generating types for Office service..."
npx openapi --input ../openapi-schemas/office-openapi.json --output ./types/api/office --exportCore false --exportServices false

echo "📝 Generating types for User service..."
npx openapi --input ../openapi-schemas/user-openapi.json --output ./types/api/user --exportCore false --exportServices false

echo "📝 Generating types for Shipments service..."
npx openapi --input ../openapi-schemas/shipments-openapi.json --output ./types/api/shipments --exportCore false --exportServices false

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

# Modify each service's index.ts to remove duplicate common types and import from shared
echo "🔧 Fixing type conflicts in service modules..."

# Function to remove common types from a service's index.ts
remove_common_types() {
    local service_file="$1"
    if [ -f "$service_file" ]; then
        # Remove HTTPValidationError and ValidationError exports
        sed -i.bak '/export type { HTTPValidationError }/d' "$service_file"
        sed -i.bak '/export type { ValidationError }/d' "$service_file"
        # Add import from shared at the top
        sed -i.bak '1a\
import type { HTTPValidationError, ValidationError } from "../shared";' "$service_file"
        # Clean up backup files
        rm -f "${service_file}.bak"
    fi
}

# Apply fixes to each service
remove_common_types "types/api/chat/index.ts"
remove_common_types "types/api/contacts/index.ts"
remove_common_types "types/api/meetings/index.ts"
remove_common_types "types/api/office/index.ts"
remove_common_types "types/api/user/index.ts"
remove_common_types "types/api/shipments/index.ts"

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
