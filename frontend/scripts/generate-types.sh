#!/bin/bash
# Type generation script for Unix systems
# Generates TypeScript types from OpenAPI schemas

set -e

echo "🚀 Generating TypeScript types from OpenAPI schemas..."

# Change to frontend directory
cd "$(dirname "$0")/.."

# Create types directory structure
mkdir -p types/api/{chat,meetings,office,user,shipments,email-sync}

# Install dependencies if not already installed
if ! npm list openapi-typescript-codegen >/dev/null 2>&1; then
    echo "📦 Installing openapi-typescript-codegen..."
    npm install
fi

# Generate types for each service
echo "📝 Generating types for Chat service..."
npx openapi --input ../openapi-schemas/chat-openapi.json --output ./types/api/chat

echo "📝 Generating types for Meetings service..."
npx openapi --input ../openapi-schemas/meetings-openapi.json --output ./types/api/meetings

echo "📝 Generating types for Office service..."
npx openapi --input ../openapi-schemas/office-openapi.json --output ./types/api/office

echo "📝 Generating types for User service..."
npx openapi --input ../openapi-schemas/user-openapi.json --output ./types/api/user

echo "📝 Generating types for Shipments service..."
npx openapi --input ../openapi-schemas/shipments-openapi.json --output ./types/api/shipments

echo "📝 Generating types for Email Sync service..."
npx openapi --input ../openapi-schemas/email_sync-openapi.json --output ./types/api/email-sync

# Create index file
echo "📄 Creating index file..."
cat > types/api/index.ts << 'EOF'
// Auto-generated TypeScript types from OpenAPI schemas
// Generated on: $(date)

export * from './chat';
export * from './meetings';
export * from './office';
export * from './user';
export * from './shipments';
export * from './email-sync';
EOF

echo "✅ Type generation completed successfully!"
echo "📁 Types saved to: types/api/"
echo "🔍 Run 'npm run typecheck' to verify types are valid"
