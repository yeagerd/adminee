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

# Check database status and handle different scenarios
echo "🗄️ Checking database status..."

# Parse command line arguments
ENV_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Usage: $0 [--env-file <file>]"
            exit 1
            ;;
    esac
done

# If no env file specified, default to .env
if [ -z "$ENV_FILE" ]; then
    ENV_FILE=".env"
fi

# Check if the specified environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file not found: $ENV_FILE"
    echo "   Please create a .env file based on .example.env"
    echo "   Example: cp .example.env .env"
    exit 1
fi

echo "📄 Using environment file: $ENV_FILE"
./scripts/check-db-status.sh --env-file "$ENV_FILE"

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
echo "  2. Copy .example.env to .env and configure your environment variables" 