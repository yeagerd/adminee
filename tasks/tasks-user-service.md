# User Service Task List

## References
* Design doc: `documentation/user-management-service.md`
* Backend architecture: `/documentation/backend-architecture.md`

## Task Management Protocol

### Workflow
1. Check next available sub-task before starting work
2. Complete one sub-task at a time
3. Update task list after each sub-task completion
4. Make descriptive git commit after completing full tasks

### Task List Updates
- Mark completed sub-tasks: `[ ]` → `[x]`
- Mark parent task complete when all sub-tasks are `[x]`
- Add new tasks as discovered
- Maintain "Relevant Files" section with one-line descriptions for all created/modified files

## General instructions for working in Python in this repo

### Setup
* Set up the unified development environment: `./setup-dev.sh`
* The virtual environment will be automatically activated
* Run all Python commands from the repository root.

### Before committing
* Run `pytest` and fix all test failures.
* Run `mypy services/` and resolve all type errors.
* Fix lint issues using `./fix`
* Run ``tox -p auto`` to validate the full test matrix and environment compatibility.


## User Management Service Implementation Tasks

## Relevant Files

### Phase 1: Project Setup & Foundation
- `requirements.txt` - Added FastAPI, Ormar, Pydantic, cryptography, next-auth, celery, structlog dependencies # Replaced clerk-backend-api with next-auth
- `services/user/` - Main service directory with auth, models, routers, services, utils subdirectories
- `services/user/main.py` - FastAPI application entry point with health check endpoint
- `services/user/settings.py` - Pydantic Settings configuration for environment variables
- `services/user/database.py` - Database connection and Ormar configuration with modern OrmarConfig
- `services/user/alembic/` - Alembic migration configuration
- `services/user/logging_config.py` - Structlog configuration for structured logging
- `Dockerfile.user-service` - Python/FastAPI Docker configuration
- `docker-compose.yml` - Updated with user-management service and Redis
- `services/user/tests/test_settings.py` - Unit tests for settings configuration

### Phase 2: Database Models & Schema
- `services/user/models/user.py` - User model with NextAuth ID, email, profile info, onboarding status
- `services/user/models/preferences.py` - UserPreferences model with UI, notification, AI, integration, privacy settings
- `services/user/models/integration.py` - Integration model with provider/status enums, OAuth metadata
- `services/user/models/token.py` - EncryptedToken model for secure OAuth token storage with user-specific encryption
- `services/user/models/audit.py` - AuditLog model for compliance tracking and security monitoring
- `services/user/models/__init__.py` - Model imports and exports for metadata registration
- `services/user/alembic/versions/791881f77389_initial_schema.py` - Auto-generated migration with all tables and performance indexes
- `services/user/tests/test_models.py` - Comprehensive unit tests for all models, validation, and relationships

### Phase 3: Basic FastAPI Application Structure
- `services/user/main.py` - Enhanced FastAPI application with CORS middleware, exception handlers, database lifecycle, and router registration
- `services/user/settings.py` - Updated with CORS origins and environment configuration
- `services/user/logging_config.py` - Added setup_logging function for main.py import compatibility
- `services/user/exceptions.py` - Comprehensive custom exception classes with HTTP status mappings and structured error responses
- `services/user/routers/users.py` - User profile management router with placeholder endpoints
- `services/user/routers/preferences.py` - User preferences management router with placeholder endpoints
- `services/user/routers/integrations.py` - OAuth integrations management router with placeholder endpoints
- `services/user/routers/webhooks.py` - Webhook handling router for external providers with placeholder endpoints
- `services/user/routers/internal.py` - Internal service-to-service API with secure token retrieval, automatic refresh, scope validation, and comprehensive error handling with service authentication
- `services/user/services/token_service.py` - Dedicated token service for internal API operations with encrypted storage, automatic refresh, scope validation, and user status tracking
- `services/user/routers/__init__.py` - Router package exports for main application registration
- `services/user/tests/test_main.py` - Comprehensive unit tests for application startup, health endpoint, exception handling, and middleware

