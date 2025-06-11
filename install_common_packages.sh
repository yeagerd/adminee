#!/bin/bash

# Install common and vector-db packages in editable mode for all services
# This script should be run from the repository root

set -e

echo "Installing common and vector-db packages in editable mode for all services..."

SERVICES=("office_service" "chat_service" "user_management")

for service in "${SERVICES[@]}"; do
    echo "Installing packages for $service..."
    
    if [ -d "services/$service/venv" ]; then
        cd "services/$service"
        
        # Activate virtual environment and install packages
        source venv/bin/activate
        
        echo "  Installing common package..."
        pip install -e ../common --force-reinstall
        
        echo "  Installing vector-db package..."
        pip install -e ../vector-db --force-reinstall
        
        deactivate
        cd ../..
        
        echo "  ✓ $service packages installed"
    else
        echo "  ⚠️  Virtual environment not found for $service"
    fi
done

echo "✓ All packages installed successfully!"
echo ""
echo "You can now import these packages in your services:"
echo "  from common.telemetry import ..."
echo "  from vector_db.pinecone_client import ..." 