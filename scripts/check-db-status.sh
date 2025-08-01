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
# Source PostgreSQL environment variables
source scripts/postgres-env.sh

echo "🔍 Checking PostgreSQL and database migration status..."

# Function to check if PostgreSQL is running
check_postgres_running() {
    echo "📊 Checking if PostgreSQL is running..."

    if pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER > /dev/null 2>&1; then
        echo "✅ PostgreSQL is running on $POSTGRES_HOST:$POSTGRES_PORT"
        return 0
    else
        echo "❌ PostgreSQL is not running on $POSTGRES_HOST:$POSTGRES_PORT"
        echo "   Start PostgreSQL with: ./scripts/postgres-start.sh"
        return 1
    fi
}

# Function to check migration status for a service
check_service_migrations() {
    local service_name=$1
    local migration_url=$2

    echo "📦 Checking migrations for $service_name..."
    cd services/$service_name

    # Set the database URL for this service
    export DB_URL=$migration_url

    # Check current migration revision
    current_rev=$(alembic current 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")

    # Check head migration revision
    head_rev=$(alembic heads 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")

    if [ "$current_rev" = "$head_rev" ] && [ "$current_rev" != "none" ]; then
        echo "✅ $service_name: Up to date (revision: $current_rev)"
        cd ../..
        return 0
    else
        echo "❌ $service_name: Out of date"
        echo "   Current: $current_rev"
        echo "   Head: $head_rev"
        cd ../..
        return 1
    fi
}

# Function to test database connections
test_connections() {
    echo "🔌 Testing database connections..."
    python3 scripts/postgres-test-connection.py
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

    services=(
        "user:$DB_URL_USER_MIGRATIONS"
        "meetings:$DB_URL_MEETINGS_MIGRATIONS"
        "shipments:$DB_URL_SHIPMENTS_MIGRATIONS"
        "office:$DB_URL_OFFICE_MIGRATIONS"
        "chat:$DB_URL_CHAT_MIGRATIONS"
        "vector_db:$DB_URL_VECTOR_MIGRATIONS"
    )

    for service_config in "${services[@]}"; do
        IFS=':' read -r service_name migration_url <<< "$service_config"
        if ! check_service_migrations "$service_name" "$migration_url"; then
            migrations_ok=false
        fi
    done
fi

echo ""
echo "=" * 50
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