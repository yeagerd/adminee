#!/bin/bash

# Office Service Startup Script
# This script runs uvicorn from the repo root to ensure proper package imports

cd "$(dirname "$0")/../.."

# Activate the virtual environment if it exists
if [ -d "services/user_management/venv" ]; then
    source services/user_management/venv/bin/activate
fi

# Run uvicorn with proper package path
python -m uvicorn services.office_service.app.main:app --port 8002 --host 0.0.0.0 --env-file .env "$@" 