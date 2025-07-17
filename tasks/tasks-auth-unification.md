# Unified Authentication Design: NextAuth JWT + API Key

## Overview

This document proposes a unified authentication model for Briefly, covering:
- End-user authentication via NextAuth (JWT-based)
- Service-to-service and background job authentication (API key and/or service JWT)
- Consistent auth handling in frontend, gateway, backend, and async jobs (e.g., Celery)

The goal is to ensure secure, scalable, and maintainable authentication for both interactive user flows and automated backend jobs (e.g., sending reminder emails).

---

## 1. User Authentication Flow (Frontend → Gateway → Backend)

### 1.1. Login & Session
- Users authenticate via NextAuth (Google/Microsoft OAuth) in the frontend.
- NextAuth issues a JWT (signed with `NEXTAUTH_SECRET`) containing user ID, email, provider, etc.
- The JWT is stored in the session and made available to the frontend (via `session.accessToken`).

### 1.2. API Requests
- The frontend uses `gateway-client.ts` to make API calls to the gateway (Express or similar).
- `gateway-client.ts` attaches the NextAuth JWT as a Bearer token in the `Authorization` header.
- The gateway validates the JWT (using `NEXTAUTH_SECRET`), extracts user info, and forwards the request to the appropriate backend service.
- Backend services (FastAPI) validate the JWT, extract the user ID, and authorize the request.

### 1.3. Key Points
- JWTs are short-lived (e.g., 1 hour), rotated as needed.
- All user-facing API calls are authenticated via JWT.
- No API keys are exposed to end users.

---

## 2. Service-to-Service & Background Job Authentication

### 2.1. API Key Auth (Current Pattern)
- Internal services (e.g., Celery jobs, backend-to-backend calls) authenticate using API keys.
- API keys are passed in `X-API-Key` or `Authorization: Bearer ...` headers.
- Backend services validate API keys against a list of allowed values (from env/config).
- Permissions can be scoped per key (e.g., `send_emails`, `read_calendar`).

### 2.2. Service JWT Auth (Proposed/Future Option)
- For advanced scenarios, services may issue and accept JWTs for service-to-service auth (with a separate signing key).
- Service JWTs would include claims like `sub` (service name), `scope`, and short expiry.
- For now, API key auth is sufficient for background jobs.

### 2.3. Background Jobs (e.g., Celery)
- When a background job (e.g., send reminder email) needs to call a backend API:
  - It uses a service API key (not a user JWT) for authentication.
  - The API key is injected into the job environment/config.
  - The receiving service checks the key and grants access based on permissions.
- If user context is needed (e.g., send email on behalf of user), the job must look up the user and/or request a user token from the user service.

---

## 3. Required Changes by Codebase Area

### 3.1. Frontend
- Ensure `gateway-client.ts` always attaches the NextAuth JWT for user API calls.
- No API keys should be present in client-side code.
- NextAuth config should generate JWTs with required claims (sub, email, provider, exp, etc.).

### 3.2. Gateway
- Validate incoming JWTs using `NEXTAUTH_SECRET`.
- Extract user info and forward as needed (e.g., in headers or request context).
- Reject requests with missing/invalid JWTs.
- Optionally, support API key auth for internal service calls (not from users).

### 3.3. Backend Services (FastAPI)
- Accept and validate JWTs for user-facing endpoints.
- Accept and validate API keys for service-to-service and background job endpoints.
- Use FastAPI dependencies for unified auth handling (see `services/user/auth/nextauth.py` and `service_auth.py`).
- Ensure endpoints are protected appropriately (user JWT vs. service API key).

