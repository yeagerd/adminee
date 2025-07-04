#!/bin/bash

# Chat Service Startup Script
# This script runs uvicorn from the repo root to ensure proper package imports

cd "$(dirname "$0")/../.."

# Activate the unified virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run uvicorn with proper package path
python -m uvicorn services.chat.main:app --port 8002 --host 0.0.0.0 --env-file .env "$@"
