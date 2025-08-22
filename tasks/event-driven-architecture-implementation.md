# Event-Driven Architecture Implementation Tasks

## Overview
Implementation checklist for the revised event-driven Office data architecture with data-type focused topics and selective consumption.

## Phase 1: Event Model Refactoring

### [x] Update Event Models
- [x] Refactor `EmailBackfillEvent` to `EmailEvent`
- [x] Add `operation` field to distinguish create/update/delete for mutable data
- [x] Add `batch_id` field for batch operations
- [x] Add `last_updated` field for content age tracking
- [x] Add `sync_timestamp` field for data freshness tracking
- [x] Update `services/common/events/email_events.py`
- [x] Update `services/common/events/calendar_events.py`
- [x] Update `services/common/events/contact_events.py`
- [x] Create new event models for `DocumentEvent` and `TodoEvent`

### [x] Design Vespa Document Types
- [x] Design `BaseVespaDocument` with common fields for unified search
- [x] Create type-specific document classes: `EmailDocument`, `CalendarDocument`, `ContactDocument`
- [x] Ensure type-appropriate fields (no `from_address` for contacts, etc.)
- [x] Create Office document types: `WordDocument`, `SheetDocument`, `PresentationDocument`, `TaskDocument`
- [x] Add internal tool document types: `LLMChatDocument`, `ShipmentEventDocument`, `MeetingPollDocument`, `BookingDocument`

## Phase 2: Topic Restructuring

### [x] Create New Data-Type Topics
- [x] Create `emails` topic (replaces `email-backfill`)
- [x] Create `calendars` topic (replaces `calendar-updates`)
- [x] Create `contacts` topic (replaces `contact-updates`)
- [x] Create `word_documents` topic (new)
- [x] Create `word_fragments` topic (new)
- [x] Create `sheet_documents` topic (new)
- [x] Create `sheet_fragments` topic (new)
- [x] Create `presentation_documents` topic (new)
- [x] Create `presentation_fragments` topic (new)
- [x] Create `task_documents` topic (new)
- [x] Create `todos` topic (new)

### [x] Update Topic Setup Scripts
- [x] Update `services/demos/setup_pubsub.py` with new topic names
- [x] Create migration script to handle topic transition
- [x] Update any hardcoded topic references in code

## Phase 3: Publisher Updates

### [x] Update Office Service Publishers
- [x] Modify `services/office/core/pubsub_publisher.py` to use new topic names
- [x] Update `services/office/api/backfill.py` to publish `EmailEvent` instead of `EmailBackfillEvent`
- [x] Update event construction to include new fields (`sync_type`, `operation`, `batch_id`)
- [x] Ensure correlation_id is properly set for batch operations

### [x] Update Common PubSub Client
- [x] Update `services/common/pubsub_client.py` helper methods
- [x] Replace `publish_email_backfill` with `publish_email_event`
- [x] Add new helper methods for other data types
- [x] Update method signatures to include new event fields
- [x] Ensure `last_updated` and `sync_timestamp` are properly set in events

## Phase 4: Consumer Updates

### [x] Update Vespa Loader Consumer
- [x] Modify `services/vespa_loader/pubsub_consumer.py` to subscribe to new topics
- [x] Update subscription names: `vespa-loader-emails`, `vespa-loader-calendars`, `vespa-loader-word-documents`, `vespa-loader-word-fragments`, `vespa-loader-sheet-documents`, `vespa-loader-sheet-fragments`, `vespa-loader-presentation-documents`, `vespa-loader-presentation-fragments`, `vespa-loader-task-documents`, etc.
- [x] Update event parsing to handle new event structure
- [x] Ensure idempotency keys use new field structure
- [x] Handle parent-child relationships between documents and fragments

### [x] Implement Vespa Document Factory
- [x] Create factory pattern to instantiate correct document type based on event data
- [x] Implement `BaseVespaDocument` with common fields
- [x] Create type-specific document classes with appropriate fields
- [x] Update Vespa indexing logic to use new document types
- [x] Ensure unified search works across all document types
- [x] Implement timestamp handling for `last_updated` and `sync_timestamp`
- [x] Ensure proper timestamp conversion and validation

### [x] Internal Tool Integration
- [x] Design event schemas for internal tools (LLM chats, shipment events, meeting polls, bookings)
- [x] Implement event publishing from internal tools to appropriate topics
- [x] Create Vespa document types for internal tool data
- [x] Ensure internal tool events follow the same event architecture patterns
- [x] Test end-to-end flow from internal tools to Vespa search

