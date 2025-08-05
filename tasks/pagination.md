# Pagination Standardization

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
- [ ] Add `itsdangerous` to `services/common/pyproject.toml` dependencies (shared dependency)
- [ ] Add `itsdangerous` to `services/shipments/pyproject.toml` dependencies
- [ ] Run `uv sync --all-packages --all-extras --active` to install new dependencies
- [ ] Create `services/common/pagination/` directory structure
- [ ] Create `services/shipments/utils/pagination.py` for shipments-specific pagination utilities
- [ ] Add pagination configuration to `services/common/settings.py` (shared configuration)
- [ ] Create `services/shipments/schemas/pagination.py` for shipments-specific pagination schemas

#### 2. Core Pagination Implementation

##### Common Components (services/common)
- [ ] Create `services/common/pagination/__init__.py` for pagination module
- [ ] Create `services/common/pagination/base.py` with base cursor pagination class:
  - [ ] `BaseCursorPagination` abstract base class
  - [ ] Common cursor data structure definition
  - [ ] Base token encoding/decoding methods using itsdangerous
  - [ ] Common validation and sanitization logic
  - [ ] Shared error handling for cursor operations
- [ ] Create `services/common/pagination/token_manager.py`:
  - [ ] `TokenManager` class for secure token operations
  - [ ] Token signing with itsdangerous
  - [ ] Token validation and expiration handling
  - [ ] Secret key management for pagination tokens
  - [ ] Token rotation and security utilities
- [ ] Create `services/common/pagination/query_builder.py`:
  - [ ] `CursorQueryBuilder` base class for database queries
  - [ ] Common cursor-based filtering logic
  - [ ] Database-agnostic query patterns
  - [ ] Shared pagination query optimization
- [ ] Create `services/common/pagination/schemas.py`:
  - [ ] Base pagination request/response schemas
  - [ ] Common cursor data models
  - [ ] Shared validation schemas
  - [ ] Pagination configuration models
- [ ] Add pagination configuration to `services/common/settings.py`:
  - [ ] `PAGINATION_SECRET_KEY` setting
  - [ ] `PAGINATION_TOKEN_EXPIRY` setting (default: 1 hour)
  - [ ] `PAGINATION_MAX_PAGE_SIZE` setting (default: 100)
  - [ ] `PAGINATION_DEFAULT_PAGE_SIZE` setting (default: 20)
- [ ] Update `services/common/__init__.py` to export pagination utilities

##### Shipments Service Implementation
- [ ] Create `services/shipments/utils/pagination.py` extending common base:
  - [ ] `ShipmentsCursorPagination` class extending `BaseCursorPagination`
  - [ ] Shipments-specific cursor data structure:
    - [ ] `last_id`: UUID of last package in current page
    - [ ] `last_updated`: ISO timestamp for consistent ordering
    - [ ] `filters`: JSON string of active filters (carrier, status, etc.)
    - [ ] `direction`: 'next' or 'prev'
    - [ ] `limit`: Number of items per page
  - [ ] Shipments-specific query building logic
  - [ ] Package-specific cursor validation rules

#### 3. Schema Updates
- [ ] **COMPLETELY REPLACE** `services/shipments/schemas/__init__.py` pagination schemas:
  - [ ] **REMOVE** the old `Pagination` class entirely
  - [ ] **REMOVE** all `page`, `per_page`, `total`, `total_pages` fields
  - [ ] Create new `CursorPagination` class with only cursor fields:
    - [ ] `next_cursor?: string`
    - [ ] `prev_cursor?: string`
    - [ ] `has_next: boolean`
    - [ ] `has_prev: boolean`
    - [ ] `limit: number`
- [ ] Create new request schemas (no legacy fields):
  - [ ] `PackageListRequest` with `cursor` and `limit` parameters only
  - [ ] `PackageSearchRequest` with cursor-based pagination only
