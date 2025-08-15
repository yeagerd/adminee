#!/bin/bash

# Start local Google Cloud Pubsub emulator
set -e

echo "Starting Google Cloud Pubsub emulator..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Stop any existing pubsub emulator container
echo "Stopping any existing pubsub emulator containers..."
docker stop pubsub-emulator 2>/dev/null || true
docker rm pubsub-emulator 2>/dev/null || true

# Start pubsub emulator container
echo "Starting pubsub emulator container..."
docker run -d \
    --name pubsub-emulator \
    -p 8085:8085 \
    gcr.io/google.com/cloudsdktool/google-cloud-cli:latest \
    gcloud beta emulators pubsub start --host-port=0.0.0.0:8085

# Wait for emulator to be ready
echo "Waiting for pubsub emulator to be ready..."
sleep 10

# Set environment variables
export PUBSUB_EMULATOR_HOST=localhost:8085
export PUBSUB_PROJECT_ID=briefly-dev

echo "Pubsub emulator is ready at localhost:8085"
echo "Environment variables set:"
echo "  PUBSUB_EMULATOR_HOST=localhost:8085"
echo "  PUBSUB_PROJECT_ID=briefly-dev"
echo ""
echo "To use in another terminal, run:"
echo "  export PUBSUB_EMULATOR_HOST=localhost:8085"
echo "  export PUBSUB_PROJECT_ID=briefly-dev"
