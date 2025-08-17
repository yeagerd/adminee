# OpenAPI Schema Generation & TypeScript Type Sync

## Overview
Generate OpenAPI schemas from all Pydantic models across services and create TypeScript types for the frontend to eliminate duplicate type definitions and maintain a single source of truth.

## Goals
- Single source of truth: Pydantic models define API contract
- Automatic sync: Frontend types update when backend changes
- Runtime validation: Backend validates requests/responses
- Type safety: Full TypeScript intellisense in frontend
- API documentation: OpenAPI schema serves as living documentation

## Services to Cover
- [ ] `services/chat/` - Chat service with draft management
- [ ] `services/meetings/` - Meeting scheduling and polling
- [ ] `services/office/` - Google/Microsoft integrations
- [ ] `services/user/` - User management and OAuth
- [ ] `services/shipments/` - Package tracking
- [ ] `services/common/` - Shared schemas and utilities
- [ ] `services/email_sync/` - Email synchronization
- [ ] `services/vector_db/` - Vector database operations

## Phase 1: Backend OpenAPI Schema Generation

### Task 1.1: Install OpenAPI Generation Dependencies
- [x] Add `fastapi[all]` to each service's dependencies if not present
- [ ] Ensure each service has proper FastAPI app configuration with metadata
- [ ] Verify OpenAPI schema generation is enabled

### Task 1.2: Enhance FastAPI App Configurations
- [x] Update `services/chat/main.py` with proper OpenAPI metadata
- [x] Update `services/meetings/main.py` with proper OpenAPI metadata  
- [x] Update `services/office/app/main.py` with proper OpenAPI metadata
- [x] Update `services/user/main.py` with proper OpenAPI metadata
- [x] Update `services/shipments/main.py` with proper OpenAPI metadata
- [x] Add OpenAPI tags and descriptions to all router endpoints

### Task 1.3: Generate OpenAPI Schemas
- [x] Create script to generate OpenAPI schemas from all services
- [x] Generate schema for chat service: `/openapi.json`
- [x] Generate schema for meetings service: `/openapi.json`
- [x] Generate schema for office service: `/openapi.json`
- [x] Generate schema for user service: `/openapi.json`
- [x] Generate schema for shipments service: `/openapi.json`
- [x] Generate schema for email_sync service: `/openapi.json`
- [x] Generate schema for vector_db service: `/openapi.json`

### Task 1.4: Schema Validation & Testing
- [x] Validate all generated OpenAPI schemas against OpenAPI 3.0 spec
- [ ] Test schema generation in CI/CD pipeline
- [ ] Ensure all Pydantic models are properly exposed in schemas
- [ ] Verify enum values and constraints are correctly represented

## Phase 2: Frontend Type Generation Setup

### Task 2.1: Install TypeScript Code Generation Tools
- [x] Add `openapi-typescript-codegen` to frontend dev dependencies
- [x] Add `@openapitools/openapi-generator-cli` as alternative option
- [x] Create npm scripts for type generation

### Task 2.2: Create Type Generation Scripts
- [x] Create `scripts/generate-types.sh` for Unix systems
- [x] Create `scripts/generate-types.bat` for Windows systems
- [x] Add type generation to frontend package.json scripts
- [x] Create configuration files for each service's type generation

### Task 2.3: Set Up Type Generation Pipeline
- [x] Create `frontend/scripts/` directory for build scripts
- [x] Create `frontend/types/api/` directory structure for generated types
- [x] Set up type generation for each service
- [x] Create index files to export all generated types

## Phase 3: Service-Specific Type Generation

### Task 3.1: Chat Service Types
- [x] Generate types from `services/chat/models.py` schemas
- [x] Include: `ChatRequest`, `ChatResponse`, `ThreadResponse`, `MessageResponse`
- [x] Include: `DraftEmail`, `DraftCalendarEvent`, `UserDraftResponse`
- [x] Generate types for all API endpoints in `services/chat/api.py`

### Task 3.2: Meetings Service Types
- [x] Generate types from `services/meetings/schemas/` schemas
- [x] Include: `BookingSettings`, `AvailabilityRequest`, `PollResponse`
- [x] Include: `BusinessHoursConfig`, `MeetingPoll`, `BookingSlot`
- [x] Generate types for all API endpoints in meetings routers

### Task 3.3: Office Service Types
- [x] Generate types from `services/office/schemas/` schemas
- [x] Include: `EmailMessage`, `CalendarEvent`, `DriveFile`, `Contact`
- [x] Include: `AvailabilityResponse`, `TypedApiResponse`, `ApiError`
- [x] Generate types for all API endpoints in office routers

