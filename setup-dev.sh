#!/bin/bash

# Development setup script for Briefly
# Creates a single virtual environment with merged requirements from all services

set -e

echo "🚀 Setting up unified development environment for Briefly"

# Create main project venv (unified for all services)
echo "📦 Creating unified virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Create temporary merged requirements file
echo "📋 Merging requirements from all services..."
TEMP_REQUIREMENTS=$(mktemp)

# Add header comment
echo "# Merged requirements from all services and root" > "$TEMP_REQUIREMENTS"
echo "" >> "$TEMP_REQUIREMENTS"

# Add root requirements
echo "# Root requirements" >> "$TEMP_REQUIREMENTS"
cat requirements.txt >> "$TEMP_REQUIREMENTS"
echo "" >> "$TEMP_REQUIREMENTS"

# Dynamically find all services with requirements.txt files
echo "🔍 Discovering services with requirements.txt files..."
for service_req_file in services/*/requirements.txt; do
    if [ -f "$service_req_file" ]; then
        service_name=$(basename "$(dirname "$service_req_file")")
        echo "  Found: $service_name"
        echo "# $service_name requirements" >> "$TEMP_REQUIREMENTS"
        cat "$service_req_file" >> "$TEMP_REQUIREMENTS"
        echo "" >> "$TEMP_REQUIREMENTS"
    fi
done

echo "📦 Installing merged requirements into unified environment..."
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install merged requirements, removing duplicates with pip's built-in deduplication
pip install -r "$TEMP_REQUIREMENTS"

# Install shared packages in editable mode
echo "📦 Installing shared packages in editable mode..."

# Dynamically find and install shared packages (common, vector-db, etc.)
for shared_package in services/common services/vector-db; do
    if [ -d "$shared_package" ] && [ -f "$shared_package/pyproject.toml" ]; then
        package_name=$(basename "$shared_package")
        echo "  Installing $package_name package..."
        pip install -e "$shared_package" --force-reinstall
    fi
done

# Clean up temporary file
rm "$TEMP_REQUIREMENTS"

echo ""
echo "✅ Unified development environment setup complete!"
echo ""
echo "📂 Virtual environment activated"
echo ""
echo "🎯 Next steps:"
echo "  • Run 'tox' from repo root to validate full test matrix"
echo "  • Run 'pytest' in any service directory to run tests"
echo "  • Run 'mypy services/' to check types"
echo ""
echo "💡 All services now use the same virtual environment!"
echo "   You can work on any service without switching environments."
echo ""
echo "📦 Shared packages available in all services:"
echo "  from common.telemetry import setup_telemetry, get_tracer"
echo "  from vector_db.pinecone_client import PineconeClient"
