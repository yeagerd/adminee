#!/bin/bash

echo "🚀 Testing all Docker builds for Briefly project"
echo "================================================="

# Set error handling
set -e

# Function to test build
test_build() {
    local service=$1
    local dockerfile=$2
    local tag=$3
    
    echo "📦 Building $service..."
    if docker build -f "$dockerfile" -t "$tag" .; then
        echo "✅ $service build successful"
        return 0
    else
        echo "❌ $service build failed"
        return 1
    fi
}

# Test all services
echo
test_build "Frontend Service" "Dockerfile.frontend" "briefly-frontend"
echo

test_build "User Management Service" "Dockerfile.user-service" "briefly-user-service"
echo

test_build "Chat Service" "Dockerfile.chat-service" "briefly-chat-service"
echo

test_build "Office Service" "Dockerfile.office-service" "briefly-office-service"
echo

echo "🎉 All Docker builds completed successfully!"
echo
echo "📋 Built images:"
docker images | grep briefly-

echo
echo "🔧 To run the full stack, use:"
echo "docker-compose up -d"
echo
echo "🧪 To run tests:"
echo "source venv/bin/activate && pytest" 