### Task 3.4: User Service Types
- [x] Generate types from `services/user/schemas/` schemas
- [x] Include: `UserBase`, `UserResponse`, `UserUpdate`, `UserCreate`
- [x] Include: `IntegrationResponse`, `NotificationPreferences`, `AIPreferences`
- [x] Generate types for all API endpoints in user routers

### Task 3.5: Shipments Service Types
- [x] Generate types from `services/shipments/schemas/` schemas
- [x] Include: `Package`, `TrackingEvent`, `Label`, `CarrierConfig`
- [x] Include: `EmailParseRequest`, `ParsedTrackingInfo`
- [x] Generate types for all API endpoints in shipments routers

### Task 3.6: Common Service Types
- [x] Generate types from `services/common/` schemas
- [x] Include: `ErrorResponse`, `BrieflyAPIError`, pagination schemas
- [x] Ensure shared types are available across all services

## Phase 4: Frontend Integration

### Task 4.1: Update Frontend API Clients
- [x] Update `frontend/api/clients/` to use generated types
- [x] Replace manual type definitions with generated ones
- [x] Update `frontend/api/types/common.ts` to use generated common types
- [x] Ensure all API calls use proper generated types

### Task 4.2: Update Frontend Components
- [x] Update components to use generated types instead of manual definitions
- [x] Update form schemas to use generated types
- [x] Update state management to use generated types
- [x] Update prop interfaces to use generated types

### Task 4.3: Type Safety Verification
- [ ] Run `npm run typecheck` to verify no type errors
- [ ] Run `npm run lint` to ensure code quality
- [ ] Run `npm test` to verify no runtime issues
- [ ] Test all major user flows with new types

## Phase 5: Automation & CI/CD

### Task 5.1: Automated Type Generation
- [ ] Create GitHub Action to generate types on schema changes
- [ ] Set up pre-commit hooks for type generation
- [ ] Create development workflow for type updates
- [ ] Add type generation to build pipeline

### Task 5.2: Schema Versioning & Breaking Changes
- [ ] Implement schema versioning strategy
- [ ] Create breaking change detection
- [ ] Set up automated compatibility checks
- [ ] Create migration guides for API changes

### Task 5.3: Documentation & Monitoring
- [ ] Update API documentation to use generated schemas
- [ ] Create developer guide for type generation
- [ ] Set up monitoring for schema generation failures
- [ ] Document type generation workflow

## Phase 6: Testing & Validation

### Task 6.1: End-to-End Testing
- [ ] Test type generation across all services
- [ ] Verify generated types match actual API responses
- [ ] Test type safety in frontend components
- [ ] Validate OpenAPI schemas against actual endpoints

### Task 6.2: Performance Testing
- [ ] Measure type generation performance
- [ ] Test build time impact
- [ ] Verify no runtime performance degradation
- [ ] Optimize type generation if needed

## Implementation Notes

### Recommended Tools
- **Backend**: FastAPI's built-in OpenAPI generation
- **Frontend**: `openapi-typescript-codegen` or `@openapitools/openapi-generator-cli`
- **Validation**: OpenAPI 3.0 spec validation
- **CI/CD**: GitHub Actions for automated generation

### File Structure
```
frontend/
├── types/
│   └── api/
│       ├── chat/
│       ├── meetings/
│       ├── office/
│       ├── user/
│       ├── shipments/
│       ├── common/
│       └── index.ts
├── scripts/
│   ├── generate-types.sh
│   └── generate-types.bat
└── package.json (with type generation scripts)
```

### Benefits
- **Single Source of Truth**: Pydantic models define API contract
- **Automatic Sync**: Types update when backend changes
- **Runtime Validation**: Backend validates requests/responses
- **Type Safety**: Full TypeScript intellisense
- **Documentation**: Living API documentation
- **Developer Experience**: Faster development with accurate types

### Challenges & Mitigation
- **Schema Complexity**: Use proper OpenAPI metadata and examples
- **Breaking Changes**: Implement versioning and migration strategies
- **Performance**: Optimize type generation and caching
- **Maintenance**: Automate generation and validation

## Success Criteria
- [ ] All services generate valid OpenAPI schemas
- [ ] Frontend types are automatically generated from schemas
- [ ] No manual type definitions in frontend
- [ ] Full type safety across all API interactions
- [ ] Automated type generation in CI/CD pipeline
- [ ] Comprehensive API documentation from schemas
- [ ] Zero type mismatches between frontend and backend

## Timeline
- **Phase 1-2**: 1-2 weeks (Backend setup + Frontend tooling)
- **Phase 3**: 2-3 weeks (Service-by-service type generation)
- **Phase 4**: 1-2 weeks (Frontend integration)
- **Phase 5**: 1 week (Automation)
- **Phase 6**: 1 week (Testing & validation)

**Total Estimated Time**: 6-9 weeks
