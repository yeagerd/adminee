#!/bin/bash
set -e

# Set working directory to the project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Parse command line arguments
CHECK_ONLY=false
ENV_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --check)
            CHECK_ONLY=true
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
            echo "  --check            Check migration status without running migrations"
            echo "  --env-file FILE    REQUIRED: Environment file with database passwords"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --env-file .env.postgres.local                    # Run migrations"
            echo "  $0 --check --env-file .env.postgres.local           # Check status"
            echo "  $0 --env-file .env.postgres.staging                 # Run on staging"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate environment file
if [ -z "$ENV_FILE" ]; then
    echo "❌ Error: Environment file is required for security"
    echo "   Please provide an environment file with database passwords"
    echo "   Example: $0 --env-file .env.postgres.local"
    echo ""
    echo "   Available environment files:"
    ls -1 .env.postgres.* 2>/dev/null | sed 's/.*\.env\.postgres\.//' | sort || echo "   No environment files found in repo root"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file not found: $ENV_FILE"
    echo "Available environment files:"
    ls -1 .env.postgres.* 2>/dev/null | sed 's/.*\.env\.postgres\.//' | sort || echo "   No environment files found in repo root"
    exit 1
fi

echo "📄 Using environment file: $ENV_FILE"

# Load environment variables from the provided file
echo "📄 Loading environment from: $ENV_FILE"
source "$ENV_FILE"

# Set up database URLs using environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432

# Service-specific database URLs using environment passwords
export DB_URL_USER=postgresql://briefly_user_service:${BRIEFLY_USER_SERVICE_PASSWORD:-briefly_user_pass}@localhost:5432/briefly_user
export DB_URL_MEETINGS=postgresql://briefly_meetings_service:${BRIEFLY_MEETINGS_SERVICE_PASSWORD:-briefly_meetings_pass}@localhost:5432/briefly_meetings
export DB_URL_SHIPMENTS=postgresql://briefly_shipments_service:${BRIEFLY_SHIPMENTS_SERVICE_PASSWORD:-briefly_shipments_pass}@localhost:5432/briefly_shipments
export DB_URL_OFFICE=postgresql://briefly_office_service:${BRIEFLY_OFFICE_SERVICE_PASSWORD:-briefly_office_pass}@localhost:5432/briefly_office
export DB_URL_CHAT=postgresql://briefly_chat_service:${BRIEFLY_CHAT_SERVICE_PASSWORD:-briefly_chat_pass}@localhost:5432/briefly_chat
export DB_URL_VECTOR=postgresql://briefly_vector_service:${BRIEFLY_VECTOR_SERVICE_PASSWORD:-briefly_vector_pass}@localhost:5432/briefly_vector

# For Alembic migrations (using admin user from env file)
export DB_URL_USER_MIGRATIONS=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@localhost:5432/briefly_user
export DB_URL_MEETINGS_MIGRATIONS=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@localhost:5432/briefly_meetings
export DB_URL_SHIPMENTS_MIGRATIONS=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@localhost:5432/briefly_shipments
export DB_URL_OFFICE_MIGRATIONS=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@localhost:5432/briefly_office
export DB_URL_CHAT_MIGRATIONS=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@localhost:5432/briefly_chat
export DB_URL_VECTOR_MIGRATIONS=postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@localhost:5432/briefly_vector

echo "✅ Environment variables loaded from $ENV_FILE"

# Check if --check flag is provided
if [ "$CHECK_ONLY" = true ]; then
    echo "🔍 Checking Alembic migration status for all services..."
else
    echo "🗄️ Running Alembic migrations for all services..."
fi

# Function to run migrations for a service
run_service_migrations() {
    local service_name=$1
    local migration_url=$2

    echo "📦 Checking migrations for $service_name..."

    # Set the database URL for this service
    export DB_URL=$migration_url

    if [ "$CHECK_ONLY" = true ]; then
        # Check current migration revision
        current_rev=$(alembic -c services/$service_name/alembic.ini current 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")

        # Check head migration revision
        head_rev=$(alembic -c services/$service_name/alembic.ini heads 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")

        if [ "$current_rev" = "$head_rev" ] && [ "$current_rev" != "none" ]; then
            echo "✅ $service_name: Up to date (revision: $current_rev)"
        else
            echo "❌ $service_name: Out of date"
            echo "   Current: $current_rev"
            echo "   Head: $head_rev"
        fi
    else
        # Check if this is a fresh database (no migration history)
        current_rev=$(alembic -c services/$service_name/alembic.ini current 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")
        
        # Handle case where alembic command fails (fresh database)
        if [[ "$current_rev" == *"FAILED:"* ]] || [ "$current_rev" = "none" ] || [ -z "$current_rev" ]; then
            echo "🆕 Fresh database detected - running migrations..."
            alembic -c services/$service_name/alembic.ini upgrade head
            echo "✅ $service_name migrations completed"
        else
            # Run migrations
            alembic -c services/$service_name/alembic.ini upgrade head
            echo "✅ $service_name migrations completed"
        fi
    fi
}

# Run migrations for each service
run_service_migrations "user" "$DB_URL_USER_MIGRATIONS"
run_service_migrations "meetings" "$DB_URL_MEETINGS_MIGRATIONS"
run_service_migrations "shipments" "$DB_URL_SHIPMENTS_MIGRATIONS"
run_service_migrations "office" "$DB_URL_OFFICE_MIGRATIONS"
run_service_migrations "chat" "$DB_URL_CHAT_MIGRATIONS"

if [ "$CHECK_ONLY" = true ]; then
    echo ""
    echo "🔍 Migration check completed!"
    echo ""
    echo "💡 To run migrations, use: ./scripts/run-migrations.sh"
else
    echo "🎉 All migrations completed successfully!"
    
    echo ""
    echo "📋 Database Status:"
    echo "  - briefly_user: Ready"
    echo "  - briefly_meetings: Ready"
    echo "  - briefly_shipments: Ready"
    echo "  - briefly_office: Ready"
    echo "  - briefly_chat: Ready"
fi
