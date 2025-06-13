# Update User Management Tests to Use Base Classes

## Overview
Update all user management test classes to inherit from `BaseUserManagementTest` or `BaseUserManagementIntegrationTest` instead of manually setting up environment variables. This will fix CI failures due to missing `DB_URL_USER_MANAGEMENT` and ensure consistent test setup.

## Base Classes Available
- `BaseUserManagementTest` - For unit tests that need environment variables
- `BaseUserManagementIntegrationTest` - For integration tests that need full app setup

## Files to Update

### ✅ Already Updated
- [x] `test_integration_endpoints.py` - All classes now inherit from `BaseUserManagementIntegrationTest`
- [x] `test_main.py` - `TestApplicationStartup` and `TestHealthEndpoint` updated

### 🔄 Partially Updated
- [ ] `test_main.py` - Update remaining classes:
  - [ ] `TestReadinessEndpoint` → `BaseUserManagementTest`
  - [ ] `TestExceptionHandling` → `BaseUserManagementTest`
  - [ ] `TestMiddleware` → `BaseUserManagementTest`
  - [ ] `TestAPIDocumentation` → `BaseUserManagementTest`

### ❌ Need Full Update
- [ ] `test_audit_service.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_auth.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_encryption.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_internal_endpoints.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_models.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_oauth_config.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_preferences.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_retry_utils.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_settings.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_token_service.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_user_endpoints.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_validation_security.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_webhook_endpoints.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_webhook_service.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_exception_handling.py` - All classes need to inherit from `BaseUserManagementTest`
- [ ] `test_integration_schemas.py` - All classes need to inherit from `BaseUserManagementTest`

## Update Pattern

### For each test file:

1. **Add import:**
   ```python
   from services.user_management.tests.test_base import BaseUserManagementTest
   # or for integration tests:
   from services.user_management.tests.test_base import BaseUserManagementIntegrationTest
   ```

2. **Update class inheritance:**
   ```python
   # Before:
   class TestSomething:
   
   # After:
   class TestSomething(BaseUserManagementTest):
   ```

3. **Update setup_method:**
   ```python
   # Before:
   def setup_method(self):
       self.db_fd, self.db_path = tempfile.mkstemp()
       os.environ["DB_URL_USER_MANAGEMENT"] = f"sqlite:///{self.db_path}"
       os.environ["TOKEN_ENCRYPTION_SALT"] = "dGVzdC1zYWx0LTE2Ynl0ZQ=="
       os.environ["API_FRONTEND_USER_KEY"] = "test-api-key"
       os.environ["CLERK_SECRET_KEY"] = "test-clerk-key"
       # ... other setup
   
   # After:
   def setup_method(self):
       super().setup_method()  # Handles all environment variables
       # ... other setup (TestClient, etc.)
   ```

4. **Remove teardown_method if it only handles database cleanup:**
   ```python
   # Remove this if it only does database cleanup:
   def teardown_method(self):
       os.close(self.db_fd)
       os.unlink(self.db_path)
   ```

5. **Remove manual environment variable setup:**
   - Remove `tempfile.mkstemp()` calls
   - Remove `os.environ["DB_URL_USER_MANAGEMENT"]` assignments
   - Remove other environment variable assignments that are handled by base class

## Files with Manual Environment Variable Setup

Based on grep search, these files have manual `DB_URL_USER_MANAGEMENT` setup:

- `test_encryption.py` (line 28)
- `test_audit_service.py` (line 74)
- `test_webhook_service.py` (line 28)
- `test_webhook_endpoints.py` (lines 28, 416, 489, 512)
- `test_token_service.py` (line 34)
- `test_internal_endpoints.py` (line 26)
- `test_main.py` (lines 117, 130, 144, 156, 173, 204, 218, 232, 246, 258, 277, 297, 346, 378)
- `test_preferences.py` (lines 179, 376)

## Testing After Updates

After updating each file, test it:
```bash
pytest services/user_management/tests/test_filename.py -v
```

## Benefits After Completion

- ✅ CI will work without local `.env` files
- ✅ Consistent test environment setup
- ✅ DRY - no repeated environment variable setup
- ✅ Easier maintenance - changes in one place
- ✅ Proper cleanup of temporary files

## Notes

- Use `BaseUserManagementTest` for most tests
- Use `BaseUserManagementIntegrationTest` only for tests that need full FastAPI app setup with HTTP patches
- The base classes handle all required environment variables automatically
- Temporary database files are automatically created and cleaned up 