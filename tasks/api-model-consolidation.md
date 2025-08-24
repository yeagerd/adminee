# API Model Consolidation Task List

## Overview
Move all Pydantic models from individual services into `services/api/v1/` to enable inter-service communication using shared API schemas instead of direct imports. This will create a clean separation between internal service models and external API contracts.

## Phase 1: Infrastructure Setup and Common Models

- [x] Create `services/api/v1/` directory structure
- [x] Create `services/api/v1/__init__.py` with proper exports
- [x] Create `services/api/v1/pyproject.toml` for the new API package
- [x] Update root `pyproject.toml` to include the new API package as a dependency
- [x] Create `services/api/v1/README.md` documenting the new structure and usage patterns
- [x] Set up proper import paths and ensure the API package can be imported by all services
- [x] **Common Models**: Move `services/common/models/` contents to `services/api/v1/common/`
- [x] **Common Events**: Move `services/common/events/` schemas to `services/api/v1/common/events/`
- [x] **Common Pagination**: Move `services/common/pagination/` schemas to `services/api/v1/common/pagination/`
- [ ] Update all services to use `services.api.v1.common` instead of `services.common`
- [ ] Ensure common package tests pass
- [ ] Update common package documentation

## Phase 2: User Service Models (Priority: High - Most Referenced)

- [x] Move `services/user/schemas/` contents to `services/api/v1/user/`
  - [x] Move `user.py` schemas
  - [x] Move `integration.py` schemas  
  - [x] Move `preferences.py` schemas
  - [x] Move `pagination.py` schemas
  - [x] Move `health.py` schemas
- [x] Update `services/user/` imports to use `services.api.v1.user` instead of local schemas
- [ ] Update any inter-service calls that import user schemas to use the new API package
  - [ ] Update `services/demos/user_management_demo.py` to use `services.api.v1.user` instead of `services.user.schemas`
  - [ ] Update `services/demos/vespa_backfill.py` user service HTTP calls to use shared user schemas for validation
  - [ ] **Office Service**: Update `services/office/core/pubsub_publisher.py` to use shared user schemas for user_id validation if any user-related schemas are added
  - [ ] **Office Service**: Update `services/office/core/token_manager.py` to use shared user schemas for token validation responses
  - [ ] **Office Service**: Update `services/office/core/api_client_factory.py` to use shared user schemas for user profile responses
  - [ ] **Office Service**: Update `services/office/api/email.py` to use shared user schemas for integration responses
  - [ ] **Office Service**: Update `services/office/api/backfill.py` to use shared user schemas for user existence responses
  - [ ] **Meetings Service**: Update `services/meetings/services/booking_availability.py` to use shared user schemas if user validation schemas are needed
  - [ ] **Meetings Service**: Update `services/meetings/services/email_integration.py` to use shared user schemas for integration responses
  - [ ] **Chat Service**: Update `services/chat/tools/data_tools.py` to use shared user schemas for integration responses
  - [ ] **Vespa Services**: Update `services/vespa_loader/` and `services/vespa_query/` to use shared user schemas for user validation responses
  - [ ] **Demo Services**: Update demo services to use shared user schemas for user service responses
  - [ ] Verify that no other services are making direct calls to user service internal models
- [ ] Ensure user service tests still pass with new import structure
- [ ] Update user service documentation to reflect new API structure

## Phase 3: Office Service Models (Priority: High - Core Integration Service)

- [x] Move `services/office/schemas/` contents to `services/api/v1/office/`
  - [x] Move all schema files from the monolithic `__init__.py`
  - [x] Break down the large schema file into logical modules
