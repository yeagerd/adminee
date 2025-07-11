#!/bin/bash

# Briefly Frontend OAuth Demo Setup Script
# This script sets up the complete NextAuth OAuth integration demo

echo "🚀 Setting up Briefly Frontend OAuth Demo..."
echo ""

# Get the script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$REPO_ROOT/frontend"

# Check if we can find the frontend directory
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Error: Cannot find frontend directory at $FRONTEND_DIR"
    echo "   Make sure this script is in the scripts/ directory of the repo root"
    exit 1
fi

# Check if frontend has package.json
if [ ! -f "$FRONTEND_DIR/package.json" ]; then
    echo "❌ Error: No package.json found in $FRONTEND_DIR"
    echo "   The frontend directory structure seems incorrect"
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed"
    echo "   Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js found: $(node --version)"
echo "✅ Frontend directory found: $FRONTEND_DIR"

# Change to frontend directory for npm operations
cd "$FRONTEND_DIR"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed successfully"

# Create environment file if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo ""
    echo "🔧 Creating environment file..."
    cat > .env.local << 'EOF'
# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=briefly-super-secret-key-for-development-only

# Google OAuth (for identity authentication)
# Get these from: https://console.cloud.google.com/
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Microsoft OAuth (for identity authentication)  
# Get these from: https://portal.azure.com/
AZURE_AD_CLIENT_ID=your-azure-client-id
AZURE_AD_CLIENT_SECRET=your-azure-client-secret
AZURE_AD_TENANT_ID=common

# Backend Services
USER_SERVICE_URL=http://localhost:8001
API_FRONTEND_USER_KEY=your-api-key

# JWT Configuration (for development)
JWT_VERIFY_SIGNATURE=false

# Webhook Security
BFF_WEBHOOK_SECRET=briefly-webhook-secret-for-development
EOF
    echo "✅ Created .env.local with default values"
    echo "⚠️  You'll need to add your OAuth credentials to .env.local"
else
    echo "✅ Environment file already exists"
fi

# Check if user service is running
echo ""
echo "🔍 Checking user service connectivity..."
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ User service is running on http://localhost:8001"
else
    echo "⚠️  User service not detected on http://localhost:8001"
    echo "   Start it with: cd services/user && ./start.sh"
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. 🔑 Configure OAuth credentials in frontend/.env.local:"
echo "   - Google: https://console.cloud.google.com/"
echo "   - Microsoft: https://portal.azure.com/"
echo ""
echo "2. 🚀 Start the development server:"
echo "   cd frontend && npm run dev"
echo ""
echo "3. 🌐 Open your browser to:"
echo "   http://localhost:3000"
echo ""
echo "4. 📖 Full setup guide:"
echo "   See frontend/README.md for detailed OAuth provider setup"
echo ""
echo "🎯 Demo Flow:"
echo "• Visit http://localhost:3000"
echo "• Click 'Sign in with Google/Microsoft'"
echo "• Complete authentication"
echo "• Go to /integrations to connect calendar/email"
echo "• Explore dashboard and profile pages"
echo ""
echo "Happy coding! 🎉" 