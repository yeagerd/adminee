# Pagination Standardization

## Progress Summary

### ✅ Completed Backend Implementation
- **Common Service**: Core pagination components, token management, query builders, schemas
- **Shipments Service**: Complete cursor-based pagination implementation with tests
- **User Service**: Complete cursor-based pagination implementation with tests
- **Integration Testing**: All 61 backend pagination tests passing across services

### 🔄 Remaining Tasks
- **Documentation and Migration** (Tasks 8): API docs, OpenAPI/Swagger updates
- **Configuration and Security** (Tasks 9): Production config, security measures
- **Frontend Integration** (Tasks 12): Complete frontend pagination rewrite
- **Performance Optimization** (Tasks 10-11): Database and application optimizations

### 📊 Completion Status
- **Backend**: ~85% complete (core implementation + testing done)
- **Frontend**: 0% complete (not started)
- **Documentation**: 0% complete (not started)
- **Production Config**: 0% complete (not started)

---

## Shipments Service Cursor-Based Pagination Implementation

### Development Commands Reference

**Dependency Management:**
```bash
# Add itsdangerous to common service (shared dependency)
uv add itsdangerous --project services/common

# Add itsdangerous to shipments service
uv add itsdangerous --project services/shipments

# Add itsdangerous to user service
uv add itsdangerous --project services/user

# Sync all dependencies
uv sync --all-packages --all-extras --active

# Update dependencies
uv lock --upgrade
```

**Testing:**
```bash
# Run common pagination tests
uv run python -m pytest services/common/tests/test_pagination.py -v

# Run shipments pagination tests
uv run python -m pytest services/shipments/tests/test_pagination.py -v

# Run user pagination tests
uv run python -m pytest services/user/tests/test_pagination.py -v

# Run all shipments tests
uv run python -m pytest services/shipments/tests/ -v

# Run all user tests
uv run python -m pytest services/user/tests/ -v

# Run all project tests
nox -s test

# Quick test feedback
nox -s test_fast
```

**Development:**
```bash
# Start shipments service
uv run python -m uvicorn services.shipments.main:app --reload

# Start user service
uv run python -m uvicorn services.user.main:app --reload

# Start all services
./scripts/start-all-services.sh

# Run migrations
alembic -c services/shipments/alembic.ini upgrade head
alembic -c services/user/alembic.ini upgrade head
```

**Linting and Type Checking:**
```bash
# Format code
nox -s format

# Run linting
nox -s lint

# Type checking
nox -s typecheck
``` 

### Overview
The shipments service currently uses offset-based pagination with `page` and `per_page` parameters. This implementation will migrate to cursor-based pagination using the `itsdangerous` library for secure token generation.

### Why itsdangerous?
- **Lightweight**: Minimal dependencies, already used in Flask ecosystem
- **Secure**: Provides signed, tamper-proof tokens
- **Simple API**: Easy to use for encoding/decoding cursor data
- **URL-safe**: Tokens are safe for use in URLs and query parameters
- **Performance**: Fast encoding/decoding operations

### Implementation Tasks

#### 1. Dependencies and Setup
- [x] Add `itsdangerous` to `services/common/setup.py` dependencies (shared dependency)
- [x] Add `itsdangerous` to `services/shipments/pyproject.toml` dependencies
- [x] Add `itsdangerous` to `services/user/pyproject.toml` dependencies
- [x] Run `uv sync --all-packages --all-extras --active` to install new dependencies
- [x] Create `services/common/pagination/` directory structure
- [x] Create `services/shipments/utils/pagination.py` for shipments-specific pagination utilities
- [x] Add pagination configuration to `services/common/settings.py` (shared configuration)
- [x] Create `services/shipments/schemas/pagination.py` for shipments-specific pagination schemas

#### 2. Core Pagination Implementation

##### Common Components (services/common)
- [x] Create `services/common/pagination/__init__.py` for pagination module
- [x] Create `services/common/pagination/base.py` with base cursor pagination class:
  - [x] `BaseCursorPagination` abstract base class
  - [x] Common cursor data structure definition
  - [x] Base token encoding/decoding methods using itsdangerous
  - [x] Common validation and sanitization logic
  - [x] Shared error handling for cursor operations
- [x] Create `services/common/pagination/token_manager.py`:
  - [x] `TokenManager` class for secure token operations
  - [x] Token signing with itsdangerous
  - [x] Token validation and expiration handling
  - [x] Secret key management for pagination tokens
  - [x] Token rotation and security utilities
