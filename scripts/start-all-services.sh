#!/bin/bash

# Start All Services Script
# This script starts the gateway, frontend, and all backend services with proper process management

set -e

# Parse command line arguments
SKIP_FRONTEND=true
SERIAL_START=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --frontend)
            SKIP_FRONTEND=false
            shift
            ;;
        --serial)
            SERIAL_START=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --frontend       Start the frontend along with backend services"
            echo "  --serial         Start services sequentially instead of simultaneously"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0               Start backend services simultaneously (fastest), run frontend separately"
            echo "  $0 --frontend    Start all services simultaneously including frontend"
            echo "  $0 --serial      Start all services sequentially (better for debugging)"
            echo "  $0 --frontend --serial  Start all services sequentially including frontend"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Ensure we're in the project root (parent of where this script is located)
cd "$(dirname "$0")/.."

# Service configuration
declare -a SERVICES=(
    "user-service:services.user.main:app:8001"
    "chat-service:services.chat.main:app:8002"
    "office-service:services.office.app.main:app:8003"
    "shipments-service:services.shipments.main:app:8004"
    "meetings-service:services.meetings.main:app:8005"
    "vespa-loader-service:services.vespa_loader.main:app:9001"
    "vespa-query-service:services.vespa_query.main:app:8006"
    "contacts-service:services.contacts.main:app:8007"
)

echo "🚀 Starting all Briefly services..."
if [ "$SKIP_FRONTEND" = true ]; then
    echo "📱 Frontend will be skipped (backend services only)"
else
    echo "📱 Frontend will be started along with backend services"
fi
if [ "$SERIAL_START" = true ]; then
    echo "⏳ Services will be started sequentially"
else
    echo "⚡ Services will be started simultaneously (fastest startup)"
fi
echo "📁 Working directory: $(pwd)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use and provide helpful info
check_port() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid=$(lsof -Pi :$port -sTCP:LISTEN -t)
        local process_info=$(ps -p $pid -o pid,ppid,command --no-headers 2>/dev/null || echo "Unknown process")
        
        echo -e "${RED}❌ Port $port is already in use by $service_name${NC}"
        echo -e "${YELLOW}   Process ID: $pid${NC}"
        echo -e "${YELLOW}   Process Info: $process_info${NC}"
        echo -e "${YELLOW}   To kill the process:${NC}"
        echo -e "${YELLOW}     kill $pid${NC}"
        echo -e "${YELLOW}     or${NC}"
        echo -e "${YELLOW}     lsof -ti:$port | xargs kill${NC}"
        echo ""
        return 1
    fi
    return 0
}

# Function to wait for a service to be ready (single attempt, short timeout)
wait_for_service() {
    local service_name=$1
    local url=$2
    local timeout=${3:-10}  # Default 10 second timeout
    
    echo -e "${BLUE}⏳ Waiting for $service_name to be ready (timeout: ${timeout}s)...${NC}"
    
    local start_time=$(date +%s)
    while true; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $timeout ]; then
            echo -e "${RED}❌ $service_name failed to start within ${timeout} seconds${NC}"
            return 1
        fi
        
        sleep 1
    done
}

