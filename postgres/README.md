# PostgreSQL Database Setup

This directory contains the initialization scripts for the Briefly PostgreSQL database container.

## Environment-Specific Configuration

The database user creation script now uses environment variables for passwords instead of hardcoded values. This provides better security and flexibility.

### Environment Files

The project uses environment-specific files to manage database passwords:

- `.env.postgres.local` - Local development environment
- `.env.postgres.staging` - Staging environment
- `.env.postgres.production` - Production environment template

**Note:** These files are located in the repo root and are git-ignored for security.

### Database Structure

The PostgreSQL container creates the following databases for each microservice:

- **`briefly_user`** - User management service
- **`briefly_meetings`** - Meetings service
- **`briefly_shipments`** - Shipments service
- **`briefly_office`** - Office integration service
- **`briefly_chat`** - Chat service
- **`briefly_vector`** - Vector database for embeddings

Each database has its own dedicated service user with appropriate permissions.

### Integration with Existing Scripts

The environment variable functionality has been integrated into the existing PostgreSQL scripts:

- **`scripts/postgres-start.sh`** - Now **requires** `--env-file` option for security
- **`scripts/postgres-stop.sh`** - Unchanged, works with all containers
- **Security Focused** - No default passwords, environment files required

The scripts now require environment files to be explicitly provided, ensuring no hardcoded passwords are used.

### Quick Start

```bash
# Start PostgreSQL with local environment file
./scripts/postgres-start.sh --env-file .env.postgres.local

# Start PostgreSQL with staging environment file
./scripts/postgres-start.sh --env-file .env.postgres.staging

# Start PostgreSQL with production environment file
./scripts/postgres-start.sh --env-file .env.postgres.production

# Start fresh with environment file (WILL DELETE DATA)
./scripts/postgres-start.sh --fresh-install --env-file .env.postgres.local

# Stop PostgreSQL containers
./scripts/postgres-stop.sh

# Stop and remove containers (preserves data)
./scripts/postgres-stop.sh --remove

# Stop and remove containers and data (WILL DELETE DATA)
./scripts/postgres-stop.sh --remove-volume
```

### Required Environment Variables

You can set the following environment variables to customize database passwords:

**Admin Credentials (REQUIRED):**
- `POSTGRES_USER` - Admin username (e.g., postgres)
- `POSTGRES_PASSWORD` - Admin password (must be set in environment file)

**Service User Passwords:**
- `BRIEFLY_USER_SERVICE_PASSWORD` - Password for the user service database user
- `BRIEFLY_MEETINGS_SERVICE_PASSWORD` - Password for the meetings service database user
- `BRIEFLY_SHIPMENTS_SERVICE_PASSWORD` - Password for the shipments service database user
- `BRIEFLY_OFFICE_SERVICE_PASSWORD` - Password for the office service database user
- `BRIEFLY_CHAT_SERVICE_PASSWORD` - Password for the chat service database user
- `BRIEFLY_VECTOR_SERVICE_PASSWORD` - Password for the vector service database user
- `BRIEFLY_READONLY_PASSWORD` - Password for the readonly user

### Usage Examples

#### Environment File Setup

Create environment files in the repo root (git-ignored):

**`.env.postgres.local`** (for local development):
```bash
# Admin user credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Database user passwords for each microservice
BRIEFLY_USER_SERVICE_PASSWORD=briefly_user_pass
BRIEFLY_MEETINGS_SERVICE_PASSWORD=briefly_meetings_pass
BRIEFLY_SHIPMENTS_SERVICE_PASSWORD=briefly_shipments_pass
BRIEFLY_OFFICE_SERVICE_PASSWORD=briefly_office_pass
BRIEFLY_CHAT_SERVICE_PASSWORD=briefly_chat_pass
BRIEFLY_VECTOR_SERVICE_PASSWORD=briefly_vector_pass
BRIEFLY_READONLY_PASSWORD=briefly_readonly_pass
```