- [x] Create `services/common/pagination/query_builder.py`:
  - [x] `CursorQueryBuilder` base class for database queries
  - [x] Common cursor-based filtering logic
  - [x] Database-agnostic query patterns
  - [x] Shared pagination query optimization
- [x] Create `services/common/pagination/schemas.py`:
  - [x] Base pagination request/response schemas
  - [x] Common cursor data models
  - [x] Shared validation schemas
  - [x] Pagination configuration models
- [x] Add pagination configuration to `services/common/settings.py`:
  - [x] `PAGINATION_SECRET_KEY` setting
  - [x] `PAGINATION_TOKEN_EXPIRY` setting (default: 1 hour)
  - [x] `PAGINATION_MAX_PAGE_SIZE` setting (default: 100)
  - [x] `PAGINATION_DEFAULT_PAGE_SIZE` setting (default: 20)
- [x] Update `services/common/__init__.py` to export pagination utilities

##### Shipments Service Implementation
- [x] Create `services/shipments/utils/pagination.py` extending common base:
  - [x] `ShipmentsCursorPagination` class extending `BaseCursorPagination`
  - [x] Shipments-specific cursor data structure:
    - [x] `last_id`: UUID of last package in current page
    - [x] `last_updated`: ISO timestamp for consistent ordering
    - [x] `filters`: JSON string of active filters (carrier, status, etc.)
    - [x] `direction`: 'next' or 'prev'
    - [x] `limit`: Number of items per page
  - [x] Shipments-specific query building logic
  - [x] Package-specific cursor validation rules

#### 3. Schema Updates
- [x] **COMPLETELY REPLACE** `services/shipments/schemas/__init__.py` pagination schemas:
  - [x] **REMOVE** the old `Pagination` class entirely
  - [x] **REMOVE** all `page`, `per_page`, `total`, `total_pages` fields
  - [x] Create new `CursorPagination` class with only cursor fields:
    - [x] `next_cursor?: string`
    - [x] `prev_cursor?: string`
    - [x] `has_next: boolean`
    - [x] `has_prev: boolean`
    - [x] `limit: number`
- [x] Create new request schemas (no legacy fields):
  - [x] `PackageListRequest` with `cursor` and `limit` parameters only
  - [x] `PackageSearchRequest` with cursor-based pagination only
- [x] Update response schemas:
  - [x] `PackageListResponse` with cursor pagination metadata only
  - [x] **REMOVE** all legacy pagination fields from existing schemas

#### 4. Database Query Updates
- [x] **COMPLETELY REWRITE** `services/shipments/routers/packages.py` pagination logic:
  - [x] **REMOVE** all offset-based pagination code
  - [x] **REMOVE** all `page`, `page_size`, `offset` calculations
  - [x] **REMOVE** all legacy pagination response formatting
  - [x] Implement pure cursor-based pagination in `get_packages()` endpoint
  - [x] Use cursor-based filtering with `WHERE` clauses
  - [x] Add proper ordering (by `id` and `updated_at`)
  - [x] Implement bidirectional pagination support
- [x] Update database queries:
  - [x] **REMOVE** all offset-based query logic
  - [x] Implement cursor-based filtering logic only
  - [x] Add proper indexing for cursor fields
  - [x] Add query optimization for large datasets
  - [x] Handle edge cases (empty results, last page, etc.)

#### 5. API Endpoint Updates
- [x] **COMPLETELY REPLACE** query parameters in package endpoints:
  - [x] **REMOVE** `page` parameter entirely
  - [x] **REMOVE** `per_page` parameter entirely
  - [x] **REMOVE** all legacy pagination parameters
  - [x] Add only cursor-based parameters:
    - [x] `cursor?: string` (replaces page)
    - [x] `limit?: number` (replaces per_page)
    - [x] `direction?: 'next' | 'prev'` (for bidirectional pagination)
- [x] **COMPLETELY REPLACE** response format:
  - [x] **REMOVE** all legacy pagination fields from responses
  - [x] Include only cursor-based pagination:
    - [x] `next_cursor?: string`
    - [x] `prev_cursor?: string`
    - [x] `has_next: boolean`
    - [x] `has_prev: boolean`
    - [x] `limit: number`
- [x] Update error handling:
  - [x] **REMOVE** all legacy pagination error handling
  - [x] Add cursor validation errors
  - [x] Handle expired or invalid tokens
  - [x] Add proper HTTP status codes for pagination errors

