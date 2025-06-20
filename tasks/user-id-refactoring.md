# User ID Refactoring Task List

## Overview
Simplified refactoring to use a single `user_id` throughout the system. No internal IDs - all APIs use external authentication provider IDs.

## New Plan Summary
- **Phase 1**: Use Clerk `user_id` (e.g., `user_2abc123def456`) everywhere
- **Phase 2**: Switch to NextAuth `user_id` (e.g., `google_108234567890123456789`) everywhere
- **No internal IDs**: All APIs and services use the external authentication provider ID
- **No data migration needed**: We're not deployed yet

## Naming Convention Standard
- `user_id: str` - External authentication provider ID (Clerk → NextAuth)
- **Always external ID**: No internal database primary keys exposed in APIs

---

## Phase 1: Standardize to Clerk user_id

### Task 1.1: Fix preferences_service.py Critical Bug
**Priority:** 🔥 CRITICAL  
**Estimated Time:** 1 hour  
**Dependencies:** None

**Description:**
Fix the broken `get_user_preferences()` function that takes `user_id: str` but queries `User.id == user_id` (integer field).

**Files to modify:**
- `services/user/services/preferences_service.py`

**Changes:**
1. Keep parameter as `user_id: str` (external Clerk ID)
2. Add user lookup: Get user by external auth ID first, then use internal ID for DB queries
3. Update all related functions in the same file to follow same pattern

**Acceptance Criteria:**
- [x] Function signature keeps `user_id: str` (external Clerk ID)
- [x] Database queries work correctly with internal ID lookup
- [x] All tests pass
- [x] Demo authentication works correctly

**✅ COMPLETED:** Fixed all three methods in PreferencesService and updated router to pass external auth ID directly. All 24 preference tests and 14 user endpoint tests pass.

**Testing:**
```bash
# Test the fix
cd services/demos && python chat.py --message "test preferences"
```

### Task 1.2: Audit all user_id parameters across codebase
**Priority:** 🔥 HIGH  
**Estimated Time:** 2 hours  
**Dependencies:** None

**Description:**
Find all places where `user_id` parameters are used and ensure they consistently expect external Clerk IDs.

**Search Commands:**
```bash
# Find all user_id parameters
grep -r "user_id:" services/ --include="*.py"
grep -r "user_id =" services/ --include="*.py"
grep -r "def.*user_id" services/ --include="*.py"
```

**Changes:**
1. Document current usage patterns
2. Identify any remaining int vs str inconsistencies
3. Create list of files that need updates

**Acceptance Criteria:**
- [ ] Complete audit of user_id usage
- [ ] List of files needing updates
- [ ] Documentation of current patterns

### Task 1.3: Update all services to use external user_id consistently
**Priority:** 🔥 HIGH  
**Estimated Time:** 4 hours  
**Dependencies:** Task 1.1, 1.2

**Description:**
Update all service files to consistently use external Clerk user_id and handle internal ID lookup internally.

**Files to modify (based on previous audit):**
- `services/user/services/user_service.py`
- `services/user/services/integration_service.py`
- `services/user/services/token_service.py`
- `services/user/services/audit_service.py`
- `services/user/services/webhook_service.py`

**Pattern to implement:**
```python
async def some_function(self, user_id: str):  # External Clerk ID
    # Internal lookup
    user = await self.get_user_by_external_auth_id(user_id)
    if not user:
        raise UserNotFoundError(f"User not found: {user_id}")
    
    # Use user.id for database operations
    return await self.db_query(user.id)
```

**Acceptance Criteria:**
- [ ] All services use `user_id: str` for external IDs
- [ ] Internal ID lookup handled consistently
- [ ] All database operations use correct internal IDs
- [ ] Error handling for missing users

### Task 1.4: Update all router endpoints
**Priority:** 🔥 HIGH  
**Estimated Time:** 3 hours  
**Dependencies:** Task 1.3

**Description:**
Update all API router endpoints to consistently use external user_id.

**Files to modify:**
- `services/user/routers/users.py`
- `services/user/routers/preferences.py`
- `services/user/routers/integrations.py`
- `services/user/routers/webhooks.py`

**Changes:**
1. Ensure all endpoints expect external Clerk user_id
2. Update path parameters and request bodies
3. Update OpenAPI documentation
4. Ensure service calls pass external user_id

**Acceptance Criteria:**
- [ ] All endpoints use external user_id consistently
- [ ] API documentation updated
- [ ] Service integration works correctly

### Task 1.5: Update chat service integration
**Priority:** 🔥 HIGH  
**Estimated Time:** 2 hours  
**Dependencies:** Task 1.4

**Description:**
Ensure chat service correctly handles external user_id when calling user service APIs.

**Files to modify:**
- `services/chat/service_client.py`
- `services/chat/auth.py`
- Any other chat service files that interact with user service

**Changes:**
1. Ensure chat service passes external Clerk user_id to user service
2. Update any user ID handling in chat service
3. Test integration between services

