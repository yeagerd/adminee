#!/bin/bash

# Briefly Express Gateway Startup Script

set -e

echo "🚀 Starting Briefly Express Gateway..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"

# Check if we're in the right directory
if [ ! -f "gateway/package.json" ]; then
    echo "❌ gateway/package.json not found. Please run this script from the repo root."
    exit 1
fi

# Change to gateway directory
cd gateway

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
else
    echo "✅ Dependencies already installed"
fi

# Set default values if not provided
export PORT=${PORT:-3001}
export NODE_ENV=${NODE_ENV:-development}
export BACKEND_URL=${BACKEND_URL:-http://localhost:8000}
export FRONTEND_URL=${FRONTEND_URL:-http://localhost:3000}

echo "🔧 Configuration:"
echo "   Port: $PORT"
echo "   Environment: $NODE_ENV"
echo "   Backend URL: $BACKEND_URL"
echo "   Frontend URL: $FRONTEND_URL"

# Start the gateway
echo "🚀 Starting gateway on port $PORT..."
echo "   Health check: http://localhost:$PORT/health"
echo "   API proxy: http://localhost:$PORT/api/*"
echo ""
echo "Press Ctrl+C to stop"

if [ "$NODE_ENV" = "development" ]; then
    npm run dev
else
    npm start
fi 