#### 6. Filtering and Search Integration
- [x] Update search functionality to work with cursors:
  - [x] Encode filter parameters in cursor tokens
  - [x] Maintain filter state across pagination
  - [x] Handle dynamic filter changes
- [x] Update carrier and status filtering:
  - [x] Include filter state in cursor data
  - [x] Ensure consistent results across pages
  - [x] Handle filter combinations properly

#### 7. Testing Implementation

##### Common Components Testing
- [x] Create `services/common/tests/test_common_pagination.py`
  - [x] Test `BaseCursorPagination` functionality
  - [x] Test `TokenManager` token operations
  - [x] Test `CursorQueryBuilder` query patterns
  - [x] Test base pagination schemas and validation
  - [x] Test common pagination configuration
- [x] Run common tests:
  - [x] `uv run python -m pytest services/common/tests/test_common_pagination.py -v`
  - [x] `uv run python -m pytest services/common/tests/ -v` (all common tests)

##### Shipments Service Testing
- [x] Create `services/shipments/tests/test_shipments_pagination.py`
  - [x] Test `ShipmentsCursorPagination` extending base functionality
  - [x] Test shipments-specific cursor encoding/decoding
  - [x] Test pagination with various filter combinations
  - [x] Test edge cases (empty results, single page, etc.)
  - [x] Test backward pagination
  - [x] Test cursor expiration and validation
- [x] Update existing tests:
  - [x] Modify `test_endpoints.py` to use cursor pagination
  - [x] Update test assertions for new response format
  - [x] Add integration tests for pagination scenarios

##### Test Execution
- [x] Run tests using UV:
  - [x] `uv run python -m pytest services/common/tests/test_common_pagination.py -v`
  - [x] `uv run python -m pytest services/shipments/tests/test_shipments_pagination.py -v`
  - [x] `uv run python -m pytest services/shipments/tests/ -v` (all shipments tests)
  - [x] `nox -s test` (all project tests)

#### 8. Documentation and Migration
- [ ] **REWRITE** API documentation:
  - [ ] **REMOVE** all documentation about legacy pagination
  - [ ] Document only cursor-based pagination parameters
  - [ ] Provide examples of cursor usage
  - [ ] **REMOVE** any migration guides - this is a breaking change
- [ ] **NO MIGRATION SCRIPT NEEDED** - this is a breaking change:
  - [ ] **REMOVE** all legacy pagination support
  - [ ] **REMOVE** all deprecation warnings
  - [ ] API consumers must update to new cursor-based pagination
- [ ] **COMPLETELY UPDATE** OpenAPI/Swagger documentation:
  - [ ] **REMOVE** all legacy pagination schemas
  - [ ] Update endpoint schemas to cursor-based only
  - [ ] Add cursor parameter examples
  - [ ] **REMOVE** all legacy response format documentation

#### 9. Configuration and Security
- [ ] Add pagination configuration:
  - [ ] Secret key for token signing
  - [ ] Token expiration time (default: 1 hour)
  - [ ] Maximum page size limits
  - [ ] Rate limiting for pagination requests
- [ ] Implement security measures:
  - [ ] Token rotation and expiration
  - [ ] Rate limiting for cursor generation
  - [ ] Audit logging for pagination usage
  - [ ] Input validation and sanitization



#### 12. Frontend Integration Updates

##### Type Definitions and Interfaces
- [ ] **COMPLETELY REPLACE** `frontend/lib/shipments-client.ts` pagination interfaces:
  - [ ] **REMOVE** the old `PaginationInfo` interface entirely
  - [ ] **REMOVE** all `page`, `per_page`, `total_pages` fields
  - [ ] Create new `CursorPaginationInfo` interface:
    ```typescript
    export interface CursorPaginationInfo {
        next_cursor?: string;
        prev_cursor?: string;
        has_next: boolean;
        has_prev: boolean;
        limit: number;
        // NO legacy fields: page, per_page, total, total_pages
    }
    ```
  - [ ] **COMPLETELY REPLACE** `getPackages()` method signature:
    ```typescript
    async getPackages(params?: {
        tracking_number?: string;
        carrier?: string;
        cursor?: string;
        limit?: number;
        direction?: 'next' | 'prev';
    }): Promise<{ data: PackageResponse[]; pagination: CursorPaginationInfo }>
    ```
  - [ ] **REMOVE** all legacy pagination helper methods
  - [ ] Add cursor-based pagination helper methods:
    - [ ] `getNextPage(cursor: string, limit?: number)`
    - [ ] `getPrevPage(cursor: string, limit?: number)`
    - [ ] `getFirstPage(limit?: number)`

