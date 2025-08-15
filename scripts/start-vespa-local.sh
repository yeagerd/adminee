#!/bin/bash

# Start local Vespa instance for development
set -e

echo "Starting local Vespa instance..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Stop any existing Vespa container
echo "Stopping any existing Vespa containers..."
docker stop vespa-local 2>/dev/null || true
docker rm vespa-local 2>/dev/null || true

# Start Vespa container
echo "Starting Vespa container..."
docker run -d \
    --name vespa-local \
    -p 8080:8080 \
    -p 19092:19092 \
    -v "$(pwd)/vespa:/vespa-config" \
    vespaengine/vespa:latest

# Wait for Vespa to be ready
echo "Waiting for Vespa to be ready..."
sleep 30

# Deploy application
echo "Deploying Vespa application..."
docker exec vespa-local bash -c "cd /vespa-config && /opt/vespa/bin/vespa-deploy prepare . && /opt/vespa/bin/vespa-deploy activate"

# Wait for deployment to complete
echo "Waiting for deployment to complete..."
sleep 10

# Check status
echo "Checking Vespa status..."
docker exec vespa-local bash -c "/opt/vespa/bin/vespa-get-config"

echo "Vespa is ready at http://localhost:8080"
echo "Application package deployed successfully"
