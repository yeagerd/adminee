#!/bin/bash
set -e

# This script grants permissions on existing tables after migrations have run
# It should be run after the migration scripts complete
# This ensures that service users have access to the tables created by migrations

# Parse command line arguments
ENV_FILE=""
DB_NAME=""
SERVICE_USER=""
ALL_SERVICES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --db-name)
            DB_NAME="$2"
            shift 2
            ;;
        --service-user)
            SERVICE_USER="$2"
            shift 2
            ;;
        --all-services)
            ALL_SERVICES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --env-file FILE     REQUIRED: Environment file with database passwords"
            echo "  --db-name NAME      Database name (required unless --all-services)"
            echo "  --service-user USER Service user name (required unless --all-services)"
            echo "  --all-services      Grant permissions for all services"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --env-file .env.postgres.local --db-name briefly_user --service-user briefly_user_service"
            echo "  $0 --env-file .env.postgres.local --all-services"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate environment file
if [ -z "$ENV_FILE" ]; then
    echo "❌ Error: Environment file is required for security"
    echo "   Please provide an environment file with database passwords"
    echo "   Example: $0 --env-file .env.postgres.local --db-name briefly_user --service-user briefly_user_service"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment variables from the provided file
echo "📄 Loading environment from: $ENV_FILE"
source "$ENV_FILE"

# Set up database connection parameters (consistent with run-migrations.sh)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432

# Function to grant permissions on a specific database
grant_permissions_on_database() {
    local db_name=$1
    local service_user=$2

    echo "🔐 Granting permissions on $db_name to $service_user..."

    # Use Docker container to run psql commands
    # Load environment variables into the container
    docker exec -i briefly-postgres bash -c "
        export PGPASSWORD=\"${POSTGRES_PASSWORD:-postgres}\"
        psql -h localhost -p 5432 -U \"${POSTGRES_USER:-postgres}\" -d \"$db_name\" -v ON_ERROR_STOP=1 << 'EOF'
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"$service_user\";
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"$service_user\";
        GRANT ALL PRIVILEGES ON TABLE alembic_version TO \"$service_user\";
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"$service_user\";
EOF
    "

    echo "✅ Permissions granted on $db_name for $service_user"
}

if [ "$ALL_SERVICES" = true ]; then
    echo "🔐 Granting permissions for all services..."
    
    # Grant permissions for each service on their respective databases
    grant_permissions_on_database "briefly_user" "briefly_user_service"
    grant_permissions_on_database "briefly_meetings" "briefly_meetings_service"
    grant_permissions_on_database "briefly_shipments" "briefly_shipments_service"
    grant_permissions_on_database "briefly_office" "briefly_office_service"
    grant_permissions_on_database "briefly_chat" "briefly_chat_service"
    grant_permissions_on_database "briefly_vector" "briefly_vector_service"

    echo "✅ All permissions granted successfully."
else
    # Validate single service parameters
    if [ -z "$DB_NAME" ] || [ -z "$SERVICE_USER" ]; then
        echo "❌ Error: Both --db-name and --service-user are required for single service mode"
        echo "   Or use --all-services to grant permissions for all services"
        exit 1
    fi

    echo "🔐 Granting permissions for single service..."
    grant_permissions_on_database "$DB_NAME" "$SERVICE_USER"
    echo "✅ Permissions granted successfully."
fi