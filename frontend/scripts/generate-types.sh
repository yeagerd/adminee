#!/bin/bash
# Type generation script for Unix systems
# Generates TypeScript types from OpenAPI schemas

set -e

echo "🚀 Generating TypeScript types from OpenAPI schemas..."

# Change to frontend directory
cd "$(dirname "$0")/.."

# Create types directory structure
mkdir -p types/api/{chat,contacts,meetings,office,user,shipments,vespa_loader,vespa_query}

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

echo "📝 Generating types for Vespa Loader service..."
npx openapi --input ../openapi-schemas/vespa_loader-openapi.json --output ./types/api/vespa_loader --exportCore false --exportServices false

echo "📝 Generating types for Vespa Query service..."
npx openapi --input ../openapi-schemas/vespa_query-openapi.json --output ./types/api/vespa_query --exportCore false --exportServices false



# Create index file
echo "📄 Creating index file..."
cat > types/api/index.ts << 'EOF'
// Auto-generated TypeScript types from OpenAPI schemas
// Generated on: $(date)

export * from './chat';
export * from './contacts';
export * from './meetings';
export * from './office';
export * from './user';
export * from './shipments';
EOF

echo "✅ Type generation completed successfully!"
echo "📁 Types saved to: types/api/"
echo "🔍 Run 'npm run typecheck' to verify types are valid"