### Phase 2: User Authentication & Authorization
- `requirements.txt` - Added PyJWT dependency for JWT token handling
- `services/user/auth/nextauth.py` - NextAuth JWT token validation with verify_jwt_token, get_current_user, and user ownership verification (Replaced clerk.py)
- `services/user/auth/service_auth.py` - Service-to-service API key authentication with multiple header format support and permission validation
- `services/user/auth/__init__.py` - Authentication package exports for easy importing
- `services/user/tests/test_auth.py` - Comprehensive unit tests for JWT validation, service authentication, and authorization checks
- `services/user/schemas/user.py` - Pydantic schemas for user CRUD operations with validation and serialization
- `services/user/schemas/__init__.py` - Schema package exports for all user-related request/response models
- `services/user/services/user_service.py` - User service business logic for profile operations, onboarding, and search functionality
- `services/user/routers/users.py` - Enhanced user profile management router with full CRUD operations, authentication, and authorization
- `services/user/tests/test_user_endpoints.py` - Comprehensive unit tests for all user profile endpoints including success and error scenarios
- `services/user/schemas/webhook.py` - Pydantic schemas for NextAuth webhook events with validation and email extraction
- `services/user/services/webhook_service.py` - Webhook service business logic for processing NextAuth user lifecycle events
- `services/user/auth/webhook_auth.py` - Webhook signature verification for NextAuth webhooks with HMAC validation
- `services/user/routers/webhooks.py` - Enhanced webhook router with NextAuth event handling, signature verification, and comprehensive error handling
- `services/user/tests/test_webhook_endpoints.py` - Comprehensive unit tests for webhook processing including signature validation and event handling

### Phase 3: User Preferences Management
- `services/user/schemas/preferences.py` - Comprehensive Pydantic schemas for all preference categories including UI, notification, AI, integration, and privacy settings with validation
- `services/user/routers/preferences.py` - Enhanced preferences router with full CRUD operations, partial updates, reset functionality, authentication, and authorization
- `services/user/services/preferences_service.py` - Preferences service business logic for managing user preferences including default value management and preference validation
- `services/user/services/__init__.py` - Updated services package exports to include preferences service
- `services/user/exceptions.py` - Added DatabaseException class for compatibility with preferences service
- `services/user/tests/test_preferences.py` - Comprehensive unit tests for preferences functionality including validation, partial updates, and default value handling

### Phase 4: Token Encryption & Security
- `services/user/security/` - Security package for encryption and key management utilities
- `services/user/security/__init__.py` - Security package exports for TokenEncryption class
- `services/user/security/encryption.py` - TokenEncryption class with AES-256-GCM encryption, PBKDF2 key derivation, user-specific keys, and key rotation support
- `services/user/settings.py` - Updated with token_encryption_salt configuration for secure key derivation
- `services/user/tests/test_encryption.py` - Comprehensive unit tests for token encryption including security scenarios, error handling, and edge cases
- `services/user/tests/test_settings.py` - Updated settings tests for encryption configuration

### Phase 5: Audit Logging & Compliance
- `services/user/services/audit_service.py` - Comprehensive audit logging service with AuditLogger class, structured logging, database persistence, querying, analytics, and retention policies
- `services/user/exceptions.py` - Added AuditException for audit operation failures
- `services/user/services/__init__.py` - Updated to export audit_logger for easy importing
- `services/user/tests/test_audit_service.py` - Comprehensive unit tests for audit logging covering all functionality including logging, querying, analytics, security tracking, compliance reporting, and data retention policies

### Phase 6: OAuth Integration Management
- `services/user/integrations/` - OAuth provider configurations and integration management package
- `services/user/integrations/__init__.py` - Integrations package exports for OAuth configuration classes
- `services/user/integrations/oauth_config.py` - Comprehensive OAuth configuration with Google and Microsoft providers, PKCE support, state management, token exchange, user info retrieval, and security features
- `services/user/tests/test_oauth_config.py` - Comprehensive unit tests for OAuth configuration covering PKCE challenges, state validation, provider management, token operations, and integration workflows
- `services/user/routers/integrations.py` - Complete integration router with OAuth flow management (start/callback), CRUD operations (list/disconnect/refresh), health monitoring, and comprehensive authentication/authorization
- `services/user/services/integration_service.py` - Full integration service with OAuth flow handling, token management, refresh operations, health checks, statistics, and encrypted token storage
- `services/user/tests/test_integration_endpoints.py` - Comprehensive test suite covering all 20 integration endpoints including OAuth flows, CRUD operations, authentication, authorization, error handling, and security scenarios

