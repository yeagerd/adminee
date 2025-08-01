#!/bin/bash
set -e

# This script is used by Dockerfile.postgres during container initialization
# It runs after databases are created
# Execution order: 03-create-users.sh (create users & permissions)
#
# Create dedicated users for each microservice
# This provides better security isolation

echo "Creating database users with environment variable passwords..."

# Set default passwords if environment variables are not provided
USER_SERVICE_PASSWORD=${BRIEFLY_USER_SERVICE_PASSWORD:-briefly_user_pass}
MEETINGS_SERVICE_PASSWORD=${BRIEFLY_MEETINGS_SERVICE_PASSWORD:-briefly_meetings_pass}
SHIPMENTS_SERVICE_PASSWORD=${BRIEFLY_SHIPMENTS_SERVICE_PASSWORD:-briefly_shipments_pass}
OFFICE_SERVICE_PASSWORD=${BRIEFLY_OFFICE_SERVICE_PASSWORD:-briefly_office_pass}
CHAT_SERVICE_PASSWORD=${BRIEFLY_CHAT_SERVICE_PASSWORD:-briefly_chat_pass}
VECTOR_SERVICE_PASSWORD=${BRIEFLY_VECTOR_SERVICE_PASSWORD:-briefly_vector_pass}
READONLY_PASSWORD=${BRIEFLY_READONLY_PASSWORD:-briefly_readonly_pass}

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- User service user
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'briefly_user_service') THEN
            CREATE USER briefly_user_service WITH PASSWORD '$USER_SERVICE_PASSWORD';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE briefly_user TO briefly_user_service;
    GRANT ALL PRIVILEGES ON DATABASE briefly_user TO briefly_user_service;
    GRANT ALL ON SCHEMA public TO briefly_user_service;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO briefly_user_service;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO briefly_user_service;

    -- Meetings service user
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'briefly_meetings_service') THEN
            CREATE USER briefly_meetings_service WITH PASSWORD '$MEETINGS_SERVICE_PASSWORD';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE briefly_meetings TO briefly_meetings_service;
    GRANT ALL PRIVILEGES ON DATABASE briefly_meetings TO briefly_meetings_service;
    GRANT ALL ON SCHEMA public TO briefly_meetings_service;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO briefly_meetings_service;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO briefly_meetings_service;

    -- Shipments service user
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'briefly_shipments_service') THEN
            CREATE USER briefly_shipments_service WITH PASSWORD '$SHIPMENTS_SERVICE_PASSWORD';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE briefly_shipments TO briefly_shipments_service;
    GRANT ALL PRIVILEGES ON DATABASE briefly_shipments TO briefly_shipments_service;
    GRANT ALL ON SCHEMA public TO briefly_shipments_service;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO briefly_shipments_service;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO briefly_shipments_service;

    -- Office service user
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'briefly_office_service') THEN
            CREATE USER briefly_office_service WITH PASSWORD '$OFFICE_SERVICE_PASSWORD';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE briefly_office TO briefly_office_service;
    GRANT ALL PRIVILEGES ON DATABASE briefly_office TO briefly_office_service;
    GRANT ALL ON SCHEMA public TO briefly_office_service;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO briefly_office_service;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO briefly_office_service;

    -- Chat service user
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'briefly_chat_service') THEN
            CREATE USER briefly_chat_service WITH PASSWORD '$CHAT_SERVICE_PASSWORD';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE briefly_chat TO briefly_chat_service;
    GRANT ALL PRIVILEGES ON DATABASE briefly_chat TO briefly_chat_service;
    GRANT ALL ON SCHEMA public TO briefly_chat_service;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO briefly_chat_service;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO briefly_chat_service;

    -- Vector service user
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'briefly_vector_service') THEN
            CREATE USER briefly_vector_service WITH PASSWORD '$VECTOR_SERVICE_PASSWORD';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE briefly_vector TO briefly_vector_service;
    GRANT ALL PRIVILEGES ON DATABASE briefly_vector TO briefly_vector_service;
    GRANT ALL ON SCHEMA public TO briefly_vector_service;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO briefly_vector_service;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO briefly_vector_service;

    -- Create a readonly user for cross-service queries (if needed)
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'briefly_readonly') THEN
            CREATE USER briefly_readonly WITH PASSWORD '$READONLY_PASSWORD';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE briefly_user TO briefly_readonly;
    GRANT CONNECT ON DATABASE briefly_meetings TO briefly_readonly;
    GRANT CONNECT ON DATABASE briefly_shipments TO briefly_readonly;
    GRANT CONNECT ON DATABASE briefly_office TO briefly_readonly;
    GRANT CONNECT ON DATABASE briefly_chat TO briefly_readonly;
    GRANT CONNECT ON DATABASE briefly_vector TO briefly_readonly;
    GRANT USAGE ON SCHEMA public TO briefly_readonly;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO briefly_readonly;
    GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO briefly_readonly;
EOSQL

echo "Database users created successfully."
