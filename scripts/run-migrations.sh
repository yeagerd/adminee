#!/bin/bash
set -e

# Database Migration Runner
# 
# This script runs Alembic migrations for all services.
# 
# Exit codes:
#   0 - All migrations completed successfully
#   1 - Error during migration execution
#
# Usage:
#   ./scripts/run-migrations.sh [--env-file .env.postgres.local] [--check]
#
# Options:
#   --env-file FILE    Environment file with database passwords (optional)
#   --check            Only check migration status, don't run migrations
#   -h, --help         Show this help message

# Set working directory to the project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Parse command line arguments
ENV_FILE=""
CHECK_ONLY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --env-file FILE    Environment file with database passwords (optional)"
            echo "  --check            Only check migration status, don't run migrations"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run all migrations"
            echo "  $0 --check                           # Check migration status only"
            echo "  $0 --env-file .env.postgres.local    # Use local environment"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Load environment variables
if [ -n "$ENV_FILE" ]; then
    if [ ! -f "$ENV_FILE" ]; then
        echo "❌ Error: Environment file not found: $ENV_FILE"
        exit 1
    fi
    source "$ENV_FILE"
    echo "✅ Environment variables loaded from $ENV_FILE"
else
    # Use default hardcoded credentials for local development
    echo "📄 Using default credentials for local development"
    # No need to source postgres-env.sh anymore - PostgresURLs will handle this
fi

# Set up basic database connection info
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432

echo "✅ Environment variables loaded"

# Check if --check flag is provided
if [ "$CHECK_ONLY" = true ]; then
    echo "🔍 Checking Alembic migration status for all services..."
else
    echo "🗄️ Running Alembic migrations for all services..."
fi

# Function to run migrations for a service
run_service_migrations() {
    local service_name=$1

    echo "📦 Checking migrations for $service_name..."

    # Use PostgresURLs to get the migration URL dynamically
    local migration_url
    migration_url=$(python3 -c "
from services.common.postgres_urls import PostgresURLs
urls = PostgresURLs()
print(urls.get_migration_url('$service_name'))
" 2>/dev/null)

    if [ $? -ne 0 ] || [ -z "$migration_url" ]; then
        echo "❌ Failed to get migration URL for $service_name"
        return 1
    fi

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
        # Run migrations
        alembic -c services/$service_name/alembic.ini upgrade head
        echo "✅ $service_name migrations completed"
        
        # Grant permissions on existing tables after migrations
        echo "🔐 Granting permissions on migrated tables..."
        if [ -f "postgres/grant-permissions.sh" ]; then
            # Map service names to database names and service users
            ./postgres/grant-permissions.sh --env-file "$ENV_FILE" --db-name "briefly_$service_name" --service-user "briefly_${service_name}_service"
            echo "✅ Permissions granted successfully for $service_name"
        else
            echo "❌ Error: postgres/grant-permissions.sh not found"
            echo "   This script is required for proper database setup"
            exit 1
        fi
    fi
}

# Run migrations for each service
run_service_migrations "user"
run_service_migrations "meetings"
run_service_migrations "shipments"
run_service_migrations "office"
run_service_migrations "chat"
run_service_migrations "contacts"

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
    echo "  - briefly_contacts: Ready"
fi
