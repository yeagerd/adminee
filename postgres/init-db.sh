#!/bin/bash
set -e

# This script is used by Dockerfile.postgres during container initialization
# It runs after PostgreSQL is initialized but before it starts accepting connections
# Execution order: 01-init-db.sh (extensions & setup)

echo "Initializing Briefly PostgreSQL instance..."

# Create the main database if it doesn't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create extension for UUID support
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Create extension for better performance
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

    -- Set timezone
    SET timezone = 'UTC';
EOSQL

echo "PostgreSQL initialization completed."