##### Gateway Client Updates
- [ ] **COMPLETELY REWRITE** `frontend/lib/gateway-client.ts` pagination logic:
  - [ ] **REMOVE** all legacy pagination code from `getPackages()` method (lines 502-540)
  - [ ] **REMOVE** all `page`, `per_page`, `total`, `total_pages` handling
  - [ ] **REMOVE** all offset-based pagination logic
  - [ ] Implement pure cursor-based pagination:
    - [ ] Add `cursor`, `limit`, `direction` parameter handling
    - [ ] Update response type to match new cursor pagination structure
    - [ ] Add cursor parameter validation and sanitization
    - [ ] Update error handling for invalid cursor tokens

##### Package Dashboard Component Updates
- [ ] **COMPLETELY REWRITE** `frontend/components/packages/PackageDashboard.tsx` pagination logic:
  - [ ] **REMOVE** all legacy pagination state management
  - [ ] **REMOVE** all `page`, `page_size`, `total` state variables
  - [ ] **REMOVE** all offset-based pagination logic
  - [ ] Add cursor state management:
    ```typescript
    const [currentCursor, setCurrentCursor] = useState<string | null>(null);
    const [nextCursor, setNextCursor] = useState<string | null>(null);
    const [prevCursor, setPrevCursor] = useState<string | null>(null);
    const [hasNext, setHasNext] = useState(false);
    const [hasPrev, setHasPrev] = useState(false);
    ```
  - [ ] **COMPLETELY REWRITE** `useEffect` for initial data loading to use cursor pagination
  - [ ] **COMPLETELY REWRITE** `refreshPackages()` function to handle cursor-based responses
  - [ ] **REMOVE** all legacy pagination navigation functions
  - [ ] Add cursor-based pagination navigation functions:
    - [ ] `loadNextPage()`
    - [ ] `loadPrevPage()`
    - [ ] `loadFirstPage()`
  - [ ] Update package filtering to work with cursor pagination
  - [ ] Add loading states for pagination operations
  - [ ] Update error handling for pagination failures

##### Package List Component Updates
- [ ] Update `frontend/components/packages/PackageList.tsx`
  - [ ] Add pagination controls component
  - [ ] Integrate with existing filter system
  - [ ] Add pagination state props:
    ```typescript
    pagination: {
        hasNext: boolean;
        hasPrev: boolean;
        nextCursor?: string;
        prevCursor?: string;
        total: number;
    }
    ```
  - [ ] Add pagination event handlers:
    - [ ] `onNextPage: () => void`
    - [ ] `onPrevPage: () => void`
    - [ ] `onFirstPage: () => void`
  - [ ] Update table to show pagination status
  - [ ] Add loading indicators for pagination operations

##### Pagination UI Components
- [ ] Create `frontend/components/packages/PackagePagination.tsx`
  - [ ] Build cursor-based pagination controls
  - [ ] Include next/previous buttons
  - [ ] Add page information display (e.g., "Showing 1-20 of 100 packages")
  - [ ] Add loading states and disabled states
  - [ ] Handle edge cases (first page, last page, no results)

##### Filter Integration
- [ ] Update filter system to work with cursor pagination:
  - [ ] Modify `frontend/components/packages/PackageDashboard.tsx` filter logic
  - [ ] Ensure filters reset pagination state when changed
  - [ ] Update search functionality to work with cursors
  - [ ] Handle filter combinations in cursor tokens
  - [ ] Add filter state persistence across pagination

##### URL State Management
- [ ] Add URL state management for pagination:
  - [ ] Update URL parameters to include cursor state
  - [ ] Handle browser back/forward navigation
  - [ ] Add URL state synchronization with component state
  - [ ] Implement deep linking for specific pages
  - [ ] Add URL parameter validation and sanitization

##### Error Handling and User Experience
- [ ] Add comprehensive error handling:
  - [ ] Handle expired cursor tokens
  - [ ] Handle invalid cursor tokens
  - [ ] Add retry mechanisms for failed pagination requests
  - [ ] Show user-friendly error messages
  - [ ] Add fallback to first page on errors