- [x] Update `services/office/` imports to use `services.api.v1.office`
- [ ] Update inter-service calls in other services that import office schemas
  - [x] **Chat Service**: Update `services/chat/schemas/office_responses.py` to import `CalendarEvent` from `services.api.v1.office`
  - [x] **Chat Service Tests**: Update `services/chat/tests/test_llm_tools.py` to import `CalendarEvent, Provider` from `services.api.v1.office`
  - [x] **Chat Service Tests**: Update `services/chat/tests/test_timezone_functionality.py` to import `CalendarEvent, Provider` from `services.api.v1.office`
  - [x] **Meetings Service**: Update `services/meetings/services/calendar_integration.py` to import `EmailAddress, CreateCalendarEventRequest` from `services.api/v1.office`
  - [x] **Demos**: Update `services/demos/office_full.py` to import `ApiResponse` from `services.api.v1.office`
  - [ ] **Demos**: Update `services/demos/office.py` to import `EmailMessage` from `services.api.v1.office`
  - [x] **Office Service Internal**: Update all internal office service files to use `services.api.v1.office` instead of local schemas
- [x] Update office service tests and ensure they pass
- [ ] Update office service documentation

## Phase 4: Meetings Service Models (Priority: Medium)

- [x] Move `services/meetings/schemas/` contents to `services/api/v1/meetings/`
  - [x] Move `booking_requests.py` schemas
- [x] Update `services/meetings/` imports to use `services.api.v1.meetings`
- [x] Update any inter-service calls that import meetings schemas
  - [x] **Common Events**: Update `services/common/events/internal_tool_events.py` to use `MeetingPollData` from `services.api.v1.meetings` instead of local definition
  - [ ] **Common Events**: Update `services/common/events/__init__.py` to export from `services.api.v1.meetings`
  - [x] **Common Tests**: Update `services/common/tests/test_internal_tool_integration.py` to import `MeetingPollData, MeetingPollEvent` from `services.api/v1.meetings`
  - [x] **Office Service**: Update `services/office/api/calendar.py` to use `CreateCalendarEventRequest` from `services.api/v1.office` (already handled in Phase 3)
  - [ ] **Office Tests**: Update `services/office/tests/test_validation.py` to use `CreateCalendarEventRequest` from `services.api.v1.office` (already handled in Phase 3)
  - [x] Verify that no other services are making direct calls to meetings service internal models
- [x] Ensure meetings service tests pass
- [ ] Update meetings service documentation

## Phase 5: Chat Service Models (Priority: Medium)

- [x] Move `services/chat/schemas/` contents to `services/api/v1/chat/`
  - [x] Move `office_responses.py` schemas
- [x] Move any other schema files that exist
- [x] Update `services/chat/` imports to use `services.api.v1.chat`
- [x] Update inter-service calls that import chat schemas
  - [x] **Common Events**: Update `services/common/events/internal_tool_events.py` to use `LLMChatMessageData` from `services.api.v1.chat` instead of local definition
  - [x] **Common Events**: Update `services/common/events/__init__.py` to export from `services.api/v1.chat`
  - [x] **Common Tests**: Update `services/common/tests/test_internal_tool_integration.py` to import `LLMChatMessageData` from `services.api.v1.chat`
  - [x] **Demos**: Update `services/demos/chat.py` to use shared chat schemas for type annotations and validation
  - [x] **Demos**: Update `services/demos/vespa_search.py` to use shared chat schemas if any chat-related schemas are needed
  - [x] **Demos**: Update `services/demos/vespa_synthetic.py` to use shared chat schemas if any chat-related schemas are needed
  - [x] Verify that no other services are making direct calls to chat service internal models
- [x] Ensure chat service tests pass
- [ ] Update chat service documentation

## Phase 6: Shipments Service Models (Priority: Medium)

- [ ] Move `services/shipments/schemas/` contents to `services/api/v1/shipments/`
  - [ ] Move `pagination.py` schemas
  - [ ] Move `email_parser.py` schemas
- [ ] Update `services/shipments/` imports to use `services.api.v1.shipments`
- [ ] Update inter-service calls that import shipments schemas
  - [ ] **Common Pagination**: Update `services/shipments/schemas/pagination.py` to import from `services.api.v1.common.pagination` instead of `common.pagination.schemas`
  - [ ] **Frontend Integration**: Update any frontend API calls that use shipments schemas to use the new shared API package
  - [ ] **Gateway Integration**: Ensure the gateway can properly route requests using the new shared shipments schemas
  - [ ] Verify that no other services are making direct calls to shipments service internal models