### Phase 8: Error Handling & Validation
- `services/user/utils/retry.py` - Comprehensive retry utilities with exponential backoff, jitter, transient error detection, and convenience decorators for database, API, and OAuth operations
- `services/user/tests/test_retry_utils.py` - Comprehensive unit tests for retry utilities covering all functionality including async/sync retry, decorators, jitter, exponential backoff, and error handling scenarios
- `services/user/tests/test_exception_handling.py` - Complete unit tests for all exception types, error response formatting, user-friendly messages, and exception hierarchy validation
- `services/user/utils/validation.py` - Comprehensive validation utilities with custom validators for email addresses, URLs, timezone strings, phone numbers, and security-focused input validation including SQL injection and XSS protection
- `services/user/middleware/sanitization.py` - Input sanitization middleware for automatic sanitization of all incoming user data to prevent XSS, injection attacks, and other security vulnerabilities with configurable strict mode
- `services/user/tests/test_validation_security.py` - Comprehensive unit tests for validation utilities and security features including edge cases, malicious input attempts, and performance testing

### Demo & Testing
- `services/demos/user_management_demo.py` - Comprehensive interactive demo showcasing all user management features including OAuth flows, profile management, preferences, and service APIs with real browser-based OAuth authorization
- `services/demos/user_management_simple.py` - Lightweight demo script for quick testing of core user management functionality without OAuth dependencies
- `services/demos/oauth_callback_handler.py` - OAuth callback handler server for capturing real OAuth authorization codes during demo flows
- `services/demos/README_user_management.md` - Comprehensive documentation for user management demos including setup instructions, OAuth configuration, and troubleshooting guide

### Phase 1: Project Setup & Foundation

* [x] 1. Project Structure & Environment Setup
* [x] 1.1 Create new Python project with FastAPI, Ormar, Pydantic dependencies in requirements.txt
* [x] 1.2 Set up project structure: `services/user/{auth,models,routers,services,utils}/__init__.py`
* [x] 1.3 Create `settings.py` using Pydantic Settings for environment variable management
* [x] 1.4 Configure PostgreSQL connection string and database configuration
* [x] 1.5 Initialize Alembic with `alembic init alembic` and configure `alembic.ini`
* [x] 1.6 Set up structlog configuration in `logging_config.py`
* [x] 1.7 Create `Dockerfile` and `docker-compose.yml` for development environment
* [x] 1.8 Write unit tests for settings configuration and environment variable loading
* [x] 1.9 Run `./fix` to format and lint code
* [x] 1.10 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [x] 2. Database Models & Schema
* [x] 2.1 Create `models/user.py` with User model including id, email, first_name, last_name, profile_image_url, onboarding fields, timestamps
* [x] 2.2 Create `models/preferences.py` with UserPreferences model including UI, notification, AI, integration, and privacy preferences
* [x] 2.3 Create `models/integration.py` with Integration model including provider enum, status enum, and relationship to User
* [x] 2.4 Create `models/token.py` with EncryptedToken model including foreign keys to User and Integration
* [x] 2.5 Create `models/audit.py` with AuditLog model for compliance tracking
* [x] 2.6 Create `models/__init__.py` to import all models and set up database metadata
* [x] 2.7 Generate initial Alembic migration with `alembic revision --autogenerate -m "Initial schema"`
* [x] 2.8 Add database indexes in migration file for user_id, provider, status, created_at fields
* [x] 2.9 Write unit tests for all model creation, validation, and relationship queries
* [x] 2.10 Run `./fix` to format and lint code
* [x] 2.11 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [x] 3. Basic FastAPI Application Structure
* [x] 3.1 Create `main.py` with FastAPI app initialization, CORS middleware, and error handling middleware
* [x] 3.2 Create router files: `routers/{users,preferences,integrations,webhooks,internal}.py`
* [x] 3.3 Implement `GET /health` endpoint returning service status and database connectivity
* [x] 3.4 Configure OpenAPI documentation with title, description, version, and contact info
* [x] 3.5 Create `exceptions.py` with custom exception classes and global exception handler
* [x] 3.6 Write unit tests for application startup, health endpoint, and exception handling
* [x] 3.7 Run `./fix` to format and lint code
* [x] 3.8 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 2: User Authentication & Authorization

