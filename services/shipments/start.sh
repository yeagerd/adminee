#!/bin/bash

# Start the Briefly Shipments Service
# This script runs uvicorn from the repo root to ensure proper package imports

cd "$(dirname "$0")/../.."

# Activate the virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

uv run python -m uvicorn services.shipments.main:app --host 0.0.0.0 --port 8004 --reload --reload-dir services/shipments --reload-dir services/common
