#!/bin/bash
set -e

# Database Status Checker
# 
# This script checks PostgreSQL status and migration state for all services.
# 
# Exit codes:
#   0 - All checks passed (PostgreSQL running, connections working, migrations up to date)
#   1 - PostgreSQL not running
#   2 - Database connection errors
#   3 - Migrations needed
#
# Usage:
#   ./scripts/check-db-status.sh [--env-file .env.postgres.local]
#
# If --env-file is provided, the script will use those credentials.
# Otherwise, it will use default hardcoded credentials for local development.

# Set working directory to the project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Parse command line arguments
ENV_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --env-file FILE    Environment file with database passwords (optional)"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Use default credentials"
            echo "  $0 --env-file .env.postgres.local     # Use local environment"
            echo "  $0 --env-file .env.postgres.staging   # Use staging environment"
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
    # Set default values for required environment variables
    export POSTGRES_USER=${POSTGRES_USER:-postgres}
    export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    # No need to source postgres-env.sh anymore - PostgresURLs will handle this
fi

# Set up basic database connection info
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432

# Set up Python interpreter for PostgresURLs calls
VENV_PYTHON="python3"
if [ -f ".venv/bin/activate" ]; then
    VENV_PYTHON=".venv/bin/python"
fi

echo "🔍 Checking PostgreSQL and database migration status..."

# Function to check if PostgreSQL is running
check_postgres_running() {
    echo "📊 Checking if PostgreSQL is running..."

    # First check if pg_isready is available
    if command -v pg_isready >/dev/null 2>&1; then
        if pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER > /dev/null 2>&1; then
            echo "✅ PostgreSQL is running on $POSTGRES_HOST:$POSTGRES_PORT"
            return 0
        else
            echo "❌ PostgreSQL is not running on $POSTGRES_HOST:$POSTGRES_PORT"
            echo "   Start PostgreSQL with: ./scripts/postgres-start.sh"
            return 1
        fi
    else
        # Fallback: try to connect using Python if pg_isready is not available
        echo "⚠️  pg_isready not found, using Python fallback..."
        
        # Try to activate virtual environment if it exists
        if [ -f ".venv/bin/activate" ]; then
            echo "📦 Activating virtual environment for psycopg2..."
        fi
        
        $VENV_PYTHON -c "
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='$POSTGRES_HOST',
        port=$POSTGRES_PORT,
        user='$POSTGRES_USER',
        password='$POSTGRES_PASSWORD',
        database='postgres'
    )
    conn.close()
    print('✅ PostgreSQL is running on $POSTGRES_HOST:$POSTGRES_PORT')
    sys.exit(0)
except Exception as e:
    print('❌ PostgreSQL is not running on $POSTGRES_HOST:$POSTGRES_PORT')
    print('   Error:', str(e))
    print('   Start PostgreSQL with: ./scripts/postgres-start.sh')
    sys.exit(1)
" 2>/dev/null
        return $?
    fi
}

# Function to check migration status for a service
check_service_migrations() {
    local service_name=$1

    echo "📦 Checking migrations for $service_name..."

    # Use PostgresURLs to get the migration URL dynamically
    local migration_url
    migration_url=$($VENV_PYTHON -c "
from services.common.postgres_urls import PostgresURLs
urls = PostgresURLs()
print(urls.get_migration_url('$service_name'))
" 2>/dev/null)

    if [ $? -ne 0 ] || [ -z "$migration_url" ]; then
        echo "❌ Failed to get migration URL for $service_name"
        return 1
    fi

    # Check current migration revision
    current_rev=$(alembic -c services/$service_name/alembic.ini current 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")

    # Check head migration revision
    head_rev=$(alembic -c services/$service_name/alembic.ini heads 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")

    if [ "$current_rev" = "$head_rev" ] && [ "$current_rev" != "none" ]; then
        echo "✅ $service_name: Up to date (revision: $current_rev)"
        return 0
    else
        echo "❌ $service_name: Out of date"
        echo "   Current: $current_rev"
        echo "   Head: $head_rev"
        return 1
    fi
}

# Function to test database connections
test_connections() {
    echo "🔌 Testing database connections..."
    
    $VENV_PYTHON scripts/postgres-test-connection.py
}

# Main execution
postgres_ok=false
migrations_ok=true
connections_ok=false

# Check if PostgreSQL is running
if check_postgres_running; then
    postgres_ok=true

    # Test connections
    if test_connections > /dev/null 2>&1; then
        connections_ok=true
    fi

    # Check migrations for each service
    echo ""
    echo "🗄️ Checking migration status..."

    services=("user" "meetings" "shipments" "office" "chat" "contacts")

    for service_name in "${services[@]}"; do
        if ! check_service_migrations "$service_name"; then
            migrations_ok=false
        fi
    done
fi

echo ""
printf "%.0s=" {1..50}
echo ""
echo "📊 Database Status Summary:"
echo "  PostgreSQL Running: $([ "$postgres_ok" = true ] && echo "✅" || echo "❌")"
echo "  Connections Working: $([ "$connections_ok" = true ] && echo "✅" || echo "❌")"
echo "  Migrations Up to Date: $([ "$migrations_ok" = true ] && echo "✅" || echo "❌")"

# Return different exit codes based on the issue
if [ "$postgres_ok" = false ]; then
    echo ""
    echo "🚨 PostgreSQL is not running. Please start it first:"
    echo "   ./scripts/postgres-start.sh"
    exit 1
elif [ "$connections_ok" = false ]; then
    echo ""
    echo "🚨 Database connection errors detected. Check PostgreSQL logs:"
    echo "   docker logs briefly-postgres"
    exit 2
elif [ "$migrations_ok" = false ]; then
    echo ""
    echo "⚠️  Some databases need migrations. Run:"
    echo "   ./scripts/run-migrations.sh"
    exit 3
else
    echo ""
    echo "🎉 All database checks passed!"
    exit 0
fi