- [ ] Ensure shipments service tests pass
- [ ] Update shipments service documentation

## Phase 7: Email Sync Service Models (Priority: Low)

- [ ] Move `services/email_sync/models/` contents to `services/api/v1/email_sync/`
- [ ] Update `services/email_sync/` imports to use `services.api.v1.email_sync`
- [ ] Update any inter-service calls that import email sync schemas
  - [ ] **No models directory content** - the email sync service models directory is empty
  - [ ] **Meetings Service Integration**: Update `services/meetings/api/email.py` to use shared email sync schemas for API key validation if any are added
  - [ ] **Common Config**: Update `services/common/config/subscription_config.py` to reference the new email sync API package structure
  - [ ] **Frontend Integration**: Update any frontend API calls that use email sync schemas to use the new shared API package
  - [ ] **Gateway Integration**: Ensure the gateway can properly route requests using the new shared email sync schemas
  - [ ] Verify that no other services are making direct calls to email sync service internal models
- [ ] Ensure email sync service tests pass
- [ ] Update email sync service documentation

## Phase 8: Vespa Services Models (Priority: Low)

- [ ] Move `services/vespa_loader/models/` contents to `services/api/v1/vespa/`
- [ ] Move `services/vespa_query/` schemas if they exist
- [ ] Update vespa services to use `services.api.v1.vespa`
- [ ] Update inter-service calls that import vespa schemas
  - [ ] **Vespa Loader Models**: Update `services/vespa_loader/services/document_chunking_service.py` to use `DocumentChunkingConfig` from `services.api.v1.vespa` instead of local models
  - [ ] **Vespa Loader Tests**: Update `services/vespa_loader/tests/test_document_chunking_service.py` to import from `services.api.v1.vespa`
  - [ ] **Vespa Loader Tests**: Update `services/vespa_loader/tests/test_document_factory.py` to import `VespaDocumentType` from `services.api.v1.vespa`
  - [ ] **Vespa Loader Tests**: Update `services/vespa_loader/tests/test_ingest_service.py` to import `VespaDocumentType` from `services.api.v1.vespa`
  - [ ] **Vespa Loader Tests**: Update `services/vespa_loader/tests/test_pubsub_consumer.py` to import `VespaDocumentType` from `services.api.v1.vespa`
  - [ ] **Chat Service**: Update `services/chat/tools/search_tools.py` to use shared vespa schemas for search functionality if any are added
  - [ ] **Demo Services**: Update `services/demos/vespa_search.py` to use shared vespa schemas for search functionality if any are added
  - [ ] **Demo Services**: Update `services/demos/vespa_synthetic.py` to use shared vespa schemas for search functionality if any are added
  - [ ] **Demo Services**: Update `services/demos/vespa_backfill.py` to use shared vespa schemas for search functionality if any are added
  - [ ] **Common Tests**: Update `services/common/tests/test_event_driven_architecture_integration.py` to import `DocumentChunkingService` from `services.api.v1.vespa`
  - [ ] **Common Tests**: Update `services/common/tests/test_internal_tool_integration.py` to import `VespaDocumentFactory` from `services.api.v1.vespa`
  - [ ] Verify that no other services are making direct calls to vespa service internal models
- [ ] Ensure vespa service tests pass
- [ ] Update vespa service documentation

## Phase 9: Frontend Type Generation Updates

- [x] Update type generation workflow - using `scripts/subscripts/update-types.sh` instead of unused `frontend/scripts/generate-types.sh`
- [ ] Ensure the script can find and process schemas from `services/api/v1/`
- [ ] Test that generated TypeScript types are correct and complete
- [ ] Update frontend API clients if needed to use new type structure
- [ ] Verify that frontend builds and tests pass with new types

## Phase 10: Inter-Service Call Updates

- [ ] Audit all `from services.` imports across the codebase
- [ ] Update imports to use the new API package structure
- [ ] Ensure no service imports internal models from other services
- [ ] Update any service clients or HTTP calls to use the shared API schemas
- [ ] Verify that all inter-service communication uses the API layer

## Phase 11: Testing and Validation

