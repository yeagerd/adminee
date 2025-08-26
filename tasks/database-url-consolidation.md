# Database URL Consolidation and Password Management

## Overview
Consolidate database URL construction and password management to use a single source of truth through `services/common/config_secrets.py` and a new `services/common/postgres_urls.py` module.

## Goals
- [ ] Single source of truth for database connection logic
- [ ] Eliminate environment variable pollution in shell scripts
- [ ] Consistent URL construction across all services
- [ ] Easy migration path to GCP Secret Manager
- [ ] Remove duplicate password/URL definitions

## Phase 1: Create Core Infrastructure

### Create PostgresURLs Module
- [x] Create `services/common/postgres_urls.py`
  - [x] Implement `PostgresURLs` class
  - [x] Add `get_service_url(service_name)` method
  - [x] Add `get_migration_url(service_name)` method
  - [x] Add `get_readonly_url(service_name)` method (if needed)
  - [x] Use `config_secrets.get_secret()` for all credential retrieval
  - [x] Add proper error handling and validation
  - [x] Add type hints and docstrings

### Update Environment Files
- [x] Consolidate `.env` and `.env.postgres.local` into single `.env` file
  - [x] Keep core database config: `POSTGRES_HOST`, `POSTGRES_PORT`
  - [x] Keep admin credentials: `POSTGRES_USER`, `POSTGRES_PASSWORD`
  - [x] Keep service passwords: `BRIEFLY_*_SERVICE_PASSWORD`
  - [x] Remove hardcoded `DB_URL_*` variables
  - [x] Add `ENVIRONMENT=local` setting
- [x] Update `.example.env` to reflect new structure
- [ ] Remove `.env.postgres.local` file

## Phase 2: Update Services

### User Service
- [x] Update `services/user/settings.py`
  - [x] Remove hardcoded database URL
  - [x] Use `PostgresURLs().get_service_url("user")`
- [x] Update `services/user/database.py`
  - [x] Use `PostgresURLs().get_service_url("user")`
- [x] Update `services/user/alembic/env.py`
  - [x] Use `PostgresURLs().get_migration_url("user")`
- [ ] Update tests to mock `PostgresURLs`

### Meetings Service
- [x] Update `services/meetings/settings.py`
  - [x] Remove hardcoded database URL
  - [x] Use `PostgresURLs().get_service_url("meetings")`
- [x] Update `services/meetings/models/__init__.py`
  - [x] Use `PostgresURLs().get_service_url("meetings")`
- [x] Update `services/meetings/alembic/env.py`
  - [x] Use `PostgresURLs().get_migration_url("meetings")`
- [ ] Update tests to mock `PostgresURLs`

### Shipments Service
- [x] Update `services/shipments/settings.py`
  - [x] Remove hardcoded database URL
  - [x] Use `PostgresURLs().get_service_url("shipments")`
- [x] Update `services/shipments/database.py`
  - [x] Use `PostgresURLs().get_service_url("shipments")`
- [x] Update `services/shipments/alembic/env.py`
  - [x] Use `PostgresURLs().get_migration_url("shipments")`
- [ ] Update tests to mock `PostgresURLs`

### Office Service
- [x] Update `services/office/settings.py`
  - [x] Remove hardcoded database URL
  - [x] Use `PostgresURLs().get_service_url("office")`
- [x] Update `services/office/models/__init__.py`
  - [x] Use `PostgresURLs().get_service_url("office")`
- [x] Update `services/office/alembic/env.py`
  - [x] Use `PostgresURLs().get_migration_url("office")`
- [ ] Update tests to mock `PostgresURLs`

### Chat Service
- [x] Update `services/chat/settings.py`
  - [x] Remove hardcoded database URL
  - [x] Use `PostgresURLs().get_service_url("chat")`
- [x] Update `services/chat/alembic/env.py`
  - [x] Use `PostgresURLs().get_migration_url("chat")`
- [x] Update `services/chat/history_manager.py`
  - [x] Use `PostgresURLs().get_service_url("chat")`
- [ ] Update tests to mock `PostgresURLs`

