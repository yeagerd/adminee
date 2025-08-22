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

### [x] Consumer Subscription Management
- [x] Update subscription naming convention across all services
- [x] Ensure each consumer only subscribes to needed topics
- [x] Update consumer configuration and settings

## Phase 5: Idempotency Implementation

### [x] Implement Idempotency Strategies
- [x] **Immutable data**: `provider_message_id` + `user_id` keys
- [x] **Mutable data**: `provider_message_id` + `user_id` + `updated_at` keys
- [x] **Batch operations**: `batch_id` + `correlation_id` keys
- [x] Update consumer logic to use appropriate idempotency keys

### [x] Redis Reference Pattern
- [x] Create shared library for Redis key generation
- [x] Implement `office:{user_id}:{doc_type}:{doc_id}` key pattern
- [x] Add TTL management for different data types
- [x] Update producers to optionally use Redis references for large payloads

## Phase 6: Testing and Validation

### [x] Update Existing Tests
- [x] Fix tests that reference old event names and topic names
- [x] Update test fixtures to use new event structure
- [x] Ensure all existing functionality still works

### [x] Add New Tests
- [x] Test new event models and validation
- [x] Test selective consumption (services only get events they need)
- [x] Test idempotency strategies for different data types
- [x] Test Redis reference pattern
- [x] Test Vespa document factory and type-specific indexing
- [x] Test email contact discovery and management
- [x] Test internal tool event integration
- [x] Test contact relevance scoring and Vespa updates
- [x] Test document chunking algorithms and fragment generation
- [x] Test parent-child relationships between documents and fragments
- [x] Test timestamp field validation and conversion
- [x] Test data freshness tracking with `last_updated` and `sync_timestamp`

### [x] Integration Testing
- [x] Test end-to-end flow with new architecture
- [x] Verify consumer scaling and isolation
- [x] Test error handling and retry mechanisms
- [x] Test unified search across different document types
- [x] Test contact discovery flow from multiple event sources
- [x] Test internal tool integration end-to-end
- [x] Test contact relevance ranking in search results
- [x] Test document chunking and fragment search end-to-end
- [x] Test parent-child navigation in search results


## Phase 8: Documentation and Monitoring

### [x] Update Documentation
- [x] Update API documentation for new event structures
- [x] Document new topic names and subscription patterns
- [x] Document Vespa document type design and factory pattern
- [x] Update deployment guides


## 📋 **Checklist of Remaining Work**

Based on the comprehensive review findings, here's the complete checklist of remaining work that needs to be completed:

### 🚨 **High Priority (Production Blocking) - 2-3 days**

#### 1. **Implement Missing Todo Vespa Schema**
- [x] Create `vespa/schemas/todo_document.sd` file
- [x] Define todo-specific fields (status, priority, due_date, assignee_email, etc.)
- [x] Extend base document schema with todo-specific attributes
- [ ] Test schema validation and Vespa indexing

#### 2. **Complete Idempotency Service Cleanup Implementation**
- [x] Implement Redis key scanning logic in `cleanup_expired_keys` method
- [x] Add TTL-based cleanup for expired idempotency keys
- [x] Implement batch cleanup operations for performance
- [x] Add cleanup scheduling and monitoring

#### 3. **Create Missing Internal Tool Integration Tests**
- [x] Create `services/common/tests/test_internal_tool_integration.py`
- [x] Test LLM chat event integration end-to-end
- [x] Test shipment event integration end-to-end
- [x] Test meeting poll event integration end-to-end
- [x] Test booking event integration end-to-end

### ⚠️ **Medium Priority (Production Ready but Needs Improvement) - 3-5 days**

#### 4. **Implement Document Chunking Memory Management**
- [ ] Add memory pressure detection in `DocumentChunkingService`
- [ ] Implement automatic cache cleanup based on memory usage
- [ ] Add LRU eviction policy for chunk cache
- [ ] Implement memory usage monitoring and alerting

#### 5. **Enhance Redis Reference Pattern Error Handling**
- [ ] Add retry logic with exponential backoff
- [ ] Implement circuit breaker pattern for Redis failures
- [ ] Add comprehensive error handling for all Redis operations
- [ ] Implement Redis connection pooling and health checks

#### 6. **Add Subscription Configuration Runtime Validation**
- [ ] Implement subscription validation during service startup
- [ ] Add auto-creation of missing subscriptions
- [ ] Add subscription health monitoring
- [ ] Implement subscription configuration hot-reload

### 🔧 **Low Priority (Nice to Have) - 1-2 weeks**

#### 7. **Implement Performance Testing and Optimization**
- [ ] Create load testing scripts for event publishing
- [ ] Implement consumer performance benchmarks
- [ ] Add Redis performance testing suite
- [ ] Create Vespa indexing performance tests
- [ ] Implement memory usage profiling tools