- [ ] Update response schemas:
  - [ ] `PackageListResponse` with cursor pagination metadata only
  - [ ] **REMOVE** all legacy pagination fields from existing schemas

#### 4. Database Query Updates
- [ ] **COMPLETELY REWRITE** `services/shipments/routers/packages.py` pagination logic:
  - [ ] **REMOVE** all offset-based pagination code
  - [ ] **REMOVE** all `page`, `page_size`, `offset` calculations
  - [ ] **REMOVE** all legacy pagination response formatting
  - [ ] Implement pure cursor-based pagination in `get_packages()` endpoint
  - [ ] Use cursor-based filtering with `WHERE` clauses
  - [ ] Add proper ordering (by `id` and `updated_at`)
  - [ ] Implement bidirectional pagination support
- [ ] Update database queries:
  - [ ] **REMOVE** all offset-based query logic
  - [ ] Implement cursor-based filtering logic only
  - [ ] Add proper indexing for cursor fields
  - [ ] Add query optimization for large datasets
  - [ ] Handle edge cases (empty results, last page, etc.)

#### 5. API Endpoint Updates
- [ ] **COMPLETELY REPLACE** query parameters in package endpoints:
  - [ ] **REMOVE** `page` parameter entirely
  - [ ] **REMOVE** `per_page` parameter entirely
  - [ ] **REMOVE** all legacy pagination parameters
  - [ ] Add only cursor-based parameters:
    - [ ] `cursor?: string` (replaces page)
    - [ ] `limit?: number` (replaces per_page)
    - [ ] `direction?: 'next' | 'prev'` (for bidirectional pagination)
- [ ] **COMPLETELY REPLACE** response format:
  - [ ] **REMOVE** all legacy pagination fields from responses
  - [ ] Include only cursor-based pagination:
    - [ ] `next_cursor?: string`
    - [ ] `prev_cursor?: string`
    - [ ] `has_next: boolean`
    - [ ] `has_prev: boolean`
    - [ ] `limit: number`
- [ ] Update error handling:
  - [ ] **REMOVE** all legacy pagination error handling
  - [ ] Add cursor validation errors
  - [ ] Handle expired or invalid tokens
  - [ ] Add proper HTTP status codes for pagination errors

#### 6. Filtering and Search Integration
- [ ] Update search functionality to work with cursors:
  - [ ] Encode filter parameters in cursor tokens
  - [ ] Maintain filter state across pagination
  - [ ] Handle dynamic filter changes
- [ ] Update carrier and status filtering:
  - [ ] Include filter state in cursor data
  - [ ] Ensure consistent results across pages
  - [ ] Handle filter combinations properly

#### 7. Testing Implementation

##### Common Components Testing
- [ ] Create `services/common/tests/test_pagination.py`
  - [ ] Test `BaseCursorPagination` functionality
  - [ ] Test `TokenManager` token operations
  - [ ] Test `CursorQueryBuilder` query patterns
  - [ ] Test base pagination schemas and validation
  - [ ] Test common pagination configuration
- [ ] Run common tests:
  - [ ] `uv run python -m pytest services/common/tests/test_pagination.py -v`
  - [ ] `uv run python -m pytest services/common/tests/ -v` (all common tests)

##### Shipments Service Testing
- [ ] Create `services/shipments/tests/test_pagination.py`
  - [ ] Test `ShipmentsCursorPagination` extending base functionality
  - [ ] Test shipments-specific cursor encoding/decoding
  - [ ] Test pagination with various filter combinations
  - [ ] Test edge cases (empty results, single page, etc.)
  - [ ] Test backward pagination
  - [ ] Test cursor expiration and validation
- [ ] Update existing tests:
  - [ ] Modify `test_endpoints.py` to use cursor pagination
  - [ ] Update test assertions for new response format
  - [ ] Add integration tests for pagination scenarios

