#!/bin/bash
set -e

# Set working directory to the project root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Source PostgreSQL environment variables
source scripts/postgres-env.sh

# Check if --check flag is provided
CHECK_ONLY=false
if [[ "$1" == "--check" ]]; then
    CHECK_ONLY=true
    echo "🔍 Checking Alembic migration status for all services..."
else
    echo "🗄️ Running Alembic migrations for all services..."
fi

# Function to run migrations for a service
run_service_migrations() {
    local service_name=$1
    local migration_url=$2

    echo "📦 Checking migrations for $service_name..."
    cd services/$service_name

    # Set the database URL for this service
    export DB_URL=$migration_url

    if [ "$CHECK_ONLY" = true ]; then
        # Check current migration revision
        current_rev=$(alembic current 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")

        # Check head migration revision
        head_rev=$(alembic heads 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")

        if [ "$current_rev" = "$head_rev" ] && [ "$current_rev" != "none" ]; then
            echo "✅ $service_name: Up to date (revision: $current_rev)"
        else
            echo "❌ $service_name: Out of date"
            echo "   Current: $current_rev"
            echo "   Head: $head_rev"
        fi
    else
        # Run migrations
        alembic upgrade head
        echo "✅ $service_name migrations completed"
    fi

    cd ../..
}

# Run migrations for each service
run_service_migrations "user" "$DB_URL_USER_MIGRATIONS"
run_service_migrations "meetings" "$DB_URL_MEETINGS_MIGRATIONS"
run_service_migrations "shipments" "$DB_URL_SHIPMENTS_MIGRATIONS"
run_service_migrations "office" "$DB_URL_OFFICE_MIGRATIONS"
run_service_migrations "chat" "$DB_URL_CHAT_MIGRATIONS"
run_service_migrations "vector_db" "$DB_URL_VECTOR_MIGRATIONS"

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
    echo "  - briefly_vector: Ready"
fi