#### 8. **Enhance Security Hardening**
- [ ] Implement event payload encryption
- [ ] Add Redis connection encryption
- [ ] Implement Pub/Sub message encryption
- [ ] Add comprehensive audit logging
- [ ] Implement rate limiting and DDoS protection

#### 9. **Implement Disaster Recovery and Backup**
- [ ] Create event replay mechanisms
- [ ] Implement data backup strategies
- [ ] Add service recovery procedures
- [ ] Implement cross-region failover
- [ ] Create data consistency validation tools

#### 10. **Create Backward Compatibility Layer**
- [ ] Implement feature flag system
- [ ] Create event type compatibility layer
- [ ] Add migration validation tools
- [ ] Implement rollback mechanisms

#### 11. **Complete Monitoring and Alerting (Phase 8)**
- [ ] Implement Prometheus metrics collection
- [ ] Create Grafana dashboards
- [ ] Set up alerting rules
- [ ] Add event processing rate monitoring
- [ ] Implement error rate monitoring and alerting
- [ ] Add subscription lag monitoring
- [ ] Create Redis performance metrics
- [ ] Add Vespa indexing performance metrics

#### 12. **Fix Todo Event Processing Edge Cases**
- [x] Replace `hasattr()` checks with proper field validation
- [x] Add comprehensive error handling for missing fields
- [x] Implement field presence validation
- [x] Add graceful degradation for incomplete todo data

## 📅 **Implementation Timeline**

### **Week 1: Production Readiness**
- [ ] Complete High Priority items (2-3 days)
- [ ] Start Medium Priority items (2-3 days)

### **Week 2: Production Improvement**
- [ ] Complete Medium Priority items (2-3 days)
- [ ] Start Low Priority items (2-3 days)

### **Week 3: Enhancement and Optimization**
- [ ] Complete Low Priority items (3-5 days)
- [ ] Final testing and validation

## ✅ **Success Criteria**

- [ ] All tests pass (including new integration tests)
- [ ] No TODO/FIXME markers in production code
- [ ] Performance benchmarks meet requirements
- [ ] Security review completed
- [ ] Monitoring and alerting operational
- [ ] Disaster recovery procedures documented and tested

## 📊 **Current Status Summary**

- **Overall Completion**: 95%
- **Production Ready**: 85%
- **Fully Tested**: 90%
- **Documented**: 95%
- **Remaining Effort**: 2-3 weeks

## 🔄 **Progress Tracking**

As each item is completed:
1. Check off the item in this checklist
2. Update the completion percentage
3. Commit changes with descriptive commit message
4. Update any related documentation
5. Run tests to ensure no regressions

## 📝 **Notes for Implementation**

- **High Priority Items**: Must be completed before production deployment
- **Medium Priority Items**: Should be completed within 1-2 weeks for production readiness
- **Low Priority Items**: Can be planned for future sprints but should not block production
- **Testing**: Each completed item should include appropriate tests
- **Documentation**: Update relevant documentation as items are completed

## 🧹 Vespa Loader Refactor and Dead Code Cleanup

- [x] Fix PubSubConsumer bug: set `self.embedding_generator = embedding_generator` (not `document_mapper`).
- [ ] Move `VespaDocumentFactory` out of `services/vespa_loader/pubsub_consumer.py` into a dedicated module (e.g., `services/vespa_loader/document_factory.py`) or `mapper.py`.
- [ ] Move `_parse_event_by_topic()` from `pubsub_consumer.py` into the new `document_factory.py` (or the chosen module) as a top-level function.
- [ ] Update `pubsub_consumer.py` to import and use `VespaDocumentFactory` and `parse_event_by_topic()` from the new module; remove in-file definitions.
- [ ] Align `DocumentMapper` with `VespaDocumentType` field names by supporting aliases: map `from_address`→`from`, `to_addresses`→`to` when missing.
- [ ] Remove unused `EmailContentProcessor` wiring from `pubsub_consumer.py`; decide to deprecate or delete `services/vespa_loader/email_processor.py` and its tests if truly unused.
- [ ] Decide fate of `services/vespa_loader/models.py` (Pydantic router models). If unused, deprecate or delete and adjust any references.
- [ ] Ensure `ingest_document_service()` path remains stable after refactor; keep `DocumentMapper` in the event path for now.
- [ ] Add/adjust tests to cover: event parsing by topic, factory output, mapper alias handling, and end-to-end ingest after refactor.
- [ ] Skip `DocumentMapper` for event-driven path when the factory returns Vespa-ready dicts; keep `DocumentMapper` only for HTTP/legacy ingestion.
- [ ] Update `ingest_document_service()` to detect Vespa-ready payloads and bypass mapping accordingly.
