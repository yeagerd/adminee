#!/bin/bash
set -e

# Set working directory to the project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Parse command line arguments
FRESH_INSTALL=false
RESTART=false
ENV_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --fresh-install)
            FRESH_INSTALL=true
            shift
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fresh-install    Remove existing container and start fresh (WILL DELETE DATA)"
            echo "  --restart          Start existing container if it's stopped"
            echo "  --env-file FILE    REQUIRED: Environment file with database passwords"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --env-file .env.postgres.local # Use local environment"
            echo "  $0 --env-file .env.postgres.staging # Use staging environment"
            echo "  $0 --fresh-install --env-file .env.postgres.local # Fresh start"
            echo "  $0 --restart --env-file .env.postgres.local # Restart existing"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🚀 Starting Briefly PostgreSQL instance..."

# Validate environment file if provided
if [ -n "$ENV_FILE" ]; then
    if [ ! -f "$ENV_FILE" ]; then
        echo "❌ Error: Environment file not found: $ENV_FILE"
        echo "Available environment files:"
        ls -1 .env.postgres.* 2>/dev/null | sed 's/.*\.env\.postgres\.//' | sort || echo "   No environment files found in repo root"
        exit 1
    fi
    echo "📄 Using environment file: $ENV_FILE"
fi

# Build the PostgreSQL image
echo "📦 Building PostgreSQL image..."
docker buildx build -f Dockerfile.postgres -t briefly-postgres .

# Check if container already exists
if docker ps -a | grep -q briefly-postgres || docker ps -a | grep -q briefly-db-1; then
    if [ "$FRESH_INSTALL" = true ]; then
        echo "🧹 Fresh install requested - removing existing container and data..."
        docker stop briefly-postgres 2>/dev/null || true
        docker rm briefly-postgres 2>/dev/null || true
        docker stop briefly-db-1 2>/dev/null || true
        docker rm briefly-db-1 2>/dev/null || true
        docker volume rm briefly_postgres_data 2>/dev/null || true
        echo "✅ Existing container and data removed"

        # Wait a moment for port to be released
        echo "⏳ Waiting for port 5432 to be released..."
        sleep 3
    else
        # Check if any container is running
        if docker ps | grep -q briefly-postgres; then
            echo "📋 Container 'briefly-postgres' is already running"
            echo "   Use --fresh-install to remove and recreate"
            echo "   Use 'docker logs briefly-postgres' to view logs"
            exit 0
        elif docker ps | grep -q briefly-db-1; then
            echo "📋 Container 'briefly-db-1' is already running"
            echo "   Use --fresh-install to remove and recreate"
            echo "   Use 'docker logs briefly-db-1' to view logs"
            exit 0
        else
            # Container exists but is not running
            if [ "$RESTART" = true ]; then
                echo "🔄 Restarting existing container..."
                if docker ps -a | grep -q briefly-postgres; then
                    docker start briefly-postgres
                    echo "✅ Container 'briefly-postgres' started"
                elif docker ps -a | grep -q briefly-db-1; then
                    docker start briefly-db-1
                    echo "✅ Container 'briefly-db-1' started"
                fi
                exit 0
            else
                echo "📋 PostgreSQL container exists but is not running"
                echo "   Use --restart to start the existing container"
                echo "   Use --fresh-install to remove and recreate"
                echo "   Use 'docker start briefly-postgres' or 'docker start briefly-db-1' to start manually"
                exit 0
            fi
        fi
    fi
fi

# Check if port 5432 is already in use (only if we're not doing a fresh install)
if [ "$FRESH_INSTALL" = false ]; then
    if lsof -i :5432 >/dev/null 2>&1; then
        echo "⚠️  Port 5432 is already in use!"
        echo "   This might be another PostgreSQL instance or your existing briefly-db-1 container"
        echo "   Please stop the existing service or use a different port"
        echo ""
        echo "   To stop existing containers:"
        echo "   docker stop briefly-db-1"
        echo "   docker stop briefly-postgres"
        exit 1
    fi
fi

# Start the PostgreSQL container
echo "🔄 Starting PostgreSQL container..."

# Build docker run command
DOCKER_RUN_CMD="docker run -d --name briefly-postgres --network host -v briefly_postgres_data:/var/lib/postgresql/data"

