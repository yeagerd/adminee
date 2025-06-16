#!/bin/bash

# User Management Service Startup Script
# This script runs uvicorn from the repo root to ensure proper package imports

cd "$(dirname "$0")/../.."

# Activate the unified virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run uvicorn with proper package path
python -m uvicorn services.user.main:app --port 8000 --host 0.0.0.0 --env-file .env "$@" 