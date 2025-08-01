#!/bin/bash
set -e

# This script is used by Dockerfile.postgres during container initialization
# It runs after PostgreSQL is fully initialized
# Execution order: 02-create-databases.sh (create databases)
#
# Create databases for each microservice with proper error handling

echo "Creating databases for each microservice..."

# Function to create database if it doesn't exist
create_database_if_not_exists() {
    local db_name=$1
    echo "Creating database: $db_name"
    
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $db_name'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db_name')\gexec
EOSQL
    
    # Grant privileges to postgres user
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        GRANT ALL PRIVILEGES ON DATABASE $db_name TO postgres;
EOSQL
    
    echo "Database $db_name created/verified successfully"
}

# Create each database
create_database_if_not_exists "briefly_user"
create_database_if_not_exists "briefly_meetings"
create_database_if_not_exists "briefly_shipments"
create_database_if_not_exists "briefly_office"
create_database_if_not_exists "briefly_chat"
create_database_if_not_exists "briefly_vector"

echo "All databases created successfully." 