* [x] 4. Authentication Middleware
* [x] 4.1 Create `auth/nextauth.py` with NextAuth JWT token validation using appropriate NextAuth SDK/library (Replaced clerk.py task)
* [x] 4.2 Implement `verify_jwt_token()` function to validate and decode NextAuth JWT tokens
* [x] 4.3 Create `get_current_user()` dependency to extract user_id from JWT claims
* [x] 4.4 Implement service-to-service API key authentication in `auth/service_auth.py`
* [ ] 4.5 Create rate limiting middleware using fastapi-limiter with Redis backend
* [x] 4.6 Implement `verify_user_ownership()` helper to ensure users can only access their own data
* [x] 4.7 Write unit tests for JWT validation, user extraction, and authorization checks
* [x] 4.8 Run `./fix` to format and lint code
* [x] 4.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [x] 5. User Profile CRUD Operations
* [x] 5.1 Create `schemas/user.py` with Pydantic models for UserResponse, UserUpdate, and UserCreate
* [x] 5.2 Implement `GET /users/{user_id}` endpoint in `routers/users.py` with authentication and authorization
* [x] 5.3 Implement `PUT /users/{user_id}` endpoint with request validation and audit logging
* [x] 5.4 Implement `DELETE /users/{user_id}` endpoint with soft delete functionality
* [x] 5.5 Create `services/user_service.py` with business logic for user operations
* [x] 5.6 Add comprehensive error handling with proper HTTP status codes and error messages
* [x] 5.7 Write unit tests for all endpoints including success and error scenarios
* [x] 5.8 Run `./fix` to format and lint code
* [x] 5.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [x] 6. NextAuth Webhook Integration (Replaced Clerk Webhook Integration)
* [x] 6.1 Install and configure NextAuth webhook handling (e.g., using its SDK or manual signature verification if applicable)
* [x] 6.2 Create `POST /webhooks/nextauth` endpoint in `routers/webhooks.py` (or adjust existing if path is generic)
* [x] 6.3 Implement webhook signature verification using NextAuth's webhook secret/mechanism
* [x] 6.4 Handle `user.created` event: create User record and default UserPreferences
* [x] 6.5 Handle `user.updated` event: update User record with new information
* [x] 6.6 Handle `user.deleted` event: soft delete User and cascade to related records
* [x] 6.7 Add error handling, logging, and idempotency for webhook processing
* [x] 6.8 Write unit tests for webhook processing including signature validation and event handling
* [x] 6.9 Run `./fix` to format and lint code
* [x] 6.10 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 3: User Preferences Management

* [x] 7. Preferences API Implementation
* [x] 7.1 Create `schemas/preferences.py` with comprehensive Pydantic models for all preference categories
* [x] 7.2 Implement `GET /users/{user_id}/preferences` endpoint returning all user preferences
* [x] 7.3 Implement `PUT /users/{user_id}/preferences` with support for partial updates using PATCH semantics
* [x] 7.4 Implement `POST /users/{user_id}/preferences/reset` to restore default preferences
* [x] 7.5 Add validation for preference values including enums for theme, timezone, language, etc.
* [x] 7.6 Create `services/preferences_service.py` with preference management business logic
* [x] 7.7 Write unit tests for preference validation, partial updates, and default value handling
* [x] 7.8 Run `./fix` to format and lint code
* [x] 7.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 4: Token Encryption & Security

