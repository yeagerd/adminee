#!/bin/bash

# Development setup script for Briefly
# Creates virtual environments for each service

set -e

echo "🚀 Setting up development environment for Briefly"

# Create main project venv (for tox, linting, etc.)
echo "📦 Creating main project virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create service-specific virtual environments
echo "📦 Setting up service virtual environments..."

# User Management Service
echo "  - User Management Service"
cd services/user_management
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../..

# Chat Service
echo "  - Chat Service"
cd services/chat_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../..

# Office Service
echo "  - Office Service"
cd services/office_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../..

echo "✅ Development environment setup complete!"
echo ""
echo "To activate environments:"
echo "  Main project: source venv/bin/activate"
echo "  User Management: cd services/user_management && source venv/bin/activate"
echo "  Chat Service: cd services/chat_service && source venv/bin/activate"
echo "  Office Service: cd services/office_service && source venv/bin/activate" 