- [ ] Improve user experience:
  - [ ] Add smooth transitions between pages
  - [ ] Implement optimistic updates where possible
  - [ ] Add loading skeletons for better perceived performance
  - [ ] Maintain scroll position or scroll to top on page change

##### Testing Frontend Changes
- [ ] **COMPLETELY REWRITE** existing pagination tests:
  - [ ] **REMOVE** all legacy pagination tests from existing test files
  - [ ] **REMOVE** all tests for `page`, `per_page`, `total` functionality
  - [ ] Create `frontend/components/packages/__tests__/PackagePagination.test.tsx`
    - [ ] Test cursor pagination component rendering
    - [ ] Test cursor pagination button interactions
    - [ ] Test edge cases (first/last page, no results)
- [ ] **COMPLETELY REWRITE** existing component tests:
  - [ ] **REMOVE** all legacy pagination tests from `PackageDashboard.test.tsx`
  - [ ] **REMOVE** all legacy pagination tests from `PackageList.test.tsx`
  - [ ] Add cursor pagination tests to existing test files
  - [ ] Add integration tests for cursor pagination flows
- [ ] Add E2E tests:
  - [ ] Test complete cursor pagination user flows
  - [ ] Test cursor pagination with filters
  - [ ] Test cursor pagination error scenarios

##### Performance Optimizations
- [ ] Implement frontend performance improvements:
  - [ ] Add cursor caching in localStorage/sessionStorage
  - [ ] Implement virtual scrolling for large lists (if needed)
  - [ ] Add request debouncing for rapid pagination clicks
  - [ ] Optimize re-renders with React.memo and useMemo
  - [ ] Add prefetching for next page data
- [ ] **REMOVE** all legacy pagination performance optimizations:
  - [ ] **REMOVE** any offset-based pagination caching
  - [ ] **REMOVE** any legacy pagination state management
  - [ ] **REMOVE** any legacy pagination performance monitoring

#### 13. Integration Testing
- [x] End-to-end testing:
  - [x] Test complete pagination flows
  - [x] Test integration with frontend components
  - [x] Test performance under load
- [x] Cross-service testing:
  - [x] Test pagination with other services
  - [x] Verify API gateway compatibility
  - [x] Test authentication and authorization
- [x] Development environment testing:
  - [x] Test with `./scripts/start-all-services.sh` (full stack)
  - [x] Test individual service with `uv run python -m uvicorn services.shipments.main:app --reload`
  - [x] Test database migrations with `alembic -c services/shipments/alembic.ini upgrade head`

### Expected Benefits
- **Performance**: Faster queries for large datasets
- **Consistency**: More reliable pagination results
- **Scalability**: Better handling of concurrent updates
- **Security**: Tamper-proof pagination tokens
- **User Experience**: More responsive pagination controls

### Migration Timeline
- **Phase 1**: **COMPLETELY REPLACE** backend pagination with cursor-based system
- **Phase 2**: **COMPLETELY REPLACE** frontend pagination with cursor-based system
- **Phase 3**: **REMOVE** all legacy pagination code and tests
- **Phase 4**: **VERIFY** no legacy pagination code remains in codebase

**Note**: This is a breaking change. No backward compatibility will be maintained. All API consumers must update to use cursor-based pagination.

## User Service Cursor-Based Pagination Implementation

### Overview
The user service currently uses offset-based pagination with `page` and `page_size` parameters in the `/users/search` endpoint. This implementation will migrate to cursor-based pagination using the shared common pagination utilities.

### Current User Service Pagination
- **Endpoint**: `/users/search` (lines 394-430 in `services/user/routers/users.py`)
- **Current Parameters**: `page`, `page_size`, `query`, `email`, `onboarding_completed`
- **Current Response**: `UserListResponse` with `page`, `page_size`, `total`, `has_next`, `has_previous`
- **Current Implementation**: Offset-based pagination in `search_users()` method (lines 528-628 in `services/user/services/user_service.py`)

### Implementation Tasks

#### 1. User Service Dependencies and Setup
- [x] Add `itsdangerous` to `services/user/pyproject.toml` dependencies
- [x] Run `uv sync --all-packages --all-extras --active` to install new dependency
- [x] Create `services/user/utils/pagination.py` for user-specific pagination utilities
- [ ] Add user-specific pagination configuration to `services/user/settings.py`