* [x] 9. Token Encryption Implementation
* [x] 9.1 Create `security/encryption.py` with TokenEncryption class using cryptography library
* [x] 9.2 Implement `derive_user_key()` method using PBKDF2 with user_id and service salt
* [x] 9.3 Implement `encrypt_token()` method using AES-256-GCM with user-specific keys
* [x] 9.4 Implement `decrypt_token()` method with proper error handling for invalid tokens
* [x] 9.5 Add key rotation support with versioned encryption keys
* [x] 9.6 Create comprehensive error handling for encryption failures and key derivation issues
* [x] 9.7 Write unit tests for encryption/decryption, key derivation, and error scenarios
* [x] 9.8 Run `./fix` to format and lint code
* [x] 9.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [x] 10. Audit Logging System
* [x] 10.1 Create `services/audit_service.py` with AuditLogger class
* [x] 10.2 Implement `log_audit_event()` method with structured logging using structlog
* [x] 10.3 Add audit logging to all user profile changes, preference updates, and token operations
* [x] 10.4 Implement audit log querying with filtering by user, action, date range
* [x] 10.5 Create audit log retention policy with automatic cleanup of old logs
* [x] 10.6 Add audit log analytics functions for compliance reporting
* [x] 10.7 Write unit tests for audit logging, querying, and retention policies
* [x] 10.8 Run `./fix` to format and lint code
* [x] 10.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 5: OAuth Integration Management

* [x] 11. OAuth Provider Configuration
* [x] 11.1 Create `integrations/oauth_config.py` with Google and Microsoft OAuth configurations
* [x] 11.2 Implement OAuth state generation and validation with PKCE support
* [x] 11.3 Create authorization URL generation for each provider with proper scopes
* [x] 11.4 Implement authorization code exchange for access and refresh tokens
* [x] 11.5 Add OAuth scope validation and management with provider-specific scope mapping
* [x] 11.6 Implement provider-specific user info retrieval using access tokens
* [x] 11.7 Write unit tests for OAuth configuration, state validation, and token exchange
* [x] 11.8 Run `./fix` to format and lint code
* [x] 11.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [x] 12. Integration Management Endpoints
* [x] 12.1 Create `schemas/integration.py` with Pydantic models for integration requests and responses
* [x] 12.2 Implement `GET /users/{user_id}/integrations` endpoint showing all user integrations
* [x] 12.3 Implement `POST /users/{user_id}/integrations/{provider}` for completing OAuth flow
* [x] 12.4 Implement `DELETE /users/{user_id}/integrations/{provider}` for disconnecting integrations
* [x] 12.5 Implement `PUT /users/{user_id}/integrations/{provider}/refresh` for manual token refresh
* [x] 12.6 Add integration status tracking and health monitoring
* [x] 12.7 Create `services/integration_service.py` with integration management business logic
* [x] 12.8 Write unit tests for all integration endpoints and business logic
* [x] 12.9 Run `./fix` to format and lint code
* [x] 12.10 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [x] 13. Secure Token Storage (where additive with 9. Token Encryption Implementation)
* [x] 13.1 Create `services/token_service.py` for encrypted token storage and retrieval
* [x] 13.2 Implement `store_tokens()` method with automatic encryption before database storage
* [x] 13.3 Implement `get_valid_token()` method with automatic refresh if token is expired
* [x] 13.4 Add token lifecycle management including creation, updates, and secure deletion
* [x] 13.5 Implement token expiration checking with configurable buffer time
* [x] 13.6 Add token revocation procedures that notify providers when possible
* [x] 13.7 Write unit tests for token storage, retrieval, refresh, and lifecycle management
* [x] 13.8 Run `./fix` to format and lint code
* [x] 13.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 6: Service-to-Service API

* [x] 14. Internal Token Retrieval API
* [x] 14.1 Create `routers/internal.py` with service-to-service authentication required
* [x] 14.2 Implement `POST /internal/tokens/get` endpoint for other services to retrieve user tokens
* [x] 14.3 Add automatic token refresh logic with expiration buffer (5 minutes)
* [x] 14.4 Implement scope validation ensuring requested scopes are available
* [x] 14.5 Add comprehensive error handling for token retrieval failures
* [x] 14.6 Implement request/response logging for audit trail of token access
* [x] 14.7 Create `POST /internal/tokens/refresh` endpoint for manual token refresh
* [x] 14.8 Write unit tests for internal API endpoints including authentication and error handling
* [x] 14.9 Run `./fix` to format and lint code
* [x] 14.10 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 8: Error Handling & Validation

* [x] 18. Comprehensive Error System
* [x] 18.1 Update `exceptions.py` with all custom exception classes mentioned in design doc
* [x] 18.2 Implement standardized error response format with type, message, details, timestamp, request_id
* [x] 18.3 Create global exception handler that maps exceptions to appropriate HTTP status codes
* [x] 18.4 Add error logging with full context including stack traces and request details
* [x] 18.5 Implement user-friendly error messages for common failure scenarios
* [x] 18.6 Create error recovery procedures for transient failures with automatic retry
* [x] 18.7 Write unit tests for all exception types and error handling scenarios
* [x] 18.8 Run `./fix` to format and lint code
* [x] 18.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [x] 19. Input Validation & Security
* [x] 19.1 Review and enhance all Pydantic schemas with comprehensive validation rules
* [x] 19.2 Add input sanitization middleware for user-provided text data
* [x] 19.3 Create custom validators for email addresses, URLs, timezone strings, and other domain-specific fields
* [x] 19.4 Implement SQL injection prevention through parameterized queries (verify Ormar usage)
* [x] 19.5 Add XSS protection for all text fields with proper escaping
* [x] 19.6 Create validation unit tests covering edge cases and malicious input attempts
* [x] 19.7 Run `./fix` to format and lint code
* [x] 19.8 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 6.5: Basic health endpoints

* [x] 26.3 Create load balancer health check endpoints (`/health`, `/ready`).  Write unit tests for new functionality. Run `./fix` and `tox -p auto` and fix issues.

### Phase 7: Background Jobs & Maintenance

* [ ] 16. Celery Setup
* [ ] 16.1 Install Celery and configure with Redis broker in `celery_config.py`
* [ ] 16.2 Create `celery_app.py` with Celery application configuration and task routing
* [ ] 16.3 Set up Celery worker configuration with proper error handling and logging
* [ ] 16.4 Add Celery monitoring endpoints for health checks and task status
* [ ] 16.5 Configure task retry logic with exponential backoff for transient failures
* [ ] 16.6 Write unit tests for Celery configuration and task execution
* [ ] 16.7 Run `./fix` to format and lint code
* [ ] 16.8 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [ ] 17. Background Tasks Implementation
* [ ] 17.1 Create `tasks/token_refresh.py` with proactive token refresh task (runs hourly)
* [ ] 17.2 Implement `tasks/data_cleanup.py` for cleaning up soft-deleted users (runs daily)
* [ ] 17.3 Create `tasks/integration_health.py` for checking integration status (runs every 15 minutes)
* [ ] 17.4 Implement `tasks/audit_cleanup.py` for audit log archival and cleanup (runs weekly)
* [ ] 17.5 Add `tasks/user_analytics.py` for user activity tracking and analytics
* [ ] 17.6 Create `tasks/backup_verification.py` for verifying backup integrity
* [ ] 17.7 Set up Celery Beat for task scheduling with crontab expressions
* [ ] 17.8 Write unit tests for all background tasks and scheduling
* [ ] 17.9 Run `./fix` to format and lint code
* [ ] 17.10 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 9: Comprehensive Testing

* [ ] 20. Unit Test Suite
* [ ] 20.1 Create comprehensive unit tests for all encryption/decryption functions with edge cases
* [ ] 20.2 Implement unit tests for OAuth flow logic including error scenarios and edge cases
* [ ] 20.3 Add unit tests for preference management including validation and inheritance
* [ ] 20.4 Create unit tests for user profile operations covering all CRUD scenarios
* [ ] 20.5 Implement unit tests for audit logging functionality and log retention
* [ ] 20.6 Add unit tests for background job logic and error handling
* [ ] 20.7 Create unit tests for all error handling scenarios and exception types
* [ ] 20.8 Run `./fix` to format and lint code
* [ ] 20.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [ ] 21. Integration Test Suite
* [ ] 21.1 Set up test database with fixtures using pytest and pytest-asyncio
* [ ] 21.2 Create integration tests for all API endpoints with real database operations
* [ ] 21.3 Implement OAuth flow testing with mock provider responses using httpx-mock
* [ ] 21.4 Add database transaction testing to ensure data consistency
* [ ] 21.5 Create service-to-service communication tests with mock internal API calls
* [ ] 21.6 Implement webhook integration testing with mock NextAuth webhook events (Replaced Clerk)
* [ ] 21.7 Add performance testing for token operations and database queries
* [ ] 21.8 Run `./fix` to format and lint code
* [ ] 21.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [ ] 22. Security Testing
* [ ] 22.1 Implement token security tests verifying encryption strength and key derivation
* [ ] 22.2 Create access control tests ensuring users can only access their own data
* [ ] 22.3 Add data isolation tests preventing cross-user data leakage
* [ ] 22.4 Implement audit logging completeness tests for all sensitive operations
* [ ] 22.5 Create rate limiting tests to verify abuse prevention mechanisms
* [ ] 22.6 Add vulnerability scanning tests for common security issues (SQL injection, XSS, etc.)
* [ ] 22.7 Write unit tests for security features and run security-focused test scenarios
* [ ] 22.8 Run `./fix` to format and lint code
* [ ] 22.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 10: Monitoring & Observability

* [ ] 23. Metrics Collection
* [ ] 23.1 Install and configure Prometheus client library for Python
* [ ] 23.2 Add custom metrics for token operations (encrypt/decrypt time, refresh success rate)
* [ ] 23.3 Create API performance metrics (request duration, error rates by endpoint)
* [ ] 23.4 Implement integration health metrics (connection status, OAuth success rates)
* [ ] 23.5 Add user activity metrics (login frequency, preference changes, integration usage)
* [ ] 23.6 Create database performance metrics (query duration, connection pool usage)
* [ ] 23.7 Write unit tests for metrics collection and export functionality
* [ ] 23.8 Run `./fix` to format and lint code
* [ ] 23.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [ ] 24. Logging & Tracing
* [ ] 24.1 Enhance structlog configuration with correlation IDs for request tracing
* [ ] 24.2 Add OpenTelemetry integration for distributed tracing across services
* [ ] 24.3 Create log aggregation configuration for centralized logging (ELK stack or similar)
* [ ] 24.4 Implement log retention policies with automatic archival and cleanup
* [ ] 24.5 Add performance profiling capabilities for identifying bottlenecks
* [ ] 24.6 Create operational dashboards configuration for monitoring service health
* [ ] 24.7 Write unit tests for logging configuration and trace correlation
* [ ] 24.8 Run `./fix` to format and lint code
* [ ] 24.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors


### Phase 10.5: Advanced User Preferences

* [ ] 8. Advanced Preferences Features
* [ ] 8.1 Implement preference inheritance system with system defaults and user overrides
* [ ] 8.2 Add preference validation schema with custom validators for complex fields
* [ ] 8.3 Create preference migration system for handling schema changes
* [ ] 8.4 Implement preference history tracking for audit and rollback capabilities
* [ ] 8.5 Add preference export/import functionality for user data portability
* [ ] 8.6 Write unit tests for inheritance, validation, migration, and history features
* [ ] 8.7 Run `./fix` to format and lint code
* [ ] 8.8 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 11: Performance & Optimization

* [ ] 15. Integration Status Management
* [ ] 15.1 Create `services/integration_status_service.py` for monitoring integration health
* [ ] 15.2 Implement periodic health checks for each integration type
* [ ] 15.3 Add automatic status updates based on token refresh success/failure
* [ ] 15.4 Create integration diagnostic tools for troubleshooting connection issues
* [ ] 15.5 Implement status broadcasting to dependent services via webhooks or message queue
* [ ] 15.6 Add integration usage analytics and reporting capabilities
* [ ] 15.7 Write unit tests for status tracking, health checks, and diagnostic tools
* [ ] 15.8 Run `./fix` to format and lint code
* [ ] 15.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors


* [ ] 25. Database Optimization
* [ ] 25.1 Review and optimize all database queries using EXPLAIN ANALYZE
* [ ] 25.2 Add missing database indexes based on query patterns and performance testing
* [ ] 25.3 Configure connection pooling with optimal pool size and connection management
* [ ] 25.4 Implement database query result caching for frequently accessed data
* [ ] 25.5 Add request/response compression middleware for API endpoints
* [ ] 25.6 Optimize token encryption/decryption performance with caching and batching
* [ ] 25.7 Write performance tests and benchmarks for critical operations
* [ ] 25.8 Run `./fix` to format and lint code
* [ ] 25.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [ ] 26. Scalability Features
* [ ] 26.1 Implement horizontal scaling support with stateless service design
* [ ] 26.2 Add database read replica configuration for read-heavy operations
* [ ] 26.4 Implement graceful shutdown procedures for zero-downtime deployments
* [ ] 26.5 Add capacity planning tools and resource monitoring
* [ ] 26.6 Create auto-scaling configuration for container orchestration
* [ ] 26.7 Write unit tests for scalability features and health check endpoints
* [ ] 26.8 Run `./fix` to format and lint code
* [ ] 26.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 12: Documentation & Deployment

* [ ] 27. Documentation
* [ ] 27.1 Generate comprehensive OpenAPI documentation with examples and descriptions
* [ ] 27.2 Write deployment guide including environment setup and configuration
* [ ] 27.3 Create troubleshooting runbook with common issues and solutions  
* [ ] 27.4 Document security procedures including incident response and key rotation
* [ ] 27.5 Add developer onboarding guide with local development setup
* [ ] 27.6 Create architecture decision records (ADRs) for key design decisions
* [ ] 27.7 Write unit tests for documentation generation and API schema validation
* [ ] 27.8 Run `./fix` to format and lint code
* [ ] 27.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [ ] 28. Production Deployment
* [ ] 28.1 Set up CI/CD pipeline with GitHub Actions or similar including automated testing
* [ ] 28.2 Create optimized Docker images with multi-stage builds and security scanning
* [ ] 28.3 Implement Infrastructure as Code using Terraform or Kubernetes Helm charts
* [ ] 28.4 Configure production environment with proper secrets management and security groups
* [ ] 28.5 Add deployment strategies including blue-green deployments and rollback procedures
* [ ] 28.6 Set up production monitoring with alerting rules and incident response procedures
* [ ] 28.7 Implement automated backup procedures with disaster recovery testing
* [ ] 28.8 Write unit tests for deployment scripts and infrastructure configuration
* [ ] 28.9 Run `./fix` to format and lint code
* [ ] 28.10 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

### Phase 13: Final Integration & Production Readiness

* [ ] 29. End-to-End Testing
* [ ] 29.1 Create complete user journey tests from registration through integration setup
* [ ] 29.2 Test integration with Next.js frontend using realistic API calls
* [ ] 29.3 Validate service-to-service communication with other microservices in staging environment
* [ ] 29.4 Perform load testing under realistic traffic conditions using tools like Locust
* [ ] 29.5 Test disaster recovery procedures including database restoration and service failover
* [ ] 29.6 Validate all security measures including encryption, authentication, and authorization
* [ ] 29.7 Write comprehensive end-to-end test suite with realistic scenarios
* [ ] 29.8 Run `./fix` to format and lint code
* [ ] 29.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors

* [ ] 30. Production Go-Live
* [ ] 30.1 Complete security audit including penetration testing and vulnerability assessment
* [ ] 30.2 Perform final performance optimization and capacity planning validation
* [ ] 30.3 Validate all monitoring, alerting, and observability systems in production environment
* [ ] 30.4 Complete final documentation review and knowledge transfer to operations team
* [ ] 30.5 Conduct comprehensive code review with security and architecture teams
* [ ] 30.6 Execute production deployment plan with rollback procedures ready
* [ ] 30.7 Write post-deployment validation tests and monitoring checks
* [ ] 30.8 Run `./fix` to format and lint code
* [ ] 30.9 Run `tox -p auto` to run lint, type checking, and tests, fixing all errors