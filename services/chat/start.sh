#!/bin/bash

# Chat Service Startup Script with UV
# This script runs uvicorn from the repo root to ensure proper package imports

cd "$(dirname "$0")/../.."

# Activate the virtual environment if it exists
if [ -d "../../.venv" ]; then
    source ../../.venv/bin/activate
fi

# Run uvicorn with UV for better performance
uv run python -m uvicorn services.chat.main:app --port 8001 --host 0.0.0.0 --env-file .env "$@"
