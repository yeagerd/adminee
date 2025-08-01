#!/bin/bash
# PostgreSQL Environment Variables for Local Development
# Source this file to set up database connection variables

# Admin connection (for migrations and setup)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres

# Service-specific database URLs
export DB_URL_USER=postgresql://briefly_user_service:briefly_user_pass@localhost:5432/briefly_user
export DB_URL_MEETINGS=postgresql://briefly_meetings_service:briefly_meetings_pass@localhost:5432/briefly_meetings
export DB_URL_SHIPMENTS=postgresql://briefly_shipments_service:briefly_shipments_pass@localhost:5432/briefly_shipments
export DB_URL_OFFICE=postgresql://briefly_office_service:briefly_office_pass@localhost:5432/briefly_office
export DB_URL_CHAT=postgresql://briefly_chat_service:briefly_chat_pass@localhost:5432/briefly_chat
export DB_URL_VECTOR=postgresql://briefly_vector_service:briefly_vector_pass@localhost:5432/briefly_vector

# Read-only connection for cross-service queries (if needed)
export DB_URL_READONLY=postgresql://briefly_readonly:briefly_readonly_pass@localhost:5432/briefly_user

# For Alembic migrations (using admin user)
export DB_URL_USER_MIGRATIONS=postgresql://postgres:postgres@localhost:5432/briefly_user
export DB_URL_MEETINGS_MIGRATIONS=postgresql://postgres:postgres@localhost:5432/briefly_meetings
export DB_URL_SHIPMENTS_MIGRATIONS=postgresql://postgres:postgres@localhost:5432/briefly_shipments
export DB_URL_OFFICE_MIGRATIONS=postgresql://postgres:postgres@localhost:5432/briefly_office
export DB_URL_CHAT_MIGRATIONS=postgresql://postgres:postgres@localhost:5432/briefly_chat
export DB_URL_VECTOR_MIGRATIONS=postgresql://postgres:postgres@localhost:5432/briefly_vector

echo "✅ PostgreSQL environment variables loaded"
echo "📋 Available variables:"
echo "  DB_URL_USER, DB_URL_MEETINGS, DB_URL_SHIPMENTS, DB_URL_OFFICE, DB_URL_CHAT, DB_URL_VECTOR"
echo "  DB_URL_USER_MIGRATIONS, DB_URL_MEETINGS_MIGRATIONS, etc." 