- [ ] Run full test suite for all services to ensure no regressions
- [ ] Run mypy type checking on all services to catch any import issues
- [ ] Verify that OpenAPI schema generation still works correctly
- [ ] Test that frontend can still communicate with all services
- [ ] Validate that inter-service communication works as expected

## Phase 12: Documentation and Cleanup

- [ ] Update all service README files to reflect new import patterns
- [ ] Update API documentation to show the new shared schema structure
- [ ] Remove old schema directories from individual services
- [ ] Update any deployment scripts or Docker configurations if needed
- [ ] Create migration guide for developers

## Phase 13: Build and Configuration Updates

- [ ] **Root pyproject.toml**: Update to include new `services/api/v1` package in UV workspace members
- [ ] **Root pyproject.toml**: Add `services/api/v1` to setuptools packages find configuration
- [ ] **Root pyproject.toml**: Update mypy exclude patterns to handle new API package structure
- [ ] **install.sh**: Update to ensure new API package is properly installed during setup
- [ ] **noxfile.py**: Update typecheck sessions to handle new API package structure
- [ ] **noxfile.py**: Update test sessions to ensure new API package is available
- [ ] **scripts/generate-openapi-schemas.sh**: Update service discovery to include new API package
- [ ] **scripts/generate-openapi-schemas.sh**: Update excluded services list to handle new structure
- [ ] **scripts/update-types.sh**: Update service discovery to handle new API package structure
- [ ] **scripts/update-types.sh**: Update excluded services list for frontend type generation
- [ ] **scripts/validate-types.sh**: Update validation logic for new API package structure
- [ ] **scripts/start-all-services.sh**: Update service startup to ensure new API package is available
- [ ] **scripts/fix-imports.sh**: Update import fixing patterns for new API package structure
- [x] **Frontend scripts**: Removed unused `frontend/scripts/generate-types.sh` - using `scripts/subscripts/update-types.sh` instead
- [ ] **Service pyproject.toml files**: Update all service pyproject.toml files to depend on new API package
- [ ] **Docker configurations**: Update any Docker files to include new API package
  - [ ] **Dockerfile.user-service**: Add `COPY services/api/v1/ ./services/api/v1/` and install with `uv pip install --system -e services/api/v1`
  - [ ] **Dockerfile.office-service**: Add `COPY services/api/v1/ ./services/api/v1/` and install with `uv pip install --system -e services/api/v1`
  - [ ] **Dockerfile.chat-service**: Add `COPY services/api/v1/ ./services/api/v1/` and install with `uv pip install --system -e services/api/v1`
  - [ ] **Dockerfile.vespa-query**: Add `COPY services/api/v1/ ./services/api/v1/` and install with `uv pip install --system -e services/api/v1`
  - [ ] **docker-compose.yml**: Ensure all services have access to the new API package volume mounts
- [ ] **CI/CD configurations**: Update GitHub Actions or other CI/CD files to handle new structure
  - [ ] **.github/workflows/ci.yml**: Update service discovery logic to include new API package in schema validation
  - [ ] **.github/workflows/ci.yml**: Update excluded services list to handle new structure (remove `common` from excluded services)
  - [ ] **.github/workflows/ci.yml**: Update OpenAPI schema generation to handle new API package structure
  - [ ] **.github/workflows/autofix.yml**: Ensure UV sync includes new API package dependencies
  - [ ] **cloudbuild.yaml**: Update Docker build steps to include new API package in all service builds

## Phase 14: Final Validation

- [ ] Run end-to-end tests to ensure system still works
- [ ] Verify that all services can start up correctly
- [ ] Check that database migrations and models still work
- [ ] Validate that the gateway can still route requests properly
- [ ] Final review of the new architecture

## Notes

- Each phase should be completed and tested before moving to the next
- After each service migration, commit changes and ensure tests pass
- The goal is to have zero direct imports between service internal models
- All inter-service communication should use the shared API schemas
- Frontend type generation should continue to work seamlessly
- This refactoring should not break existing API contracts or frontend functionality
- **Important**: Common schemas (Phase 1) must be completed before other phases since they are dependencies for other services
