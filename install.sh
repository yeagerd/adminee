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

# Check database status and handle different scenarios
echo "🗄️ Checking database status..."
./scripts/check-db-status.sh
db_status=$?

case $db_status in
    0)
        echo "✅ Database is ready!"
        ;;
    1)
        echo "🚨 PostgreSQL is not running. Please start it first:"
        echo "   ./scripts/postgres-start.sh"
        exit 1
        ;;
    2)
        echo "🚨 Database connection errors detected. Check PostgreSQL logs:"
        echo "   docker logs briefly-postgres"
        exit 1
        ;;
    3)
        echo "📦 Database needs migrations. Running migrations..."
        ./scripts/run-migrations.sh
        ;;
    *)
        echo "❌ Unknown database status error (exit code: $db_status)"
        exit 1
        ;;
esac

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