**`.env.postgres.staging`** (for staging):
```bash
# Admin user credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=staging_admin_pass_$(openssl rand -hex 8)

# Database user passwords for each microservice
BRIEFLY_USER_SERVICE_PASSWORD=staging_user_pass_$(openssl rand -hex 8)
BRIEFLY_MEETINGS_SERVICE_PASSWORD=staging_meetings_pass_$(openssl rand -hex 8)
BRIEFLY_SHIPMENTS_SERVICE_PASSWORD=staging_shipments_pass_$(openssl rand -hex 8)
BRIEFLY_OFFICE_SERVICE_PASSWORD=staging_office_pass_$(openssl rand -hex 8)
BRIEFLY_CHAT_SERVICE_PASSWORD=staging_chat_pass_$(openssl rand -hex 8)
BRIEFLY_VECTOR_SERVICE_PASSWORD=staging_vector_pass_$(openssl rand -hex 8)
BRIEFLY_READONLY_PASSWORD=staging_readonly_pass_$(openssl rand -hex 8)
```

**`.env.postgres.production`** (for production):
```bash
# Admin user credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=REPLACE_WITH_STRONG_ADMIN_PASSWORD

# Database user passwords for each microservice
BRIEFLY_USER_SERVICE_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
BRIEFLY_MEETINGS_SERVICE_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
BRIEFLY_SHIPMENTS_SERVICE_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
BRIEFLY_OFFICE_SERVICE_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
BRIEFLY_CHAT_SERVICE_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
BRIEFLY_VECTOR_SERVICE_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
BRIEFLY_READONLY_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
```

## Security Best Practices

1. **Use strong passwords**: Generate secure, random passwords for each service
2. **Use different passwords**: Each service should have a unique password
3. **Environment-specific passwords**: Use different passwords for development, staging, and production
4. **Secret management**: Use a secrets management service (like Docker Secrets, Kubernetes Secrets, or HashiCorp Vault) in production
5. **Never commit passwords**: Ensure passwords are not committed to version control

## Neon Integration

For production deployments using Neon PostgreSQL, you can use the environment files to configure your Neon database:

1. **Set up Neon database** with the required databases (briefly_user, briefly_meetings, etc.)
2. **Create users** in Neon with the passwords from your `.env.postgres.production` file
3. **Update your application** to use Neon connection strings instead of local PostgreSQL

Example Neon setup:
```bash
# Use the production environment file to get password requirements
cat .env.postgres.production

# Create users in Neon with the same passwords
# Then update your application configuration to use Neon
```

## Production Migration

When deploying to production (Neon/Supabase), update the connection strings:

```bash
# Development
export DB_URL_USER=postgresql://briefly_user_service:briefly_user_pass@localhost:5432/briefly_user

# Production (Neon)
export DB_URL_USER=postgresql://briefly_user_service:prod_password@briefly-core.neon.tech/briefly_user
```

**Migration Commands:**

### Run all migrations
```bash
./scripts/run-migrations.sh
```

### Run migrations for specific service
```bash
cd services/user
export DB_URL=postgresql://postgres:postgres@localhost:5432/briefly_user
alembic upgrade head
```

### Create new migration
```bash
cd services/user
export DB_URL=postgresql://postgres:postgres@localhost:5432/briefly_user
alembic revision --autogenerate -m "Description of changes"
```

## Database Status Checking

This section covers scripts for checking PostgreSQL status and migration state.

### `check-db-status.sh`
Comprehensive database status checker that:
- Verifies PostgreSQL is running
- Tests database connections for all services
- Checks if all databases are up to date with migrations

**Usage:**
```bash
# Use default credentials for local development
./scripts/check-db-status.sh

# Use specific environment file
./scripts/check-db-status.sh --env-file .env.postgres.local

# Use staging environment
./scripts/check-db-status.sh --env-file .env.postgres.staging
```