# Add environment file if provided
if [ -n "$ENV_FILE" ]; then
    DOCKER_RUN_CMD="$DOCKER_RUN_CMD --env-file $ENV_FILE"
else
    echo "❌ Error: Environment file is required for security"
    echo "   Please provide an environment file with POSTGRES_USER and POSTGRES_PASSWORD"
    echo "   Example: $0 --env-file .env.postgres.local"
    echo ""
    echo "   Available environment files:"
    ls -1 .env.postgres.* 2>/dev/null | sed 's/.*\.env\.postgres\.//' | sort || echo "   No environment files found in repo root"
    exit 1
fi

# Add image name and execute
DOCKER_RUN_CMD="$DOCKER_RUN_CMD briefly-postgres"
echo "🚀 Executing: $DOCKER_RUN_CMD"
CONTAINER_ID=$(eval $DOCKER_RUN_CMD)

# Check if container started successfully
if [ $? -ne 0 ]; then
    echo "❌ Failed to start PostgreSQL container"
    echo "📋 Container logs:"
    docker logs briefly-postgres 2>/dev/null || echo "   No logs available"
    exit 1
fi

echo "📦 Container started with ID: $CONTAINER_ID"

# Wait for PostgreSQL to be ready with better error handling
echo "⏳ Waiting for PostgreSQL to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Check if container is still running
    if ! docker ps | grep -q briefly-postgres; then
        echo "❌ PostgreSQL container stopped unexpectedly"
        echo "📋 Container logs:"
        docker logs briefly-postgres
        echo ""
        echo "🔍 Container status:"
        docker ps -a | grep briefly-postgres
        exit 1
    fi
    
    # Check if PostgreSQL is ready
    if docker exec briefly-postgres pg_isready -U postgres >/dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo "⏳ PostgreSQL is not ready yet. Waiting... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ PostgreSQL failed to start within $((MAX_ATTEMPTS * 2)) seconds"
    echo "📋 Container logs:"
    docker logs briefly-postgres
    echo ""
    echo "🔍 Container status:"
    docker ps -a | grep briefly-postgres
    exit 1
fi

# Verify that initialization scripts ran successfully
echo "🔍 Verifying database initialization..."
sleep 3  # Give a moment for any final initialization

# Check if service users were created
if ! docker exec briefly-postgres psql -U postgres -d briefly_user -c "SELECT 1 FROM pg_roles WHERE rolname='briefly_user_service';" | grep -q "1 row"; then
    echo "⚠️  Warning: Service users may not have been created properly"
    echo "📋 Recent container logs:"
    docker logs briefly-postgres | tail -20
    echo ""
    echo "💡 This might be normal if the database was already initialized"
fi

# Display connection information
echo ""
echo "📋 Connection Information:"
echo "Host: localhost"
echo "Port: 5432"

# Extract admin credentials from environment file
ADMIN_USER=$(grep "^POSTGRES_USER=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' || echo "postgres")
ADMIN_PASSWORD=$(grep "^POSTGRES_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' || echo "postgres")
echo "Admin User: $ADMIN_USER"
echo "Admin Password: $ADMIN_PASSWORD"

# Show environment file info if used
if [ -n "$ENV_FILE" ]; then
    echo ""
    echo "🔧 Environment Configuration:"
    echo "Environment file: $ENV_FILE"
    echo "Database passwords are configured via environment variables"
fi

echo ""
echo "🗄️ Available Databases:"
echo "- briefly_user (User service)"
echo "- briefly_meetings (Meetings service)"
echo "- briefly_shipments (Shipments service)"
echo "- briefly_office (Office service)"
echo "- briefly_chat (Chat service)"
echo "- briefly_vector (Vector service)"
echo ""
echo "🔑 Service-specific users:"
echo "Passwords configured via environment variables from: $ENV_FILE"
echo "Users: briefly_user_service, briefly_meetings_service, briefly_shipments_service,"
echo "       briefly_office_service, briefly_chat_service, briefly_vector_service"
echo ""
echo "💡 To connect to a specific database:"
echo "psql -h localhost -p 5432 -U postgres -d briefly_user"
echo ""
echo "🛑 To stop: ./scripts/stop-postgres.sh"
echo "🗑️ To remove: ./scripts/stop-postgres.sh --remove"
echo "🔄 To start fresh: $0 --fresh-install --env-file $ENV_FILE"
echo "🔧 To restart with same environment: $0 --env-file $ENV_FILE"