#### 2. User Service Core Pagination Implementation
- [x] Create `services/user/utils/pagination.py` extending common base:
  - [x] `UserCursorPagination` class extending `BaseCursorPagination`
  - [x] User-specific cursor data structure:
    - [x] `last_id`: Integer ID of last user in current page
    - [x] `last_created_at`: ISO timestamp for consistent ordering
    - [x] `filters`: JSON string of active filters (query, email, onboarding_completed)
    - [x] `direction`: 'next' or 'prev'
    - [x] `limit`: Number of items per page
  - [x] User-specific query building logic
  - [x] User-specific cursor validation rules

#### 3. User Service Schema Updates
- [x] **COMPLETELY REPLACE** `services/user/schemas/user.py` pagination schemas:
  - [x] **REMOVE** the old `UserListResponse` class entirely (lines 238-246)
  - [x] **REMOVE** all `page`, `page_size`, `total` fields
  - [x] Create new `UserCursorListResponse` class with only cursor fields:
    - [x] `users: list[UserResponse]`
    - [x] `next_cursor?: string`
    - [x] `prev_cursor?: string`
    - [x] `has_next: boolean`
    - [x] `has_prev: boolean`
    - [x] `limit: number`
- [x] **COMPLETELY REPLACE** `UserSearchRequest` class (lines 325-326):
  - [x] **REMOVE** `page` and `page_size` fields
  - [x] Add cursor-based parameters:
    - [x] `cursor?: string`
    - [x] `limit?: number`
    - [x] `direction?: 'next' | 'prev'`
    - [x] Keep existing filter fields: `query`, `email`, `onboarding_completed`

#### 4. User Service Database Query Updates
- [x] **COMPLETELY REWRITE** `services/user/services/user_service.py` pagination logic:
  - [x] **REMOVE** all offset-based pagination code from `search_users()` method (lines 528-628)
  - [x] **REMOVE** all `page`, `page_size`, `offset` calculations
  - [x] **REMOVE** all legacy pagination response formatting
  - [x] Implement pure cursor-based pagination in `search_users()` method
  - [x] Use cursor-based filtering with `WHERE` clauses
  - [x] Add proper ordering (by `id` and `created_at`)
  - [x] Implement bidirectional pagination support
- [x] Update database queries:
  - [x] **REMOVE** all offset-based query logic
  - [x] Implement cursor-based filtering logic only
  - [x] Add proper indexing for cursor fields (`id`, `created_at`)
  - [x] Add query optimization for large datasets
  - [x] Handle edge cases (empty results, last page, etc.)

#### 5. User Service API Endpoint Updates
- [x] **COMPLETELY REPLACE** query parameters in `/users/search` endpoint:
  - [x] **REMOVE** `page` parameter entirely
  - [x] **REMOVE** `page_size` parameter entirely
  - [x] **REMOVE** all legacy pagination parameters
  - [x] Add only cursor-based parameters:
    - [x] `cursor?: string` (replaces page)
    - [x] `limit?: number` (replaces page_size)
    - [x] `direction?: 'next' | 'prev'` (for bidirectional pagination)
    - [x] Keep existing filter parameters: `query`, `email`, `onboarding_completed`
- [x] **COMPLETELY REPLACE** response format:
  - [x] **REMOVE** all legacy pagination fields from responses
  - [x] Include only cursor-based pagination:
    - [x] `next_cursor?: string`
    - [x] `prev_cursor?: string`
    - [x] `has_next: boolean`
    - [x] `has_prev: boolean`
    - [x] `limit: number`
- [x] Update error handling:
  - [x] **REMOVE** all legacy pagination error handling
  - [x] Add cursor validation errors
  - [x] Handle expired or invalid tokens
  - [x] Add proper HTTP status codes for pagination errors

#### 6. User Service Filtering and Search Integration
- [x] Update search functionality to work with cursors:
  - [x] Encode filter parameters in cursor tokens
  - [x] Maintain filter state across pagination
  - [x] Handle dynamic filter changes
- [x] Update user filtering:
  - [x] Include filter state in cursor data
  - [x] Ensure consistent results across pages
  - [x] Handle filter combinations properly

#### 7. User Service Testing Implementation

##### Common Components Testing
- [ ] Ensure common pagination tests pass:
  - [ ] `uv run python -m pytest services/common/tests/test_pagination.py -v`

