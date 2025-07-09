#!/bin/bash

# Briefly Development Setup Script with UV
# This script sets up the development environment using UV for faster dependency management

set -e

echo "🚀 Setting up Briefly development environment with UV..."

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ UV installed successfully!"
    echo "Please restart your terminal or run: source ~/.bashrc"
    exit 1
fi

echo "✅ UV is already installed"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install all workspace and dev dependencies
echo "📥 Installing all workspace and development dependencies..."
uv sync --all-packages --all-extras --active

# Run database migrations from repository root
echo "🗄️ Setting up databases..."
alembic -c services/user/alembic.ini upgrade head
alembic -c services/chat/alembic.ini upgrade head
alembic -c services/office/alembic.ini upgrade head

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Copy .env.example to .env and configure your environment variables"
echo "  2. Start services with: ./scripts/start-services.sh"
echo "  3. Run tests with: uv run tox"
echo "  4. Run linting with: uv run tox -e lint"
echo ""
echo "🚀 Happy coding!" 