##### Test Execution
- [ ] Run tests using UV:
  - [ ] `uv run python -m pytest services/common/tests/test_pagination.py -v`
  - [ ] `uv run python -m pytest services/shipments/tests/test_pagination.py -v`
  - [ ] `uv run python -m pytest services/shipments/tests/ -v` (all shipments tests)
  - [ ] `nox -s test` (all project tests)

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
- [ ] End-to-end testing:
  - [ ] Test complete pagination flows
  - [ ] Test integration with frontend components
  - [ ] Test performance under load
- [ ] Cross-service testing:
  - [ ] Test pagination with other services
  - [ ] Verify API gateway compatibility
  - [ ] Test authentication and authorization
- [ ] Development environment testing:
  - [ ] Test with `./scripts/start-all-services.sh` (full stack)
  - [ ] Test individual service with `uv run python -m uvicorn services.shipments.main:app --reload`
  - [ ] Test database migrations with `alembic -c services/shipments/alembic.ini upgrade head`

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
- [ ] Add `itsdangerous` to `services/user/pyproject.toml` dependencies
- [ ] Run `uv sync --all-packages --all-extras --active` to install new dependency
- [ ] Create `services/user/utils/pagination.py` for user-specific pagination utilities
- [ ] Add user-specific pagination configuration to `services/user/settings.py`

#### 2. User Service Core Pagination Implementation
- [ ] Create `services/user/utils/pagination.py` extending common base:
  - [ ] `UserCursorPagination` class extending `BaseCursorPagination`
  - [ ] User-specific cursor data structure:
    - [ ] `last_id`: Integer ID of last user in current page
    - [ ] `last_created_at`: ISO timestamp for consistent ordering
    - [ ] `filters`: JSON string of active filters (query, email, onboarding_completed)
    - [ ] `direction`: 'next' or 'prev'
    - [ ] `limit`: Number of items per page
  - [ ] User-specific query building logic
  - [ ] User-specific cursor validation rules

#### 3. User Service Schema Updates
- [ ] **COMPLETELY REPLACE** `services/user/schemas/user.py` pagination schemas:
  - [ ] **REMOVE** the old `UserListResponse` class entirely (lines 238-246)
  - [ ] **REMOVE** all `page`, `page_size`, `total` fields
  - [ ] Create new `UserCursorListResponse` class with only cursor fields:
    - [ ] `users: list[UserResponse]`
    - [ ] `next_cursor?: string`
    - [ ] `prev_cursor?: string`
    - [ ] `has_next: boolean`
    - [ ] `has_prev: boolean`
    - [ ] `limit: number`
- [ ] **COMPLETELY REPLACE** `UserSearchRequest` class (lines 325-326):
  - [ ] **REMOVE** `page` and `page_size` fields
  - [ ] Add cursor-based parameters:
    - [ ] `cursor?: string`
    - [ ] `limit?: number`
    - [ ] `direction?: 'next' | 'prev'`
    - [ ] Keep existing filter fields: `query`, `email`, `onboarding_completed`

#### 4. User Service Database Query Updates
- [ ] **COMPLETELY REWRITE** `services/user/services/user_service.py` pagination logic:
  - [ ] **REMOVE** all offset-based pagination code from `search_users()` method (lines 528-628)
  - [ ] **REMOVE** all `page`, `page_size`, `offset` calculations
  - [ ] **REMOVE** all legacy pagination response formatting
  - [ ] Implement pure cursor-based pagination in `search_users()` method
  - [ ] Use cursor-based filtering with `WHERE` clauses
  - [ ] Add proper ordering (by `id` and `created_at`)
  - [ ] Implement bidirectional pagination support
- [ ] Update database queries:
  - [ ] **REMOVE** all offset-based query logic
  - [ ] Implement cursor-based filtering logic only
  - [ ] Add proper indexing for cursor fields (`id`, `created_at`)
  - [ ] Add query optimization for large datasets
  - [ ] Handle edge cases (empty results, last page, etc.)