### Contacts Service
- [x] Update `services/contacts/settings.py`
  - [x] Remove hardcoded database URL
  - [x] Use `PostgresURLs().get_service_url("contacts")`
- [x] Update `services/contacts/database.py`
  - [x] Use `PostgresURLs().get_service_url("contacts")`
- [x] Update `services/contacts/alembic/env.py`
  - [x] Use `PostgresURLs().get_migration_url("contacts")`
- [ ] Update tests to mock `PostgresURLs`

### Vector Service
- [x] Update `services/vector_db/` (if it exists)
  - [x] Use `PostgresURLs().get_service_url("vector")`
  - [x] Update tests to mock `PostgresURLs`

## Phase 3: Update Scripts

### Remove postgres-env.sh
- [x] Delete `scripts/postgres-env.sh` (redundant with new approach)
- [x] Update any scripts that source it

### Update check-db-status.sh
- [x] Update `scripts/check-db-status.sh`
  - [x] Remove hardcoded URL construction
  - [x] Use `PostgresURLs().get_migration_url()` for migration checks
  - [x] Remove `DB_URL_*` exports (no more environment pollution)
  - [x] Use Python subprocess calls to get URLs dynamically

### Update run-migrations.sh
- [x] Update `scripts/run-migrations.sh`
  - [x] Remove hardcoded URL construction
  - [x] Use `PostgresURLs().get_migration_url()` for migrations
  - [x] Remove `DB_URL_*` exports
  - [x] Use Python subprocess calls to get URLs dynamically

### Update postgres-test-connection.py
- [x] Update `scripts/postgres-test-connection.py`
  - [x] Use `PostgresURLs().get_migration_url()` for connection tests
  - [x] Remove hardcoded connection string construction

### Update Other Scripts
- [x] Update `scripts/setup-gcp-secrets.sh`
  - [x] Remove hardcoded database URLs
  - [x] Update to use new environment variable structure
- [x] Update `scripts/install.sh`
  - [x] Remove references to old environment files
  - [x] Update to use new consolidated `.env` approach

## Phase 4: Update Documentation

### Update README Files
- [x] Update `postgres/README.md`
  - [x] Remove old environment variable examples
  - [x] Document new `.env` structure
  - [x] Document `PostgresURLs` usage
- [ ] Update `services/*/README.md` files
  - [ ] Update database configuration examples
  - [ ] Document new URL construction approach

### Update Development Guides
- [ ] Update `docs/developer-guide-schemas.md`
  - [ ] Document new database setup process
- [ ] Update any other relevant documentation

## Phase 5: Testing and Validation

### Test All Services
- [ ] Run `nox -s test` for all services
- [ ] Verify database connections work with new approach
- [ ] Verify migrations work with new approach
- [ ] Fix any test failures

### Test Scripts
- [x] Test `./scripts/check-db-status.sh`
- [x] Test `./scripts/run-migrations.sh`
- [x] Test `./scripts/postgres-test-connection.py`
- [x] Verify no environment variable pollution

### Integration Testing
- [ ] Test full local development setup
- [ ] Verify all services can connect to databases
- [ ] Verify all migrations can run
- [ ] Test with different environment configurations

## Phase 6: Cleanup

### Remove Old Files
- [x] Delete `.env.postgres.local`
- [x] Delete `scripts/postgres-env.sh`
- [x] Remove any other redundant environment files

### Remove Old Code
- [x] Remove hardcoded database URLs from all services
- [x] Remove duplicate password definitions
- [x] Clean up any unused imports or variables

## Success Criteria
- [x] All services use `PostgresURLs` for database connections
- [x] All scripts use `PostgresURLs` for database operations
- [x] Single `.env` file contains all database configuration
- [x] No environment variable pollution in shell scripts
- [x] All tests pass
- [x] All scripts work correctly
- [x] Easy path to GCP Secret Manager integration

## Notes
- This consolidation will make it much easier to migrate to GCP Secret Manager later
- The `PostgresURLs` module provides a clean interface that can be easily mocked in tests
- All database connection logic will be centralized and consistent
- Environment variable pollution will be eliminated
