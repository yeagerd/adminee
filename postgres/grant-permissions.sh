#!/bin/bash
set -e

# This script grants permissions on existing tables after migrations have run
# It should be run after the migration scripts complete
# This ensures that service users have access to the tables created by migrations

# Load environment variables with defaults
POSTGRES_CONTAINER=${POSTGRES_CONTAINER:-briefly-postgres}
POSTGRES_USER=${POSTGRES_USER:-postgres}

echo "Granting permissions on existing tables..."

# Function to grant permissions on a specific database
grant_permissions_on_database() {
    local db_name=$1
    local service_user=$2

    echo "Granting permissions on $db_name to $service_user..."

    docker exec "$POSTGRES_CONTAINER" psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db_name" <<-EOSQL
        -- Grant permissions on existing tables
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $service_user;

        -- Grant permissions on existing sequences
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $service_user;

        -- Grant permissions on the alembic_version table specifically
        GRANT ALL PRIVILEGES ON TABLE alembic_version TO $service_user;
EOSQL

    echo "Permissions granted on $db_name for $service_user"
}

# Function to grant readonly permissions on a specific database
grant_readonly_permissions_on_database() {
    local db_name=$1

    echo "Granting readonly permissions on $db_name to briefly_readonly..."

    docker exec "$POSTGRES_CONTAINER" psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db_name" <<-EOSQL
        -- Grant SELECT permissions on existing tables to readonly user
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO briefly_readonly;

        -- Grant SELECT permissions on existing sequences to readonly user
        GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO briefly_readonly;

        -- Grant SELECT permissions on the alembic_version table specifically
        GRANT SELECT ON TABLE alembic_version TO briefly_readonly;
EOSQL

    echo "Readonly permissions granted on $db_name for briefly_readonly"
}

# Grant permissions for each service on their respective databases
grant_permissions_on_database "briefly_user" "briefly_user_service"
grant_permissions_on_database "briefly_meetings" "briefly_meetings_service"
grant_permissions_on_database "briefly_shipments" "briefly_shipments_service"
grant_permissions_on_database "briefly_office" "briefly_office_service"
grant_permissions_on_database "briefly_chat" "briefly_chat_service"
grant_permissions_on_database "briefly_vector" "briefly_vector_service"

# Grant readonly permissions on all databases
grant_readonly_permissions_on_database "briefly_user"
grant_readonly_permissions_on_database "briefly_meetings"
grant_readonly_permissions_on_database "briefly_shipments"
grant_readonly_permissions_on_database "briefly_office"
grant_readonly_permissions_on_database "briefly_chat"
grant_readonly_permissions_on_database "briefly_vector"

echo "All permissions granted successfully."