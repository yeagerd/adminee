#!/bin/bash
set -e

echo "🔄 Safe migration to new PostgreSQL setup..."

# Check if existing container is running
if ! docker ps | grep -q briefly-db-1; then
    echo "❌ Existing PostgreSQL container (briefly-db-1) is not running!"
    echo "Please start your existing container first:"
    echo "docker-compose up -d db"
    exit 1
fi

# Create backup directory
BACKUP_DIR="./postgres_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup of existing databases..."

# Backup all databases
docker exec briefly-db-1 pg_dump -U postgres briefly > "$BACKUP_DIR/briefly_backup.sql"
docker exec briefly-db-1 pg_dump -U postgres briefly_user > "$BACKUP_DIR/briefly_user_backup.sql"
docker exec briefly-db-1 pg_dump -U postgres briefly_meetings > "$BACKUP_DIR/briefly_meetings_backup.sql"
docker exec briefly-db-1 pg_dump -U postgres briefly_shipments > "$BACKUP_DIR/briefly_shipments_backup.sql"
docker exec briefly-db-1 pg_dump -U postgres briefly_office > "$BACKUP_DIR/briefly_office_backup.sql"
docker exec briefly-db-1 pg_dump -U postgres briefly_chat > "$BACKUP_DIR/briefly_chat_backup.sql"
docker exec briefly-db-1 pg_dump -U postgres briefly_vector > "$BACKUP_DIR/briefly_vector_backup.sql"

echo "✅ Backup completed in: $BACKUP_DIR"

# Ask for confirmation
echo ""
echo "⚠️  WARNING: This will replace your existing PostgreSQL container!"
echo "   Your data is backed up in: $BACKUP_DIR"
echo ""
read -p "Do you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Migration cancelled. Your existing data is safe."
    exit 1
fi

echo "🚀 Starting migration..."

# Run the new PostgreSQL setup
./scripts/start-postgres.sh

echo "📥 Restoring data to new container..."

# Wait for new container to be ready
sleep 10

# Restore data to new container
docker exec briefly-postgres psql -U postgres -d briefly_user -f /tmp/briefly_user_backup.sql < "$BACKUP_DIR/briefly_user_backup.sql" || echo "No user data to restore"
docker exec briefly-postgres psql -U postgres -d briefly_meetings -f /tmp/briefly_meetings_backup.sql < "$BACKUP_DIR/briefly_meetings_backup.sql" || echo "No meetings data to restore"
docker exec briefly-postgres psql -U postgres -d briefly_shipments -f /tmp/briefly_shipments_backup.sql < "$BACKUP_DIR/briefly_shipments_backup.sql" || echo "No shipments data to restore"
docker exec briefly-postgres psql -U postgres -d briefly_office -f /tmp/briefly_office_backup.sql < "$BACKUP_DIR/briefly_office_backup.sql" || echo "No office data to restore"
docker exec briefly-postgres psql -U postgres -d briefly_chat -f /tmp/briefly_chat_backup.sql < "$BACKUP_DIR/briefly_chat_backup.sql" || echo "No chat data to restore"
docker exec briefly-postgres psql -U postgres -d briefly_vector -f /tmp/briefly_vector_backup.sql < "$BACKUP_DIR/briefly_vector_backup.sql" || echo "No vector data to restore"

echo "✅ Migration completed!"
echo "📁 Backup files are in: $BACKUP_DIR"
echo "🔄 You can now stop the old container: docker stop briefly-db-1" 