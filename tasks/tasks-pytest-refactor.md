# Pytest Refactor Tasklist: Local Setup/Teardown for User Management & Chat Service Tests

## Refactor Instructions

1. **Remove all dependencies on conftest.py fixtures.**
   - Inline any fixtures (e.g., `client`, `sample_user_data`, `mock_user`, etc.) as class/static methods or properties in each test class.
   - If a fixture is used by multiple classes, duplicate it as needed for now.

2. **Add `setup_method` and `teardown_method` to each test class.**
   - In `setup_method`, create a temporary SQLite database file and set the appropriate environment variable (e.g., `DB_URL_USER_MANAGEMENT` or `DB_URL_CHAT`).
   - Initialize the FastAPI `TestClient` and any other per-class resources.
   - In `teardown_method`, close and delete the temporary database file and clean up any resources.

3. **Add a `_clean_database` helper method to each class if needed.**
   - Use this to clear tables or reset state before each test.
   - Call this from `setup_method` or at the start of each test as appropriate.

4. **Replace all uses of pytest fixtures (e.g., `client`, `clean_database`, etc.) with `self.` references.**
   - For example, use `self.client` instead of a `client` fixture.
   - Use `self.sample_user_data()` instead of a fixture.

5. **Ensure all test methods are self-contained and do not rely on global state.**
   - Each test should be able to run independently and in any order.

6. **Remove any remaining references to conftest.py or global fixtures.**

7. **Test each file independently with `pytest path/to/test_file.py` to ensure correctness.**

8. Process one test file at a time, and mark it complete in the list below once it passes.

---

**Goal:**
- All test files in `services/user_management/tests/` and `services/chat_service/tests/` use local setup/teardown and are fully isolated.
- No `conftest.py` is needed for these services. Remove once complete.
- All tests pass when run individually or as a suite. 


## User Management Test Files to Refactor

- [ ] test_main.py
- [ ] test_user_endpoints.py
- [ ] test_oauth_config.py
- [ ] test_integration_endpoints.py
- [ ] test_encryption.py
- [ ] test_settings.py
- [ ] test_webhook_endpoints.py
- [ ] test_preferences.py
- [ ] test_auth.py
- [ ] test_audit_service.py
- [ ] test_token_service.py
- [ ] test_exception_handling.py
- [ ] test_models.py
- [ ] test_validation_security.py
- [ ] test_internal_endpoints.py
- [ ] test_retry_utils.py
- [ ] test_integration_schemas.py
- [x] test_webhook_service.py

## Chat Service Test Files to Refactor (DB/History Isolation)

- [ ] test_llama_manager.py
- [ ] test_llama_manager_integration.py
- [ ] test_llm_tools.py
- [ ] test_chat_agent.py
- [ ] test_chat_service_e2e.py
- [ ] test_history_manager.py
- [ ] test_hello_pytest.py

> **Note:**
> - All chat service tests that interact with the history database (e.g., via `history_manager.py`) must use local setup/teardown and a unique temporary SQLite DB per test class or method.
> - Remove or inline any fixtures from `conftest.py` and ensure no global DB state is shared between tests.
