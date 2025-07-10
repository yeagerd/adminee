#!/bin/bash

# Briefly Service Startup Script with UV
# This script starts all services using UV for better performance

set -e

echo "🚀 Starting Briefly services with UV..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Function to start a service
start_service() {
    local service_name=$1
    local module_path=$2
    local port=$3
    local host=${4:-"0.0.0.0"}
    
    echo "🔄 Starting $service_name on port $port..."
    
    # Start service in background
    uv run python -m uvicorn $module_path --host $host --port $port --reload &
    local pid=$!
    
    # Store PID for cleanup
    echo $pid > /tmp/briefly-$service_name.pid
    
    echo "✅ $service_name started with PID $pid"
    sleep 2
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    
    for pid_file in /tmp/briefly-*.pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            local service_name=$(basename "$pid_file" .pid | sed 's/briefly-//')
            
            if kill -0 $pid 2>/dev/null; then
                echo "🛑 Stopping $service_name (PID: $pid)..."
                kill $pid
                wait $pid 2>/dev/null || true
            fi
            
            rm -f "$pid_file"
        fi
    done
    
    echo "✅ All services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start services
echo "📡 Starting all services..."

# Start User Management Service
start_service "user-management" "services.user.main:app" 8001

# Start Chat Service  
start_service "chat-service" "services.chat.main:app" 8002

# Start Office Service
start_service "office-service" "services.office.app.main:app" 8003

echo ""
echo "🎉 All services started successfully!"
echo ""
echo "📋 Service URLs:"
echo "   • User Management: http://localhost:8001"
echo "   • Chat Service:     http://localhost:8002"
echo "   • Office Service:   http://localhost:8003"
echo ""
echo "🔍 Health checks:"
echo "   • User Management: http://localhost:8001/health"
echo "   • Chat Service:     http://localhost:8002/health"
echo "   • Office Service:   http://localhost:8003/health"
echo ""
echo "⏹️  Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait 