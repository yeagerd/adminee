# Secrets Migration Plan

## Overview
Migrate from using individual `settings.py`/`config.py` files to using the centralized `services/common/secrets.py` module for loading secrets across all services.

## Benefits
- **Unified secret management**: Single source of truth for secret loading logic
- **Better security**: Centralized GCP Secret Manager integration with fallback to env vars
- **Consistency**: All services use the same secret loading mechanism
- **Caching**: Built-in secret caching to avoid repeated API calls
- **Environment awareness**: Automatic handling of local vs production environments

## Current State Analysis

### Services Using Settings/Config Files
1. **Chat Service**: `services/chat_service/settings.py`
   - Uses Pydantic BaseSettings
   - Loads: database URL, API keys, service URLs, OpenAI API key, etc.

2. **User Management Service**: `services/user_management/settings.py`
   - Uses Pydantic BaseSettings
   - Loads: database URL, Clerk secrets, OAuth secrets, Redis URL, etc.

3. **Office Service**: `services/office_service/core/config.py`
   - Uses Pydantic BaseSettings
   - Loads: database URL, API keys, Redis URL, etc.

### Already Using Secrets Module
- `services/user_management/security/encryption.py` - already imports `get_token_encryption_salt`

## Migration Strategy

### Phase 1: Extend secrets.py module
- [ ] Add service-specific secret getters to `secrets.py`
- [ ] Add missing secret getters for all current environment variables
- [ ] Ensure backward compatibility during migration

### Phase 2: Update services to use secrets.py
- [ ] **Chat Service**: Update to use `secrets.py` instead of `settings.py`
- [ ] **User Management Service**: Update to use `secrets.py` instead of `settings.py`
- [ ] **Office Service**: Update to use `secrets.py` instead of `config.py`

### Phase 3: Clean up and testing
- [ ] Remove old settings/config files
- [ ] Update imports across all services
- [ ] Update tests to use `clear_cache()` helper
- [ ] Validate all services work with new secret loading

## Detailed Tasks

### Task 1: Extend secrets.py module

#### 1.1 Add Chat Service Secret Getters
- [ ] `get_chat_database_url()` - for `DB_URL_CHAT`
- [ ] `get_api_frontend_chat_key()` - for `API_FRONTEND_CHAT_KEY`
- [ ] `get_api_chat_user_key()` - for `API_CHAT_USER_KEY`
- [ ] `get_api_chat_office_key()` - for `API_CHAT_OFFICE_KEY`
- [ ] `get_user_management_service_url()` - for `USER_MANAGEMENT_SERVICE_URL`
- [ ] `get_office_service_url()` - for `OFFICE_SERVICE_URL`
- [ ] `get_llm_provider()` - for `LLM_PROVIDER`
- [ ] `get_llm_model()` - for `LLM_MODEL`

#### 1.2 Add User Management Service Secret Getters
- [ ] `get_user_management_database_url()` - for `DB_URL_USER_MANAGEMENT`
- [ ] `get_api_frontend_user_key()` - for `API_FRONTEND_USER_KEY`
- [ ] `get_clerk_webhook_secret()` - for `CLERK_WEBHOOK_SECRET`
- [ ] `get_clerk_jwt_key()` - for `CLERK_JWT_KEY`
- [ ] `get_google_client_id()` - for `GOOGLE_CLIENT_ID`
- [ ] `get_google_client_secret()` - for `GOOGLE_CLIENT_SECRET`
- [ ] `get_azure_ad_client_id()` - for `AZURE_AD_CLIENT_ID`
- [ ] `get_azure_ad_client_secret()` - for `AZURE_AD_CLIENT_SECRET`
- [ ] `get_azure_ad_tenant_id()` - for `AZURE_AD_TENANT_ID`
- [ ] `get_oauth_redirect_uri()` - for `OAUTH_REDIRECT_URI`
- [ ] `get_oauth_base_url()` - for `OAUTH_BASE_URL`
- [ ] `get_celery_broker_url()` - for `CELERY_BROKER_URL`
- [ ] `get_celery_result_backend()` - for `CELERY_RESULT_BACKEND`

#### 1.3 Add Office Service Secret Getters
- [ ] `get_office_database_url()` - for `DB_URL_OFFICE`
- [ ] `get_api_frontend_office_key()` - for `API_FRONTEND_OFFICE_KEY`
- [ ] `get_api_office_user_key()` - for `API_OFFICE_USER_KEY`

#### 1.4 Add General Configuration Getters
- [ ] `get_environment()` - for `ENVIRONMENT`
- [ ] `get_log_level()` - for `LOG_LEVEL`
- [ ] `get_log_format()` - for `LOG_FORMAT`
- [ ] `get_debug_mode()` - for `DEBUG`
- [ ] `get_cors_origins()` - for `CORS_ORIGINS` (return list)
- [ ] `get_jwt_verify_signature()` - for `JWT_VERIFY_SIGNATURE`

### Task 2: Update Chat Service

#### 2.1 Create new chat service configuration
- [ ] Create `services/chat_service/config.py` using `secrets.py`
- [ ] Implement `get_chat_config()` function that returns config dict
- [ ] Migrate all secret loading from `settings.py` to use `secrets.py`

#### 2.2 Update chat service imports
- [ ] Update `services/chat_service/main.py` to use new config
- [ ] Update `services/chat_service/database.py` to use new config
- [ ] Update any other files importing from `settings.py`

#### 2.3 Update chat service tests
- [ ] Update test files to use `secrets.clear_cache()` in setup/teardown
- [ ] Update test configuration to use new config system

### Task 3: Update User Management Service

#### 3.1 Create new user management service configuration
- [ ] Create `services/user_management/config.py` using `secrets.py`
- [ ] Implement `get_user_management_config()` function that returns config dict
- [ ] Migrate all secret loading from `settings.py` to use `secrets.py`

#### 3.2 Update user management service imports
- [ ] Update `services/user_management/main.py` to use new config
- [ ] Update `services/user_management/database.py` to use new config
- [ ] Update `services/user_management/auth/clerk.py` to use new config
- [ ] Update `services/user_management/integrations/oauth_config.py` to use new config
- [ ] Update any other files importing from `settings.py`

#### 3.3 Update user management service tests
- [ ] Update test files to use `secrets.clear_cache()` in setup/teardown
- [ ] Update test configuration to use new config system
- [ ] Update `services/user_management/tests/test_settings.py` to test new config

### Task 4: Update Office Service

#### 4.1 Create new office service configuration
- [ ] Update `services/office_service/core/config.py` to use `secrets.py`
- [ ] Implement `get_office_config()` function that returns config dict
- [ ] Migrate all secret loading from existing config to use `secrets.py`

#### 4.2 Update office service imports
- [ ] Update `services/office_service/main.py` to use new config
- [ ] Update `services/office_service/database.py` to use new config
- [ ] Update any other files importing from `core.config`

#### 4.3 Update office service tests
- [ ] Update test files to use `secrets.clear_cache()` in setup/teardown
- [ ] Update test configuration to use new config system

### Task 5: Clean up and validation

#### 5.1 Remove old configuration files
- [ ] Remove `services/chat_service/settings.py`
- [ ] Remove `services/user_management/settings.py`
- [ ] Update `services/office_service/core/config.py` (keep as wrapper if needed)

#### 5.2 Update documentation
- [ ] Update `services/common/README.md` with new secret getters
- [ ] Update service-specific documentation
- [ ] Update `.example.env` if needed

#### 5.3 Run comprehensive tests
- [ ] Run `pytest` across all services
- [ ] Run `mypy services/` to catch type errors
- [ ] Run `./fix` to fix any lint issues
- [ ] Run `tox` to validate full test matrix

## Implementation Notes

### Backward Compatibility
During migration, maintain backward compatibility by:
- Keeping existing settings files until fully migrated
- Using the same environment variable names
- Providing default values where appropriate

### Error Handling
- Ensure proper error handling for missing secrets in production
- Use appropriate defaults for development environment
- Log warnings for missing optional secrets

### Testing Strategy
- Use `secrets.clear_cache()` in test setup to ensure clean state
- Mock `secrets.py` functions in unit tests
- Test both local and production environment scenarios

## Risk Mitigation

### Potential Issues
1. **Circular imports**: Be careful with import order
2. **Missing secrets**: Ensure all required secrets are available
3. **Environment differences**: Test in multiple environments
4. **Cache invalidation**: Ensure cache is cleared appropriately in tests

### Rollback Plan
- Keep old configuration files until migration is complete and tested
- Use feature flags to switch between old and new configuration
- Have database backups ready before deployment

## Success Criteria
- [ ] All services load secrets from `services/common/secrets.py`
- [ ] No more individual `settings.py`/`config.py` files (except as thin wrappers)
- [ ] All tests pass with new configuration system
- [ ] Local development and production environments work correctly
- [ ] No performance degradation from secret loading 