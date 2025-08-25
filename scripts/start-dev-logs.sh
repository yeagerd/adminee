#!/bin/bash

# Start services with human-readable logging for development
# This makes logs much easier to read during development

# Parse command line arguments
FORCE_KILL=false
ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_KILL=true
            ARGS+=("$1")  # Pass through the --force argument
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force         Kill port-conflicting services instead of exiting"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0              Start services normally (exit if ports conflict)"
            echo "  $0 --force      Start services, killing any port conflicts"
            exit 0
            ;;
        *)
            # Pass through all other arguments to start-all-services.sh
            ARGS+=("$1")
            shift
            ;;
    esac
done

echo "🚀 Starting Briefly services with human-readable logs..."
if [ "$FORCE_KILL" = true ]; then
    echo "   ⚠️  Force mode enabled - will kill port-conflicting services"
fi
echo "   (This script now waits for processes - use Ctrl+C to stop all services)"
echo ""

# Set environment variables for human-readable logging
export LOG_FORMAT=text
export LOG_LEVEL=INFO

# Get the directory where this script is located
SCRIPT_DIR="$(dirname "$0")"

# Start all services (now with proper process management and waiting)
# Pass through all command line arguments including --force
"$SCRIPT_DIR/start-all-services.sh" "${ARGS[@]}"

echo ""
echo "📝 Log format set to 'text' for easier reading"
echo "🔍 To see debug logs: export LOG_LEVEL=DEBUG"
echo "🔄 To switch to JSON logs: export LOG_FORMAT=json" 