##### User Service Testing
- [x] Create `services/user/tests/test_user_pagination.py`
  - [x] Test `UserCursorPagination` extending base functionality
  - [x] Test user-specific cursor encoding/decoding
  - [x] Test pagination with various filter combinations
  - [x] Test edge cases (empty results, single page, etc.)
  - [x] Test backward pagination
  - [x] Test cursor expiration and validation
- [x] Update existing tests:
  - [x] **REMOVE** all legacy pagination tests from existing test files
  - [x] **REMOVE** all tests for `page`, `page_size`, `total` functionality
  - [x] Add cursor pagination tests to existing test files
  - [x] Add integration tests for cursor pagination flows

##### Test Execution
- [x] Run tests using UV:
  - [x] `uv run python -m pytest services/user/tests/test_user_pagination.py -v`
  - [x] `uv run python -m pytest services/user/tests/ -v` (all user tests)
  - [x] `nox -s test` (all project tests)

#### 8. User Service Documentation and Migration
- [ ] **COMPLETELY REWRITE** API documentation:
  - [ ] **REMOVE** all documentation about legacy pagination
  - [ ] Document only cursor-based pagination parameters
  - [ ] Provide examples of cursor usage
  - [ ] **REMOVE** any migration guides - this is a breaking change
- [ ] **NO MIGRATION SCRIPT NEEDED** - this is a breaking change:
  - [ ] **REMOVE** all legacy pagination support
  - [ ] **REMOVE** all deprecation warnings
  - [ ] API consumers must update to new cursor-based pagination
- [ ] **COMPLETELY UPDATE** OpenAPI/Swagger documentation:
  - [ ] **REMOVE** all legacy pagination schemas
  - [ ] Update endpoint schemas to cursor-based only
  - [ ] Add cursor parameter examples
  - [ ] **REMOVE** all legacy response format documentation

#### 9. User Service Configuration and Security
- [ ] Add user service pagination configuration:
  - [ ] Use shared secret key from common settings
  - [ ] Use shared token expiration time
  - [ ] Use shared maximum page size limits
  - [ ] Add rate limiting for pagination requests
- [ ] Implement security measures:
  - [ ] Token rotation and expiration
  - [ ] Rate limiting for cursor generation
  - [ ] Audit logging for pagination usage
  - [ ] Input validation and sanitization

#### 10. User Service Performance Optimization
- [ ] Database optimization:
  - [ ] Add composite indexes for cursor fields (`id`, `created_at`)
  - [ ] Optimize queries for cursor-based filtering
  - [ ] Add query result caching where appropriate
- [ ] Application optimization:
  - [ ] Implement cursor caching
  - [ ] Optimize token generation/validation
  - [ ] Add connection pooling for database queries
- [ ] Development workflow optimization:
  - [ ] Use `uv run python -m uvicorn services.user.main:app --reload` for development
  - [ ] Use `./scripts/start-all-services.sh` for full integration testing
  - [ ] Use `nox -s test_fast` for quick test feedback during development

#### 11. User Service Frontend Integration (if applicable)
- [ ] **Note**: User service is primarily backend-only, but if frontend components exist:
  - [ ] **COMPLETELY REPLACE** any frontend pagination interfaces
  - [ ] **REMOVE** all legacy pagination state management
  - [ ] **REMOVE** all `page`, `page_size`, `total` state variables
  - [ ] Add cursor state management
  - [ ] **COMPLETELY REWRITE** data loading functions
  - [ ] Add cursor-based pagination navigation functions
  - [ ] Update any user search components to use cursor pagination

#### 12. User Service Integration Testing
- [x] End-to-end testing:
  - [x] Test complete cursor pagination flows
  - [x] Test integration with other services
  - [x] Test performance under load
- [x] Cross-service testing:
  - [x] Test pagination with other services
  - [x] Verify API gateway compatibility
  - [x] Test authentication and authorization
- [x] Development environment testing:
  - [x] Test with `./scripts/start-all-services.sh` (full stack)
  - [x] Test individual service with `uv run python -m uvicorn services.user.main:app --reload`
  - [x] Test database migrations with `alembic -c services/user/alembic.ini upgrade head`

### User Service Migration Timeline
- **Phase 1**: **COMPLETELY REPLACE** user service pagination with cursor-based system
- **Phase 2**: **REMOVE** all legacy pagination code and tests
- **Phase 3**: **VERIFY** no legacy pagination code remains in user service
- **Phase 4**: **TEST** integration with other services using cursor pagination

**Note**: This is a breaking change. No backward compatibility will be maintained. All API consumers must update to use cursor-based pagination.
