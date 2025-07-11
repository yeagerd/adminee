# Email-to-User-ID Resolution Implementation

## Overview
Implement a backend endpoint that resolves email addresses to external_auth_id, allowing the frontend to handle email normalization transparently. This eliminates the need for frontend email normalization and future-proofs the system.

## Prerequisites
- Understand the existing email normalization in `services/user/utils/email_collision.py`
- Review the current chat.py demo authentication flow
- Familiarize yourself with the user service API patterns

---

## Tasks

### 1. Create Email Resolution Endpoint
**File:** `services/user/routers/users.py`
**Dependency:** None
**Status:** pending

Create a new endpoint `POST /users/resolve-email` that:
- Accepts an email address in the request body
- Returns the corresponding external_auth_id
- Handles email normalization internally
- Returns proper error responses for not found

**Expected API:**
```json
POST /users/resolve-email
Request: {"email": "john.doe+work@gmail.com"}
Response: {"external_auth_id": "user_a1b2c3d4e5f67890", "email": "john.doe@gmail.com"}
```

### 2. Add Email Resolution Schema
**File:** `services/user/schemas/user.py`
**Dependency:** None
**Status:** pending

Create Pydantic models for:
- `EmailResolutionRequest` - input schema
- `EmailResolutionResponse` - output schema

Include proper validation and documentation.

### 3. Implement Email Resolution Service Logic
**File:** `services/user/services/user_service.py`
**Dependency:** Task 2
**Status:** pending

Add method `resolve_email_to_user_id()` that:
- Takes raw email input
- Uses existing email normalization utilities
- Queries database by normalized_email
- Returns external_auth_id and original email from database
- Handles case where user doesn't exist

### 4. Add Database Query Method
**File:** `services/user/services/user_service.py`
**Dependency:** Task 3
**Status:** pending

Add database method to find user by normalized email:
- Query users table by normalized_email column
- Handle multiple matches (edge case)
- Return None if no match found

### 5. Add Comprehensive Unit Tests
**File:** `services/user/tests/test_email_resolution.py`
**Dependency:** Tasks 1-4
**Status:** pending

Test scenarios:
- Valid email resolution for each provider (Gmail, Outlook, Yahoo)
- Email normalization edge cases (dots, plus addressing)
- Non-existent email handling
- Invalid email format handling
- Database error scenarios

### 6. Add Integration Tests
**File:** `services/user/tests/test_user_endpoints.py`
**Dependency:** Task 5
**Status:** pending

Test the full API endpoint:
- HTTP request/response flow
- Authentication requirements
- Error response formats
- Rate limiting (if applicable)

### 7. Update Chat Demo Authentication
**File:** `services/demos/chat.py`
**Dependency:** Tasks 1-6
**Status:** pending

Modify the authentication flow to:
- Call the new `/users/resolve-email` endpoint
- Handle the response to get external_auth_id
- Remove the problematic email-to-ID transformation code
- Update all subsequent API calls to use the resolved ID

**Key changes:**
- Replace `user_id = f"user_{auth_email.replace('@', '_').replace('.', '_')}"` 
- Add HTTP call to user service
- Handle resolution failures gracefully

### 8. Add Error Handling to Chat Demo
**File:** `services/demos/chat.py`
**Dependency:** Task 7
**Status:** pending

Add proper error handling for:
- Network failures to user service
- User not found scenarios
- Invalid email formats
- Service unavailable scenarios

### 9. Update Chat Demo Documentation
**File:** `services/demos/README_chat.md`
**Dependency:** Task 8
**Status:** pending

Document the new authentication flow:
- Explain email resolution step
- Update setup instructions
- Add troubleshooting section
- Include example API calls

Update documentation with:
- New endpoint specification
- Example requests/responses
- Error codes and meanings
- Integration guidance for other services

---

## Success Criteria
- [ ] Email resolution endpoint works for all provider types
- [ ] Chat demo successfully authenticates using email resolution
- [ ] All tests pass (unit + integration)
- [ ] No frontend email normalization required
- [ ] System handles email format variations correctly
- [ ] Error cases are properly handled and documented

## Testing Validation
Run these commands to validate implementation:
```bash
# Test the user service
cd services/user && python -m pytest tests/test_email_resolution.py -v

# Test the chat demo integration
cd services/demos && python -m pytest tests/test_chat_demo_integration.py -v

# Manual test with chat demo
cd services/demos && python chat.py
```

## Notes for Junior Engineer
- Start with tasks 1-4 (core backend implementation)
- Test thoroughly before moving to integration (tasks 5-6)
- The chat demo changes (tasks 7-8) should be straightforward after backend is solid
- Ask for help if email normalization logic is unclear
- Focus on error handling - it's critical for user experience 