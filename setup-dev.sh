#!/bin/bash

# Development setup script for Briefly
# Creates virtual environments for each service and installs shared packages

set -e

echo "🚀 Setting up development environment for Briefly"

# Create main project venv (for tox, linting, etc.)
echo "📦 Creating main project virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Service configuration
SERVICES=("user_management" "chat_service" "office_service")

# Create service-specific virtual environments
echo "📦 Setting up service virtual environments..."

for service in "${SERVICES[@]}"; do
    echo "  - $service"
    cd "services/$service"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Install service requirements
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    
    cd ../..
done

# Install shared packages in editable mode
echo "📦 Installing shared packages in editable mode..."

for service in "${SERVICES[@]}"; do
    echo "  Installing shared packages for $service..."
    
    if [ -d "services/$service/venv" ]; then
        cd "services/$service"
        
        # Activate virtual environment and install shared packages
        source venv/bin/activate
        
        echo "    Installing common package..."
        pip install -e ../common --force-reinstall
        
        echo "    Installing vector-db package..."
        pip install -e ../vector-db --force-reinstall
        
        deactivate
        cd ../..
        
        echo "    ✓ $service shared packages installed"
    else
        echo "    ⚠️  Virtual environment not found for $service"
    fi
done

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  • Run 'tox' from repo root to validate full test matrix"
echo "  • Run 'pytest' in any service directory to run tests"
echo "  • Run 'mypy services/' to check types"
echo ""
echo "📂 To activate environments:"
echo "  Main project: source venv/bin/activate"
echo "  User Management: cd services/user_management && source venv/bin/activate"
echo "  Chat Service: cd services/chat_service && source venv/bin/activate"
echo "  Office Service: cd services/office_service && source venv/bin/activate"
echo ""
echo "📦 Shared packages available in all services:"
echo "  from common.telemetry import setup_telemetry, get_tracer"
echo "  from vector_db.pinecone_client import PineconeClient" 