**Acceptance Criteria:**
- [ ] Chat service passes correct external user_id
- [ ] Integration tests pass
- [ ] Demo chat functionality works

### Task 1.6: Update office service integration
**Priority:** 🟡 MEDIUM  
**Estimated Time:** 2 hours  
**Dependencies:** Task 1.4

**Description:**
Ensure office service correctly handles external user_id.

**Files to modify:**
- `services/office/core/auth.py`
- Any office service files that handle user identification

**Changes:**
1. Ensure office service uses external Clerk user_id
2. Update any user ID handling
3. Test office service functionality

**Acceptance Criteria:**
- [ ] Office service uses correct external user_id
- [ ] Office service functionality works

---

## Phase 2: Switch from Clerk to NextAuth

### Task 2.1: Update frontend authentication
**Priority:** 🔥 HIGH  
**Estimated Time:** 4 hours  
**Dependencies:** Phase 1 complete

**Description:**
Replace Clerk authentication with NextAuth in the frontend.

**Files to modify:**
- Frontend authentication configuration
- Any frontend code that extracts user_id

**Changes:**
1. Remove Clerk dependencies
2. Implement NextAuth configuration
3. Update user_id extraction to use NextAuth sub field
4. Test authentication flow

**Acceptance Criteria:**
- [ ] NextAuth authentication working
- [ ] User ID extraction returns NextAuth format (e.g., `google_108234567890123456789`)
- [ ] Frontend can authenticate users

### Task 2.2: Update user service to handle NextAuth user_id format
**Priority:** 🔥 HIGH  
**Estimated Time:** 2 hours  
**Dependencies:** Task 2.1

**Description:**
Ensure user service can handle NextAuth user_id format and create users with new ID format.

**Files to modify:**
- `services/user/services/user_service.py`
- User creation/lookup logic

**Changes:**
1. Update user creation to handle NextAuth user_id format
2. Ensure existing user lookup still works
3. Test user creation with new ID format

**Acceptance Criteria:**
- [ ] User service handles NextAuth user_id format
- [ ] New users can be created with NextAuth IDs
- [ ] User lookup works correctly

### Task 2.3: Test end-to-end authentication flow
**Priority:** 🔥 HIGH  
**Estimated Time:** 2 hours  
**Dependencies:** Task 2.1, 2.2

**Description:**
Test complete authentication flow with NextAuth user_id.

**Testing:**
1. User logs in via NextAuth
2. Frontend extracts NextAuth user_id
3. API calls use NextAuth user_id
4. Backend services handle NextAuth user_id correctly
5. All functionality works as expected

**Acceptance Criteria:**
- [ ] Complete authentication flow works
- [ ] All services handle NextAuth user_id
- [ ] Demo applications work correctly
- [ ] No authentication errors

---

## Phase 3: Cleanup and Documentation

### Task 3.1: Remove any remaining Clerk references
**Priority:** 🟡 MEDIUM  
**Estimated Time:** 1 hour  
**Dependencies:** Phase 2 complete

**Description:**
Clean up any remaining Clerk references in code and documentation.

**Changes:**
1. Remove Clerk dependencies from package.json
2. Remove Clerk configuration files
3. Update documentation
4. Clean up environment variables

**Acceptance Criteria:**
- [ ] No Clerk dependencies remain
- [ ] Documentation updated
- [ ] Clean codebase

### Task 3.2: Update documentation
**Priority:** 🟡 MEDIUM  
**Estimated Time:** 2 hours  
**Dependencies:** Phase 2 complete

**Description:**
Update all documentation to reflect new NextAuth authentication system.

**Files to modify:**
- README files
- API documentation
- Architecture documentation

**Changes:**
1. Document NextAuth integration
2. Update API documentation with correct user_id format
3. Update setup instructions

**Acceptance Criteria:**
- [ ] Documentation reflects NextAuth system
- [ ] Setup instructions updated
- [ ] API documentation correct

---

## Key Benefits of This Approach

1. **Simplicity**: Single user_id concept throughout system
2. **No Breaking Changes**: Backend APIs remain the same between phases
3. **Clean Architecture**: External ID used consistently
4. **Easy Migration**: Just change the format of user_id being passed
5. **No Data Migration**: Since we're not deployed yet

## Testing Strategy

### Phase 1 Testing
- [ ] All existing demos work with Clerk user_id
- [ ] User service APIs work correctly
- [ ] Chat service integration works
- [ ] Office service integration works

### Phase 2 Testing  
- [ ] Frontend authentication with NextAuth works
- [ ] Backend receives NextAuth user_id correctly
- [ ] All services handle new user_id format
- [ ] End-to-end authentication flow works

## Risk Mitigation

1. **Gradual Implementation**: Phase 1 fixes current issues, Phase 2 switches auth provider
2. **Consistent Interface**: Backend APIs don't change between phases
3. **Thorough Testing**: Test each phase completely before moving to next
4. **Documentation**: Keep documentation updated throughout process 