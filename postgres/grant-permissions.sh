#!/bin/bash
set -e

# This script grants permissions on existing tables after migrations have run
# It should be run after the migration scripts complete
# This ensures that service users have access to the tables created by migrations

echo "Granting permissions on existing tables..."

# Function to grant permissions on a specific database
grant_permissions_on_database() {
    local db_name=$1
    local service_user=$2

    echo "Granting permissions on $db_name to $service_user..."

    docker exec briefly-postgres psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "$db_name" <<-EOSQL
        -- Grant permissions on existing tables
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $service_user;

        -- Grant permissions on existing sequences
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $service_user;

        -- Grant permissions on the alembic_version table specifically
        GRANT ALL PRIVILEGES ON TABLE alembic_version TO $service_user;

        -- Grant permissions on any existing indexes
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $service_user;
EOSQL

    echo "Permissions granted on $db_name for $service_user"
}

# Grant permissions for each service on their respective databases
grant_permissions_on_database "briefly_user" "briefly_user_service"
grant_permissions_on_database "briefly_meetings" "briefly_meetings_service"
grant_permissions_on_database "briefly_shipments" "briefly_shipments_service"
grant_permissions_on_database "briefly_office" "briefly_office_service"
grant_permissions_on_database "briefly_chat" "briefly_chat_service"
grant_permissions_on_database "briefly_vector" "briefly_vector_service"

echo "All permissions granted successfully."