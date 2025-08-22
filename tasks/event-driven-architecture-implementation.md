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

### [ ] Monitoring and Observability
- [ ] Implement monitoring dashboards for the new event-driven architecture
- [ ] Set up alerting for critical metrics
- [ ] Create operational runbooks

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

## Deferred Work and Incomplete Implementations

During the comprehensive review of the implemented code, several areas were identified where work was deferred, marked as TODO, or potentially incomplete. These items should be addressed before considering the implementation production-ready.

### 1. Idempotency Service Cleanup Implementation

**File**: `services/common/idempotency/idempotency_service.py`
**Issue**: The `cleanup_expired_keys` method is not fully implemented
**Current Status**: Returns 0 and logs "Cleanup of expired idempotency keys not implemented"
**Required Work**: Implement Redis key scanning and cleanup logic for expired idempotency keys

```python
def cleanup_expired_keys(self, max_age_hours: int = 24) -> int:
    """Clean up expired idempotency keys."""
    try:
        # This would typically scan Redis for expired keys
        # For now, return 0 as cleanup is not implemented
        logger.info("Cleanup of expired idempotency keys not implemented")
        return 0
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 0
```

### 2. Todo Event Processing Edge Cases

**File**: `services/user/services/contact_discovery_service.py`
**Issue**: Todo event processing has incomplete error handling for missing fields
**Current Status**: Uses `hasattr()` check which may not catch all edge cases
**Required Work**: Implement proper field validation and error handling for todo events

```python
def process_todo_event(self, event: TodoEvent) -> None:
    """Process a todo event to discover contacts."""
    try:
        # Extract assignee information from todo
        if hasattr(event.todo, 'assignee_email') and event.todo.assignee_email:
            # ... processing logic
    except Exception as e:
        logger.error(f"Error processing todo event for contact discovery: {e}")
```

### 3. Missing Vespa Schema for Todo Documents

**Issue**: While `TodoEvent` and `TodoData` models are implemented, there's no corresponding Vespa schema
**Current Status**: Todo events are processed but may not be properly indexed in Vespa
**Required Work**: Create `todo_document.sd` Vespa schema file

**Files to Create**:
- `vespa/schemas/todo_document.sd`

### 4. Document Chunking Service Memory Management

**File**: `services/common/services/document_chunking_service.py`
**Issue**: Memory usage tracking is implemented but cleanup mechanisms are not fully developed
**Current Status**: Chunks are cached but no automatic cleanup or memory pressure handling
**Required Work**: Implement memory pressure detection and automatic cache cleanup

### 5. Missing Integration Tests for Internal Tools

**Issue**: While internal tool event schemas are defined, comprehensive integration tests are missing
**Current Status**: Basic event models exist but end-to-end testing with internal tools is not implemented
**Required Work**: Create integration tests for LLM chats, shipment events, meeting polls, and bookings

**Files to Create**:
- `services/common/tests/test_internal_tool_integration.py`

### 6. Redis Reference Pattern Error Handling

**File**: `services/common/idempotency/redis_reference.py`
**Issue**: Some Redis operations lack comprehensive error handling and retry logic
**Current Status**: Basic error handling exists but may not handle all Redis failure scenarios
**Required Work**: Implement retry logic, circuit breaker pattern, and comprehensive error handling

### 7. Subscription Configuration Validation

**File**: `services/common/config/subscription_config.py`
**Issue**: While validation methods exist, runtime validation during service startup is not implemented
**Current Status**: Configuration is validated but services don't verify their subscriptions exist
**Required Work**: Implement runtime subscription validation and auto-creation if missing

### 8. Missing Monitoring and Alerting

**Issue**: While the architecture is implemented, production monitoring and alerting are not in place
**Current Status**: Basic logging exists but no metrics collection, dashboards, or alerting
**Required Work**: Implement Prometheus metrics, Grafana dashboards, and alerting rules

**Components to Implement**:
- Metrics collection for event processing rates
- Error rate monitoring and alerting
- Subscription lag monitoring
- Redis performance metrics
- Vespa indexing performance metrics

### 9. Backward Compatibility Layer

**Issue**: While deprecated methods exist, there's no comprehensive backward compatibility layer
**Current Status**: Old event types are marked as deprecated but may still be used in some services
**Required Work**: Implement feature flags and gradual migration strategy

**Components to Implement**:
- Feature flag system for gradual rollout
- Event type compatibility layer
- Migration validation tools
- Rollback mechanisms

### 10. Performance Testing and Optimization

**Issue**: While functional tests exist, performance testing under load is not implemented
**Current Status**: Basic integration tests pass but no performance benchmarks
**Required Work**: Implement load testing, performance profiling, and optimization

**Components to Implement**:
- Load testing scripts for event publishing
- Consumer performance benchmarks
- Redis performance testing
- Vespa indexing performance testing
- Memory usage profiling

### 11. Security Hardening

**Issue**: Basic security exists but production-grade security measures are not fully implemented
**Current Status**: Basic authentication and authorization exist
**Required Work**: Implement comprehensive security measures

**Components to Implement**:
- Event payload encryption
- Redis connection encryption
- Pub/Sub message encryption
- Audit logging for all operations
- Rate limiting and DDoS protection

### 12. Disaster Recovery and Backup

**Issue**: No disaster recovery procedures or backup strategies are implemented
**Current Status**: Basic error handling exists but no recovery mechanisms
**Required Work**: Implement comprehensive disaster recovery

**Components to Implement**:
- Event replay mechanisms
- Data backup strategies
- Service recovery procedures
- Cross-region failover
- Data consistency validation tools

## Priority Order for Addressing Deferred Work

1. **High Priority** (Production Blocking):
   - Todo Vespa schema implementation
   - Idempotency service cleanup implementation
   - Missing integration tests for internal tools

2. **Medium Priority** (Production Ready but Needs Improvement):
   - Document chunking memory management
   - Redis reference pattern error handling
   - Subscription configuration validation

3. **Low Priority** (Nice to Have):
   - Performance testing and optimization
   - Security hardening
   - Disaster recovery and backup
   - Backward compatibility layer
   - Monitoring and alerting (covered in Phase 8)

## Estimated Effort

- **High Priority Items**: 2-3 days
- **Medium Priority Items**: 3-5 days  
- **Low Priority Items**: 1-2 weeks
- **Total Additional Effort**: 2-3 weeks

## Recommendations

1. **Immediate**: Address high priority items before production deployment
2. **Short Term**: Complete medium priority items within 1-2 weeks
3. **Long Term**: Plan low priority items for future sprints
4. **Documentation**: Update this task list as items are completed