### 3.4. Background Jobs (Celery, etc.)
- Configure jobs to use service API keys for backend API calls.
- Never use user JWTs for background jobs unless acting on behalf of a user (in which case, obtain a user token via the user service's internal API).
- Store API keys securely (env vars, secret manager).

---

## 4. Implementation Task Breakdown (Properly Ordered by Dependencies)

**Rationale:**
- All user-facing endpoints should use JWT auth and extract the user from the token, not from URL/query params. Use `/me` or similar endpoints for user context (e.g., `/users/me/preferences`, `/me/integrations`).
- All service-to-service (internal) endpoints should be under `/internal`, require API key auth, and may take `user_id` as a path or query param. Never accept user JWTs on these endpoints.
- This ensures a clear, industry-standard security boundary and makes endpoint intent/auditing obvious.

### Phase 1: Foundation and Infrastructure (Must be done first)

#### 4.1. Gateway Updates (Foundation)
- [ ] **HIGH PRIORITY**: Update gateway to properly extract user from JWT and forward via `X-User-Id` header
- [ ] **HIGH PRIORITY**: Ensure gateway does not call `/internal` endpoints
- [ ] **HIGH PRIORITY**: Add proper error handling for missing/invalid JWTs
- [ ] **HIGH PRIORITY**: Add tests for JWT validation and user context forwarding
- [ ] **MEDIUM PRIORITY**: Add API key validation for `/internal` routes (future enhancement)

#### 4.2. User Service - Internal Endpoints (Foundation)
- [ ] **HIGH PRIORITY**: Add new `/internal/users/id` endpoint (API key only) alongside existing `/users/id`
- [ ] **HIGH PRIORITY**: Add new `/internal/users/` (POST) endpoint (API key only) alongside existing `/users/` (POST)
- [ ] **HIGH PRIORITY**: Ensure all `/internal` endpoints require API key auth (`Depends(get_current_service)`)
- [ ] **HIGH PRIORITY**: Ensure `/internal` endpoints never accept user JWTs
- [ ] **HIGH PRIORITY**: Add/verify tests for API key extraction and access control

### Phase 2: Backend Service Updates (Depends on Phase 1)

#### 4.3. Chat Service Updates (Depends on Gateway)
- [ ] **HIGH PRIORITY**: Add new endpoints that extract user from `X-User-Id` header (not query params)
- [ ] **HIGH PRIORITY**: Update `get_user_id_from_gateway()` function to use header only
- [ ] **HIGH PRIORITY**: Update all endpoint handlers to use gateway header
- [ ] **HIGH PRIORITY**: Add/verify tests for user extraction from headers
- [ ] **MEDIUM PRIORITY**: Add any missing `/internal` endpoints if needed for service-to-service calls

#### 4.4. Office Service Updates (Depends on Gateway)
- [ ] **HIGH PRIORITY**: Add new endpoints that extract user from `X-User-Id` header (not query params)
- [ ] **HIGH PRIORITY**: Update endpoint handlers to use gateway header
- [ ] **HIGH PRIORITY**: Add/verify tests for user extraction from headers
- [ ] **MEDIUM PRIORITY**: Add any missing `/internal` endpoints if needed for service-to-service calls

### Phase 3: Frontend Updates (Depends on Phase 2)

#### 4.5. Frontend API Client Updates (Depends on Backend)
- [ ] **HIGH PRIORITY**: Update all API client calls to use new endpoints (no user_id in query params)
- [ ] **HIGH PRIORITY**: Update office service calls to use new endpoints (no user_id in query params)
- [ ] **HIGH PRIORITY**: Ensure no API keys are present in client-side code
- [ ] **HIGH PRIORITY**: Add/verify tests for correct session/JWT usage
- [ ] **MEDIUM PRIORITY**: Update any hardcoded user ID references

### Phase 4: Background Jobs and Service-to-Service (Depends on Phase 1)

#### 4.6. Background Jobs (Celery, etc.) (Depends on Internal Endpoints)
- [ ] **HIGH PRIORITY**: Update all job code to use new `/internal` endpoints and API key auth
- [ ] **HIGH PRIORITY**: Never use user JWTs in background jobs unless explicitly acting on behalf of a user
- [ ] **HIGH PRIORITY**: Store API keys securely (env vars, secret manager)
- [ ] **HIGH PRIORITY**: Add/verify tests for background job authentication flows
- [ ] **MEDIUM PRIORITY**: Update any existing background job configurations

### Phase 5: Cleanup and Documentation (Depends on all previous phases)

#### 4.7. Remove Old Endpoints and Cleanup
- [ ] **HIGH PRIORITY**: Remove old `/users/id` endpoint (after frontend/BFF updated)
- [ ] **HIGH PRIORITY**: Remove old `/users/` (POST) endpoint (after frontend/BFF updated)
- [ ] **HIGH PRIORITY**: Remove old user-facing endpoints with user_id in URL (after frontend updated)
- [ ] **HIGH PRIORITY**: Clean up any deprecated auth dependencies
- [ ] **MEDIUM PRIORITY**: Update OpenAPI docs to clearly distinguish user vs. internal endpoints
- [ ] **MEDIUM PRIORITY**: Update API documentation to reflect new patterns
- [ ] **MEDIUM PRIORITY**: Add integration tests for complete auth flows
- [ ] **MEDIUM PRIORITY**: Update deployment documentation for new auth patterns

---

## 5. Detailed Endpoint Mapping and Migration Tasks

Below is a concrete mapping of current endpoints to their new standardized forms, with migration tasks for each. This ensures a smooth transition to the new /me and /internal patterns and robust, auditable authentication.

### User Service

#### User-Facing Endpoints (/me, JWT) - Already Correct

- **Current:** GET /users/me (JWT) ✅
- **Status:** Already correct - no changes needed

- **Current:** GET /users/{user_id} (JWT)
- **New:** GET /users/me (JWT)
- **Tasks:**
  - [ ] Add new GET /users/me endpoint that extracts user from JWT
  - [ ] Update frontend to use new endpoint
  - [ ] Remove old GET /users/{user_id} endpoint
  - [ ] Update tests, docs

- **Current:** PUT /users/{user_id} (JWT)
- **New:** PUT /users/me (JWT)
- **Tasks:**
  - [ ] Add new PUT /users/me endpoint that extracts user from JWT
  - [ ] Update frontend to use new endpoint
  - [ ] Remove old PUT /users/{user_id} endpoint
  - [ ] Update tests, docs

- **Current:** DELETE /users/{user_id} (JWT)
- **New:** DELETE /users/me (JWT)
- **Tasks:**
  - [ ] Add new DELETE /users/me endpoint that extracts user from JWT
  - [ ] Update frontend to use new endpoint
  - [ ] Remove old DELETE /users/{user_id} endpoint
  - [ ] Update tests, docs

- **Current:** GET /users/me/preferences (JWT) ✅
- **Status:** Already correct - no changes needed

- **Current:** PUT /users/{user_id}/preferences (JWT)
- **New:** PUT /users/me/preferences (JWT)
- **Tasks:**
  - [ ] Add new PUT /users/me/preferences endpoint that extracts user from JWT
  - [ ] Update frontend to use new endpoint
  - [ ] Remove old PUT /users/{user_id}/preferences endpoint
  - [ ] Update tests, docs

- **Current:** POST /users/{user_id}/preferences/reset (JWT)
- **New:** POST /users/me/preferences/reset (JWT)
- **Tasks:**
  - [ ] Add new POST /users/me/preferences/reset endpoint that extracts user from JWT
  - [ ] Update frontend to use new endpoint
  - [ ] Remove old POST /users/{user_id}/preferences/reset endpoint
  - [ ] Update tests, docs

- **Current:** GET /users/me/integrations (JWT) ✅
- **Status:** Already correct - no changes needed

- **Current:** POST /users/me/integrations/oauth/start (JWT) ✅
- **Status:** Already correct - no changes needed

- **Current:** POST /users/me/integrations/oauth/callback (JWT) ✅
- **Status:** Already correct - no changes needed

- **Current:** GET /users/me/integrations/{provider} (JWT) ✅
- **Status:** Already correct - no changes needed

- **Current:** DELETE /users/me/integrations/{provider} (JWT) ✅
- **Status:** Already correct - no changes needed

- **Current:** PUT /users/me/integrations/{provider}/refresh (JWT) ✅
- **Status:** Already correct - no changes needed

- **Current:** GET /users/me/integrations/{provider}/health (JWT) ✅
- **Status:** Already correct - no changes needed

#### Internal/Service Endpoints (/internal, API Key) - Needs Migration

- **Current:** GET /users/id (API Key)
- **New:** GET /internal/users/id (API Key)
- **Tasks:**
  - [ ] Add new GET /internal/users/id endpoint (API key only)
  - [ ] Update BFF/gateway to use new endpoint
  - [ ] Remove old GET /users/id endpoint
  - [ ] Update tests, docs

- **Current:** POST /users/ (API Key)
- **New:** POST /internal/users/ (API Key)
- **Tasks:**
  - [ ] Add new POST /internal/users/ endpoint (API key only)
  - [ ] Update BFF/gateway to use new endpoint
  - [ ] Remove old POST /users/ endpoint
  - [ ] Update tests, docs

- **Current:** POST /internal/tokens/get (API Key) ✅
- **Status:** Already correct - no changes needed

- **Current:** POST /internal/tokens/refresh (API Key) ✅
- **Status:** Already correct - no changes needed

- **Current:** GET /internal/users/{user_id}/status (API Key) ✅
- **Status:** Already correct - no changes needed

- **Current:** GET /internal/users/{user_id}/preferences (API Key) ✅
- **Status:** Already correct - no changes needed

- **Current:** GET /internal/users/{user_id}/integrations (API Key) ✅
- **Status:** Already correct - no changes needed

### Chat Service

#### User-Facing Endpoints (JWT, /me pattern via gateway) - Needs Updates

- **Current:** POST /chat (JWT via gateway header, but uses user_id query param)
- **New:** POST /chat (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new POST /chat endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old POST /chat endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** POST /chat/stream (JWT via gateway header, but uses user_id query param)
- **New:** POST /chat/stream (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new POST /chat/stream endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old POST /chat/stream endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** GET /threads (JWT via gateway header, but uses user_id query param)
- **New:** GET /threads (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new GET /threads endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old GET /threads endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** GET /threads/{thread_id}/history (JWT via gateway header)
- **New:** GET /threads/{thread_id}/history (JWT via gateway header)
- **Tasks:**
  - [ ] Confirm user is extracted from JWT or gateway header, not from URL/query
  - [ ] Update tests, docs

- **Current:** POST /feedback (JWT via gateway header)
- **New:** POST /feedback (JWT via gateway header)
- **Tasks:**
  - [ ] Confirm user is extracted from JWT or gateway header, not from URL/query
  - [ ] Update tests, docs

- **Current:** POST /user-drafts (JWT via gateway header, but uses user_id query param)
- **New:** POST /user-drafts (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new POST /user-drafts endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old POST /user-drafts endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** GET /user-drafts (JWT via gateway header, but uses user_id query param)
- **New:** GET /user-drafts (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new GET /user-drafts endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old GET /user-drafts endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** GET /user-drafts/{draft_id} (JWT via gateway header)
- **New:** GET /user-drafts/{draft_id} (JWT via gateway header)
- **Tasks:**
  - [ ] Confirm user is extracted from JWT or gateway header, not from URL/query
  - [ ] Update tests, docs

- **Current:** PUT /user-drafts/{draft_id} (JWT via gateway header)
- **New:** PUT /user-drafts/{draft_id} (JWT via gateway header)
- **Tasks:**
  - [ ] Confirm user is extracted from JWT or gateway header, not from URL/query
  - [ ] Update tests, docs

- **Current:** DELETE /user-drafts/{draft_id} (JWT via gateway header)
- **New:** DELETE /user-drafts/{draft_id} (JWT via gateway header)
- **Tasks:**
  - [ ] Confirm user is extracted from JWT or gateway header, not from URL/query
  - [ ] Update tests, docs

#### Internal/Service Endpoints (API Key, /internal pattern)
- [ ] Audit for any internal endpoints; if present, move to /internal and require API key auth.

### Office Service

#### User-Facing Endpoints (JWT, /me pattern) - Needs Updates

- **Current:** GET /calendar/events (JWT via gateway header, but uses user_id query param)
- **New:** GET /calendar/events (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new GET /calendar/events endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old GET /calendar/events endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** POST /calendar/events (JWT via gateway header, but uses user_id query param)
- **New:** POST /calendar/events (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new POST /calendar/events endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old POST /calendar/events endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** GET /email/messages (JWT via gateway header, but uses user_id query param)
- **New:** GET /email/messages (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new GET /email/messages endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old GET /email/messages endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** POST /email/send (JWT via gateway header, but uses user_id query param)
- **New:** POST /email/send (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new POST /email/send endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old POST /email/send endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** GET /files (JWT via gateway header, but uses user_id query param)
- **New:** GET /files (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new GET /files endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old GET /files endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** GET /files/search (JWT via gateway header, but uses user_id query param)
- **New:** GET /files/search (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new GET /files/search endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old GET /files/search endpoint with user_id query param
  - [ ] Update tests, docs

- **Current:** GET /files/{file_id} (JWT via gateway header, but uses user_id query param)
- **New:** GET /files/{file_id} (JWT via gateway header only)
- **Tasks:**
  - [ ] Add new GET /files/{file_id} endpoint that extracts user from X-User-Id header only
  - [ ] Update frontend to use new endpoint (no user_id in query)
  - [ ] Remove old GET /files/{file_id} endpoint with user_id query param
  - [ ] Update tests, docs

#### Internal/Service Endpoints (API Key, /internal pattern)
- [ ] Audit and move internal/service endpoints to /internal, require API key auth, update tests/docs.

---

## 6. References
- `frontend/lib/auth.ts`, `gateway-client.ts`
- `services/user/auth/nextauth.py`, `service_auth.py`
- `documentation/oauth-bff-integration-design.md`, `backend-architecture.md`, `user-management-service.md`
- Celery, FastAPI, and NextAuth docs 