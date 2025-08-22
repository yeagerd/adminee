# Event-Driven Architecture Implementation Tasks

## Overview
Implementation checklist for the revised event-driven Office data architecture with data-type focused topics and selective consumption.

## Phase 1: Event Model Refactoring

### [ ] Update Event Models
- [ ] Refactor `EmailBackfillEvent` to `EmailEvent` with `sync_type` field
- [ ] Add `sync_type` enum: `["batch_sync", "incremental_sync", "real_time"]`
- [ ] Add `operation` field to distinguish create/update/delete for mutable data
- [ ] Add `batch_id` field for batch operations
- [ ] Update `services/common/events/email_events.py`
- [ ] Update `services/common/events/calendar_events.py`
- [ ] Update `services/common/events/contact_events.py`
- [ ] Create new event models for `DocumentEvent` and `TodoEvent`

### [ ] Design Vespa Document Types
- [ ] Design `BaseVespaDocument` with common fields for unified search
- [ ] Create type-specific document classes: `EmailDocument`, `CalendarDocument`, `ContactDocument`
- [ ] Ensure type-appropriate fields (no `from_address` for contacts, etc.)
- [ ] Plan for future document types: `DocumentDocument`, `TodoDocument`, `SheetDocument`, `PresentationDocument`
- [ ] Add internal tool document types: `LLMChatDocument`, `ShipmentEventDocument`, `MeetingPollDocument`, `BookingDocument`

## Phase 2: Topic Restructuring

### [ ] Create New Data-Type Topics
- [ ] Create `emails` topic (replaces `email-backfill`)
- [ ] Create `calendars` topic (replaces `calendar-updates`)
- [ ] Create `contacts` topic (replaces `contact-updates`)
- [ ] Create `documents` topic (new)
- [ ] Create `todos` topic (new)

### [ ] Update Topic Setup Scripts
- [ ] Update `services/demos/setup_pubsub.py` with new topic names
- [ ] Create migration script to handle topic transition
- [ ] Update any hardcoded topic references in code

## Phase 3: Publisher Updates

### [ ] Update Office Service Publishers
- [ ] Modify `services/office/core/pubsub_publisher.py` to use new topic names
- [ ] Update `services/office/api/backfill.py` to publish `EmailEvent` instead of `EmailBackfillEvent`
- [ ] Update event construction to include new fields (`sync_type`, `operation`, `batch_id`)
- [ ] Ensure correlation_id is properly set for batch operations

### [ ] Update Common PubSub Client
- [ ] Update `services/common/pubsub_client.py` helper methods
- [ ] Replace `publish_email_backfill` with `publish_email_event`
- [ ] Add new helper methods for other data types
- [ ] Update method signatures to include new event fields

## Phase 4: Consumer Updates

### [ ] Update Vespa Loader Consumer
- [ ] Modify `services/vespa_loader/pubsub_consumer.py` to subscribe to new topics
- [ ] Update subscription names: `vespa-loader-emails`, `vespa-loader-calendars`, etc.
- [ ] Update event parsing to handle new event structure
- [ ] Ensure idempotency keys use new field structure

### [ ] Implement Vespa Document Factory
- [ ] Create factory pattern to instantiate correct document type based on event data
- [ ] Implement `BaseVespaDocument` with common fields
- [ ] Create type-specific document classes with appropriate fields
- [ ] Update Vespa indexing logic to use new document types
- [ ] Ensure unified search works across all document types

### [ ] Internal Tool Integration
- [ ] Design event schemas for internal tools (LLM chats, shipment events, meeting polls, bookings)
- [ ] Implement event publishing from internal tools to appropriate topics
- [ ] Create Vespa document types for internal tool data
- [ ] Ensure internal tool events follow the same event architecture patterns
- [ ] Test end-to-end flow from internal tools to Vespa search

### [ ] Update Domain-Specific Consumers
- [ ] **Meetings Service**: Update to subscribe to `calendars` topic only
- [ ] **Shipments Service**: Update to subscribe to `emails` topic only
- [ ] **Contact Service**: Create/update to subscribe to `emails`, `calendars`, `documents` for contact discovery
- [ ] **FE SSE Notifier**: Create/update to subscribe to relevant data types

### [ ] Implement Email Contacts Management
- [ ] Design `EmailContact` data model with event type counters and last_seen tracking
- [ ] Decide on service location (user service vs office service)
- [ ] Implement contact discovery from email, calendar, and document events
- [ ] Create contact update events for Vespa integration
- [ ] Implement contact relevance scoring (last_seen + event counts)
- [ ] Add Vespa update triggers for significant contact changes

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

### [ ] Integration Testing
- [ ] Test end-to-end flow with new architecture
- [ ] Verify consumer scaling and isolation
- [ ] Test error handling and retry mechanisms
- [ ] Test unified search across different document types
- [ ] Test contact discovery flow from multiple event sources
- [ ] Test internal tool integration end-to-end
- [ ] Test contact relevance ranking in search results

## Phase 7: Migration and Deployment

### [ ] Migration Strategy
- [ ] Plan gradual migration from old topics to new ones
- [ ] Ensure no data loss during transition
- [ ] Create rollback plan if issues arise

### [ ] Deployment
- [ ] Deploy new event models and publishers
- [ ] Deploy updated consumers
- [ ] Deploy new Vespa document types
- [ ] Monitor for any issues or performance impacts

## Phase 8: Documentation and Monitoring

### [ ] Update Documentation
- [ ] Update API documentation for new event structures
- [ ] Document new topic names and subscription patterns
- [ ] Document Vespa document type design and factory pattern
- [ ] Update deployment guides

### [ ] Monitoring and Observability
- [ ] Update metrics to track new topic usage
- [ ] Add monitoring for selective consumption patterns
- [ ] Ensure correlation_id tracking works for batch operations
- [ ] Monitor Vespa indexing performance with new document types
- [ ] Monitor contact discovery and update rates
- [ ] Track internal tool event processing performance
- [ ] Monitor contact relevance scoring accuracy

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
