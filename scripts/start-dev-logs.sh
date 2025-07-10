#!/bin/bash

# Start services with human-readable logging for development
# This makes logs much easier to read during development

echo "🚀 Starting Briefly services with human-readable logs..."
echo "   (For production JSON logs, use ./start-all-services.sh instead)"
echo ""

# Set environment variables for human-readable logging
export LOG_FORMAT=text
export LOG_LEVEL=INFO

# Start all services
./start-all-services.sh

echo ""
echo "📝 Log format set to 'text' for easier reading"
echo "🔍 To see debug logs: export LOG_LEVEL=DEBUG"
echo "🔄 To switch to JSON logs: export LOG_FORMAT=json" 