**Exit codes:**
- `0`: All checks passed
- `1`: PostgreSQL not running
- `2`: Database connection errors
- `3`: Migrations needed

**Environment Files:**
The script can optionally use an environment file to get database credentials:
- Without `--env-file`: Uses default hardcoded credentials for local development
- With `--env-file`: Uses the specified environment file for secure credential management

### `run-migrations.sh`
Runs or checks Alembic migrations for all services.

**Usage:**
```bash
# Run all migrations
./scripts/run-migrations.sh

# Check migration status only (don't run migrations)
./scripts/run-migrations.sh --check
```

### `postgres-test-connection.py`
Python script that tests database connections for all services.

**Usage:**
```bash
python3 scripts/postgres-test-connection.py
```

## Integration with Install Script

The `install.sh` script now automatically:
1. Checks database status using `check-db-status.sh`
2. Only runs migrations if needed
3. Provides clear feedback about database readiness

## Database Maintenance

### Check Migration Status
```bash
./scripts/run-migrations.sh --check
```

### Test Connections
```bash
python3 scripts/postgres-test-connection.py
```

### Comprehensive Status Check
```bash
./scripts/check-db-status.sh
```

## File Structure

- `init-db.sh` - Initial database setup (extensions, timezone)
- `create-database.sql` - Creates the individual databases for each service
- `create-users.sh` - Creates database users with environment variable passwords
- `create-users.sql.deprecated` - **DEPRECATED**: Old version with hardcoded passwords
- `README.md` - This documentation file

**Environment files** (in repo root, git-ignored):
- `.env.postgres.local` - Local development environment passwords
- `.env.postgres.staging` - Staging environment passwords
- `.env.postgres.production` - Production environment password template

See env.postgres.example for an example.

## Service Configuration

Update your service settings to use the PostgreSQL URLs:

### services/user/settings.py
```python
# Use service-specific user for application
db_url_user = os.getenv("DB_URL_USER", "postgresql://briefly_user_service:briefly_user_pass@localhost:5432/briefly_user")

# Use admin user for migrations
db_url_user_migrations = os.getenv("DB_URL_USER_MIGRATIONS", "postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/briefly_user")
```

## Database Management

### Connect to database
```bash
# Connect to specific database
psql -h localhost -p 5432 -U postgres -d $database

# Connect as service user
psql -h localhost -p 5432 -U briefly_user_service -d $database
```

### List databases
```bash
psql -h localhost -p 5432 -U postgres -c "\l"
```

### Reset database
```bash
# Drop and recreate database
psql -h localhost -p 5432 -U postgres -c "DROP DATABASE briefly_user;"
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE briefly_user;"
```

## Docker Commands

### View logs
```bash
docker logs briefly-postgres
```

### Access container shell
```bash
docker exec -it briefly-postgres bash
```

## Troubleshooting

### Container Won't Start
- Ensure environment file exists and contains `POSTGRES_USER` and `POSTGRES_PASSWORD`
- Check that environment file path is correct (should be in repo root)
- Verify Docker has sufficient resources

### Database Creation Errors
- If you see "database already exists" errors, use `--fresh-install` to start clean
- This happens when switching between different environment configurations

### Connection Issues
- Verify the container is running: `docker ps | grep briefly-postgres`
- Check container logs: `docker logs briefly-postgres`
- Ensure port 5432 is not in use by another PostgreSQL instance

### Port already in use
```bash
# Check what's using port 5432
lsof -i :5432

# Kill the process or use a different port
```

### Permission denied
```bash
# Make sure scripts are executable
chmod +x scripts/*.sh
```

### Database connection failed
```bash
# Check if container is running
docker ps | grep briefly-postgres

# Check container logs
docker logs briefly-postgres

# Run comprehensive status check
./scripts/check-db-status.sh

# Test connections specifically
python3 scripts/postgres-test-connection.py
```
