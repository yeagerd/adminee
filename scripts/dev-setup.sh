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
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install all dependencies
echo "📥 Installing project dependencies..."
uv pip install -e .
uv pip install -e services/chat
uv pip install -e services/user
uv pip install -e services/office
uv pip install -e services/common
uv pip install -e services/vector-db

# Install development dependencies
echo "🔧 Installing development dependencies..."
uv pip install -e ".[dev]"

# Run database migrations
echo "🗄️ Setting up databases..."
cd services/user && alembic upgrade head && cd ../..
cd services/chat && alembic upgrade head && cd ../..
cd services/office && alembic upgrade head && cd ../..

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Copy .env.example to .env and configure your environment variables"
echo "  2. Start services with: ./scripts/start-services.sh"
echo "  3. Run tests with: uv run tox"
echo "  4. Run linting with: uv run tox -e lint"
echo ""
echo "🚀 Happy coding!" 