### [x] Update Domain-Specific Consumers
- [x] **Meetings Service**: Update to subscribe to `calendars` topic only
- [x] **Shipments Service**: Update to subscribe to `emails` topic only
- [x] **Contact Service**: Create/update to subscribe to `emails`, `calendars`, `documents` for contact discovery
- [x] **FE SSE Notifier**: Create/update to subscribe to relevant data types

### [x] Implement Email Contacts Management
- [x] Design `EmailContact` data model with event type counters and last_seen tracking
- [x] Decide on service location (user service vs office service)
- [x] Implement contact discovery from email, calendar, and document events
- [x] Create contact update events for Vespa integration
- [x] Implement contact relevance scoring (last_seen + event counts)
- [x] Add Vespa update triggers for significant contact changes

### [x] Implement Document Chunking Strategy
- [x] Design chunking algorithms for different document types (Word, Sheet, Presentation)
- [x] Implement parent-child relationship tracking between documents and fragments
- [x] Create fragment generation service that processes large documents
- [x] Implement chunking rules (section boundaries, page limits, semantic breaks)
- [x] Ensure fragment metadata includes parent document references
- [x] Test chunking performance and search relevance

### [ ] Consumer Subscription Management
- [ ] Update subscription naming convention across all services
- [ ] Ensure each consumer only subscribes to needed topics
- [ ] Update consumer configuration and settings

## Phase 5: Idempotency Implementation

### [ ] Implement Idempotency Strategies
- [ ] **Immutable data**: `provider_message_id` + `user_id` keys
- [ ] **Mutable data**: `provider_message_id` + `user_id` + `updated_at` keys
- [ ] **Batch operations**: `batch_id` + `correlation_id` keys
- [ ] Update consumer logic to use appropriate idempotency keys

### [ ] Redis Reference Pattern
- [ ] Create shared library for Redis key generation
- [ ] Implement `office:{user_id}:{doc_type}:{doc_id}` key pattern
- [ ] Add TTL management for different data types
- [ ] Update producers to optionally use Redis references for large payloads

## Phase 6: Testing and Validation

### [ ] Update Existing Tests
- [ ] Fix tests that reference old event names and topic names
- [ ] Update test fixtures to use new event structure
- [ ] Ensure all existing functionality still works

### [ ] Add New Tests
- [ ] Test new event models and validation
- [ ] Test selective consumption (services only get events they need)
- [ ] Test idempotency strategies for different data types
- [ ] Test Redis reference pattern
- [ ] Test Vespa document factory and type-specific indexing
- [ ] Test email contact discovery and management
- [ ] Test internal tool event integration
- [ ] Test contact relevance scoring and Vespa updates
- [ ] Test document chunking algorithms and fragment generation
- [ ] Test parent-child relationships between documents and fragments
- [ ] Test timestamp field validation and conversion
- [ ] Test data freshness tracking with `last_updated` and `sync_timestamp`

### [ ] Integration Testing
- [ ] Test end-to-end flow with new architecture
- [ ] Verify consumer scaling and isolation
- [ ] Test error handling and retry mechanisms
- [ ] Test unified search across different document types
- [ ] Test contact discovery flow from multiple event sources
- [ ] Test internal tool integration end-to-end
- [ ] Test contact relevance ranking in search results
- [ ] Test document chunking and fragment search end-to-end
- [ ] Test parent-child navigation in search results


## Phase 8: Documentation and Monitoring

### [ ] Update Documentation
- [ ] Update API documentation for new event structures
- [ ] Document new topic names and subscription patterns
- [ ] Document Vespa document type design and factory pattern
- [ ] Update deployment guides

## Dependencies and Order

1. **Event Model Refactoring** must be done first
2. **Vespa Document Type Design** can be done in parallel with event models
3. **Topic Restructuring** can happen in parallel with Publisher Updates
4. **Consumer Updates** depend on new topics, event models, and Vespa document types
5. **Idempotency Implementation** can be done incrementally
6. **Testing** should be done at each phase
7. **Migration** happens last after all components are ready

## Notes

- Keep existing `EmailBackfillEvent` working during transition
- Consider feature flags for gradual rollout
- Monitor message processing performance during migration
- Ensure backward compatibility where possible
- Vespa document factory should gracefully handle unknown event types
- Test unified search performance with new document type structure
- Email contacts service location decision affects data ownership and scaling
- Internal tool events should follow same patterns as office data events
- Contact relevance scoring thresholds need tuning based on user behavior
- Consider contact data retention policies and GDPR compliance
