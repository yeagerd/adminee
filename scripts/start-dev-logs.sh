#!/bin/bash

# Start services with human-readable logging for development
# This makes logs much easier to read during development

echo "🚀 Starting Briefly services with human-readable logs..."
echo "   (This script now waits for processes - use Ctrl+C to stop all services)"
echo ""

# Set environment variables for human-readable logging
export LOG_FORMAT=text
export LOG_LEVEL=INFO

# Get the directory where this script is located
SCRIPT_DIR="$(dirname "$0")"

# Start all services (now with proper process management and waiting)
# Pass through all command line arguments and pipe through color filtering
"$SCRIPT_DIR/start-all-services.sh" "$@" 2>&1 | perl -pe "
    s/\[WARNING\]/$(printf '\033[1;33m')[WARNING]$(printf '\033[0m')/g;
    s/\[ERROR\]/$(printf '\033[0;31m')[ERROR]$(printf '\033[0m')/g;
"

echo ""
echo "📝 Log format set to 'text' for easier reading"
echo "🔍 To see debug logs: export LOG_LEVEL=DEBUG"
echo "🔄 To switch to JSON logs: export LOG_FORMAT=json" 