#### 5. User Service API Endpoint Updates
- [ ] **COMPLETELY REPLACE** query parameters in `/users/search` endpoint:
  - [ ] **REMOVE** `page` parameter entirely
  - [ ] **REMOVE** `page_size` parameter entirely
  - [ ] **REMOVE** all legacy pagination parameters
  - [ ] Add only cursor-based parameters:
    - [ ] `cursor?: string` (replaces page)
    - [ ] `limit?: number` (replaces page_size)
    - [ ] `direction?: 'next' | 'prev'` (for bidirectional pagination)
    - [ ] Keep existing filter parameters: `query`, `email`, `onboarding_completed`
- [ ] **COMPLETELY REPLACE** response format:
  - [ ] **REMOVE** all legacy pagination fields from responses
  - [ ] Include only cursor-based pagination:
    - [ ] `next_cursor?: string`
    - [ ] `prev_cursor?: string`
    - [ ] `has_next: boolean`
    - [ ] `has_prev: boolean`
    - [ ] `limit: number`
- [ ] Update error handling:
  - [ ] **REMOVE** all legacy pagination error handling
  - [ ] Add cursor validation errors
  - [ ] Handle expired or invalid tokens
  - [ ] Add proper HTTP status codes for pagination errors

#### 6. User Service Filtering and Search Integration
- [ ] Update search functionality to work with cursors:
  - [ ] Encode filter parameters in cursor tokens
  - [ ] Maintain filter state across pagination
  - [ ] Handle dynamic filter changes
- [ ] Update user filtering:
  - [ ] Include filter state in cursor data
  - [ ] Ensure consistent results across pages
  - [ ] Handle filter combinations properly

#### 7. User Service Testing Implementation

##### Common Components Testing
- [ ] Ensure common pagination tests pass:
  - [ ] `uv run python -m pytest services/common/tests/test_pagination.py -v`

##### User Service Testing
- [ ] Create `services/user/tests/test_pagination.py`
  - [ ] Test `UserCursorPagination` extending base functionality
  - [ ] Test user-specific cursor encoding/decoding
  - [ ] Test pagination with various filter combinations
  - [ ] Test edge cases (empty results, single page, etc.)
  - [ ] Test backward pagination
  - [ ] Test cursor expiration and validation
- [ ] Update existing tests:
  - [ ] **REMOVE** all legacy pagination tests from existing test files
  - [ ] **REMOVE** all tests for `page`, `page_size`, `total` functionality
  - [ ] Add cursor pagination tests to existing test files
  - [ ] Add integration tests for cursor pagination flows

##### Test Execution
- [ ] Run tests using UV:
  - [ ] `uv run python -m pytest services/user/tests/test_pagination.py -v`
  - [ ] `uv run python -m pytest services/user/tests/ -v` (all user tests)
  - [ ] `nox -s test` (all project tests)

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
- [ ] End-to-end testing:
  - [ ] Test complete cursor pagination flows
  - [ ] Test integration with other services
  - [ ] Test performance under load
- [ ] Cross-service testing:
  - [ ] Test pagination with other services
  - [ ] Verify API gateway compatibility
  - [ ] Test authentication and authorization
- [ ] Development environment testing:
  - [ ] Test with `./scripts/start-all-services.sh` (full stack)
  - [ ] Test individual service with `uv run python -m uvicorn services.user.main:app --reload`
  - [ ] Test database migrations with `alembic -c services/user/alembic.ini upgrade head`

### User Service Migration Timeline
- **Phase 1**: **COMPLETELY REPLACE** user service pagination with cursor-based system
- **Phase 2**: **REMOVE** all legacy pagination code and tests
- **Phase 3**: **VERIFY** no legacy pagination code remains in user service
- **Phase 4**: **TEST** integration with other services using cursor pagination

**Note**: This is a breaking change. No backward compatibility will be maintained. All API consumers must update to use cursor-based pagination.
