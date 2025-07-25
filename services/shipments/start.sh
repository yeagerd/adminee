#!/bin/bash

# Start the Briefly Shipments Service

uv run python -m uvicorn services.shipments.main:app --host 0.0.0.0 --port 8004 --reload --reload-dir services/shipments --reload-dir services/common
