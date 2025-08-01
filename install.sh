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

# Install all workspace and dev dependencies
echo "📥 Installing all workspace and development dependencies..."
uv sync --all-packages --all-extras --active
uv pip install -e services/meetings

# Check database status and run migrations if needed
echo "🗄️ Checking database status..."
if ./scripts/check-db-status.sh; then
    echo "✅ Database is ready!"
else
    echo "📦 Database needs setup. Running migrations..."
    ./scripts/run-migrations.sh
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Run `source .venv/bin/activate` to activate the virtual environment"
echo "  2. Copy .env.example to .env and configure your environment variables"
echo "  3. Start PostgreSQL with: ./scripts/postgres-start.sh"
echo "  4. Check database status with: ./scripts/check-db-status.sh"
echo "  5. Start services with: ./scripts/start-services.sh"
echo "  6. Run tests with: nox -s test"
echo "  7. Run linting with: nox -s lint"
echo ""
echo "🚀 Happy coding!" 