# Check if required tools are installed
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Please run ./install.sh first${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if ports are already in use
echo -e "${BLUE}🔍 Checking if ports are available...${NC}"

check_port 3001 "Gateway" || exit 1
for service_config in "${SERVICES[@]}"; do
    IFS=':' read -r service_name module_path port <<< "$service_config"
    check_port "$port" "$service_name" || exit 1
done

if [ "$SKIP_FRONTEND" = false ]; then
    check_port 3000 "Frontend" || exit 1
fi

echo -e "${GREEN}✅ All required ports are available${NC}"

# Function to start a Python service
start_python_service() {
    local service_name=$1
    local module_path=$2
    local port=$3
    local host=${4:-"0.0.0.0"}

    # Extract reload directory from module_path (e.g., services.chat.main -> services/chat)
    local reload_dir=$(echo $module_path | awk -F. '{print $1 "/" $2}')

    echo -e "${BLUE}🔄 Starting $service_name on port $port...${NC}"

    # Start service in background, only watching the service directory and services/common for reloads
    # Disable uvicorn access logs since we handle request logging in our middleware
    uv run python -m uvicorn $module_path --host $host --port $port --reload --reload-dir $reload_dir --reload-dir services/common --no-access-log &
    local pid=$!
    
    # Store PID for cleanup
    echo $pid > /tmp/briefly-$service_name.pid
    
    echo -e "${GREEN}✅ $service_name started with PID $pid${NC}"
    sleep 2
}

# Function to start a Node.js service
start_node_service() {
    local service_name=$1
    local directory=$2
    local port=$3
    
    echo -e "${BLUE}🔄 Starting $service_name on port $port...${NC}"
    
    # Change to service directory and start
    cd $directory
    npm run dev &
    local pid=$!
    cd - > /dev/null
    
    # Store PID for cleanup
    echo $pid > /tmp/briefly-$service_name.pid
    
    echo -e "${GREEN}✅ $service_name started with PID $pid${NC}"
    sleep 2
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping all services...${NC}"
    
    # Kill all background processes started by this script
    jobs -p | xargs -r kill 2>/dev/null || true
    
    # Kill processes from PID files
    for pid_file in /tmp/briefly-*.pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            local service_name=$(basename "$pid_file" .pid | sed 's/briefly-//')
            
            if kill -0 $pid 2>/dev/null; then
                echo -e "${YELLOW}🛑 Stopping $service_name (PID: $pid)...${NC}"
                kill $pid 2>/dev/null || true
                # Give it a moment to shut down gracefully
                sleep 1
                # Force kill if still running
                kill -9 $pid 2>/dev/null || true
            fi
            
            rm -f "$pid_file"
        fi
    done
    
    # Kill any remaining processes on our ports (only for services we started)
    local ports_to_kill="3001"
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name module_path port <<< "$service_config"
        ports_to_kill="$ports_to_kill $port"
    done
    if [ "$SKIP_FRONTEND" = false ]; then
        ports_to_kill="$ports_to_kill 3000"
    fi

    for port in $ports_to_kill; do
        lsof -ti:$port 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    done
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Set up signal handlers for proper Ctrl+C handling
trap cleanup SIGINT SIGTERM

# Start all services
if [ "$SERIAL_START" = true ]; then
    echo -e "${BLUE}🔧 Starting all services sequentially...${NC}"
    
    # Start all Python services sequentially
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name module_path port <<< "$service_config"
        start_python_service "$service_name" "$module_path" "$port"
        wait_for_service "$service_name" "http://localhost:$port/health"
    done
    
    # Start Gateway
    echo -e "${BLUE}🚀 Starting Express Gateway...${NC}"
    ./scripts/gateway-start.sh &
    GATEWAY_PID=$!
    echo $GATEWAY_PID > /tmp/briefly-gateway.pid
    wait_for_service "Gateway" "http://localhost:3001/health"
    
    # Start Frontend (if not skipped)
    if [ "$SKIP_FRONTEND" = false ]; then
        echo -e "${BLUE}🚀 Starting Frontend...${NC}"
        start_node_service "frontend" "frontend" 3000
        wait_for_service "Frontend" "http://localhost:3000"
    else
        echo -e "${YELLOW}📱 Frontend skipped - start it separately with:${NC}"
        echo -e "${YELLOW}   cd frontend && npm run dev${NC}"
    fi
    
else
    echo -e "${BLUE}🔧 Starting all services simultaneously (aggressive parallel)...${NC}"
    
    # Start all Python services simultaneously
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name module_path port <<< "$service_config"
        start_python_service "$service_name" "$module_path" "$port" &
    done
    
    # Start Gateway
    echo -e "${BLUE}🚀 Starting Express Gateway...${NC}"
    ./scripts/gateway-start.sh &
    GATEWAY_PID=$!
    echo $GATEWAY_PID > /tmp/briefly-gateway.pid
    
    # Start Frontend (if not skipped)
    if [ "$SKIP_FRONTEND" = false ]; then
        echo -e "${BLUE}🚀 Starting Frontend...${NC}"
        start_node_service "frontend" "frontend" 3000 &
    else
        echo -e "${YELLOW}📱 Frontend skipped - start it separately with:${NC}"
        echo -e "${YELLOW}   cd frontend && npm run dev${NC}"
    fi
    
    # Wait for all services to be ready
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name module_path port <<< "$service_config"
        wait_for_service "$service_name" "http://localhost:$port/health"
    done
    wait_for_service "Gateway" "http://localhost:3001/health"

    if [ "$SKIP_FRONTEND" = false ]; then
        wait_for_service "Frontend" "http://localhost:3000"
    fi
fi

# Wait for all services to be ready (only needed for serial mode)
if [ "$SERIAL_START" = true ]; then
    echo -e "${BLUE}⏳ All services started sequentially - they should be ready${NC}"
else
    echo -e "${BLUE}⚡ All services started simultaneously - they will be ready shortly${NC}"
fi

# Display service status
if [ "$SERIAL_START" = true ]; then
    echo -e "${GREEN}🎉 All services started successfully in sequence!${NC}"
else
    echo -e "${GREEN}🎉 All services started successfully simultaneously!${NC}"
fi
echo ""
echo -e "${BLUE}📋 Service Status:${NC}"
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "   Frontend:     ${GREEN}http://localhost:3000${NC}"
else
    echo -e "   Frontend:     ${YELLOW}Not started (use --frontend flag)${NC}"
fi
echo -e "   Gateway:      ${GREEN}http://localhost:3001${NC}"
for service_config in "${SERVICES[@]}"; do
    IFS=':' read -r service_name module_path port <<< "$service_config"
    # Convert service-name to display name (e.g., "user-service" -> "User Service")
    local display_name=$(echo "$service_name" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
    echo -e "   $display_name: ${GREEN}http://localhost:$port${NC}"
done
echo ""
echo -e "${BLUE}🔗 Quick Links:${NC}"
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "   App:          ${GREEN}http://localhost:3000${NC}"
else
    echo -e "   App:          ${YELLOW}Start frontend separately: cd frontend && npm run dev${NC}"
fi
echo -e "   Gateway Health: ${GREEN}http://localhost:3001/health${NC}"
echo -e "   API Docs:     ${GREEN}http://localhost:8001/docs${NC}"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo -e "   - Use Ctrl+C to stop all services"
echo -e "   - Check logs in individual service directories"
echo -e "   - Gateway provides centralized auth and security"
if [ "$SERIAL_START" = true ]; then
    echo -e "   - Services started sequentially for better debugging"
else
    echo -e "   - Services started simultaneously for fastest startup (no health checks)"
fi
if [ "$SKIP_FRONTEND" = true ]; then
    echo -e "   - Frontend is not managed by this script - restart it separately"
fi
echo ""

# Wait for all background processes - this allows Ctrl+C to work
echo -e "${BLUE}🔄 All services running. Press Ctrl+C to stop.${NC}"
wait 