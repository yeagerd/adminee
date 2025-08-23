# Move Document Chunking to Vespa Loader Service

## Overview
Move the document chunking functionality from `services/common/` into the `services/vespa_loader` service, and simplify pubsub events to handle full documents with large payloads stored in Redis.

## Current State
- Document chunking models are in `services/common/models/document_chunking.py`
- Document chunking service is in `services/common/services/document_chunking_service.py`
- Document chunking tests are in `services/common/tests/test_document_chunking_service.py`
- Pubsub events include `DocumentFragmentData` and `DocumentFragmentEvent` for chunked documents
- Vespa loader service handles document ingestion and processing

## Target State
- Document chunking functionality moved to `services/vespa_loader`
- Pubsub events simplified to handle full documents
- Large document payloads stored in Redis instead of chunked events
- Cleaner separation of concerns between services

## Migration Checklist

### Phase 1: Analysis and Planning
- [ ] Audit current usage of `DocumentFragmentData` and `DocumentFragmentEvent` across services
- [ ] Identify all imports and dependencies on `document_chunking.py`
- [ ] Identify all imports and dependencies on `document_chunking_service.py`
- [ ] Review how vespa_loader currently processes documents
- [ ] Plan Redis storage strategy for large document payloads
- [ ] Design new simplified document event structure

### Phase 2: Create New Vespa Loader Structure
- [ ] Create `services/vespa_loader/models/` directory
- [ ] Move `document_chunking.py` to `services/vespa_loader/models/document_chunking.py`
- [ ] Create `services/vespa_loader/services/` directory
- [ ] Move `document_chunking_service.py` to `services/vespa_loader/services/document_chunking_service.py`
- [ ] Update import paths within the moved files
- [ ] Create `services/vespa_loader/services/document_chunking_service.py` for chunking logic
- [ ] Move chunking service logic from common to vespa_loader

### Phase 3: Move and Update Tests
- [ ] Create `services/vespa_loader/tests/` directory if it doesn't exist
- [ ] Move `test_document_chunking_service.py` to `services/vespa_loader/tests/test_document_chunking_service.py`
- [ ] Update test imports to use new vespa_loader paths
- [ ] Update test fixtures and mocks as needed
- [ ] Ensure all document chunking tests pass in new location
- [ ] Remove old test file from common services

### Phase 4: Update Vespa Loader Service
- [ ] Update `services/vespa_loader/document_factory.py` to use new chunking models
- [ ] Update `services/vespa_loader/ingest_service.py` to handle chunking internally
- [ ] Update `services/vespa_loader/vespa_client.py` to work with chunked documents
- [ ] Ensure vespa_loader can process full documents and create chunks internally
- [ ] Update vespa_loader tests to use new structure

### Phase 5: Simplify Pubsub Events
- [ ] Remove `DocumentFragmentData` from `services/common/events/document_events.py`
- [ ] Remove `DocumentFragmentEvent` from `services/common/events/document_events.py`
- [ ] Update `DocumentData` to handle full document content
- [ ] Remove chunking-related fields from document events
- [ ] Update `services/common/events/__init__.py` to remove fragment exports

### Phase 6: Implement Redis Storage Strategy
- [ ] Design Redis key structure for large document payloads
- [ ] Create Redis storage service for document content
- [ ] Update document events to reference Redis keys instead of content
- [ ] Implement document content retrieval from Redis
- [ ] Add Redis cleanup/expiration policies for document content

### Phase 7: Update Event Consumers
- [ ] Update vespa_loader pubsub consumer to handle full document events
- [ ] Update other services that consume document events
- [ ] Ensure document content can be retrieved from Redis when needed
- [ ] Update event processing to work with simplified document structure

### Phase 8: Update Tests and Documentation
- [ ] Update all tests that use `DocumentFragmentData` or `DocumentFragmentEvent`
- [ ] Update tests that import from `services/common/models/document_chunking`
- [ ] Update tests that import from `services/common/services/document_chunking_service`
- [ ] Update integration tests to work with new document flow
- [ ] Update API documentation and schemas
- [ ] Update service documentation

### Phase 9: Cleanup and Validation
- [ ] Remove old `services/common/models/document_chunking.py`
- [ ] Remove old `services/common/services/document_chunking_service.py`
- [ ] Remove old `services/common/tests/test_document_chunking_service.py`
- [ ] Remove any remaining chunking-related code from common service
- [ ] Run full test suite to ensure no regressions
- [ ] Validate document processing end-to-end
- [ ] Performance testing with large documents

### Phase 10: Deployment and Monitoring
- [ ] Deploy changes to staging environment
- [ ] Test document processing with real data
- [ ] Monitor Redis usage and performance
- [ ] Monitor document processing performance
- [ ] Deploy to production

## Technical Considerations

### Redis Storage Strategy
- Use consistent key naming: `doc:content:{document_id}`
- Set appropriate TTL for document content
- Consider compression for very large documents
- Implement cleanup policies

### Event Structure Changes
```python
# Before (chunked)
class DocumentFragmentEvent(BaseEvent):
    fragment: DocumentFragmentData

# After (full document)
class DocumentEvent(BaseEvent):
    document: DocumentData
    redis_content_key: str  # Reference to Redis-stored content
```

### Chunking Logic
- Move chunking logic to vespa_loader service
- Process full documents internally
- Create chunks for Vespa indexing
- Maintain chunk relationships for search

### Backward Compatibility
- Consider migration period for existing chunked documents
- Update any external consumers of document events
- Ensure no breaking changes to public APIs

## Benefits
- Cleaner separation of concerns
- Simplified pubsub event structure
- Better performance for large documents
- Reduced memory usage in event queues
- More focused vespa_loader service

## Risks
- Breaking changes to document event structure
- Need to migrate existing chunked documents
- Redis dependency for document storage
- Potential performance impact of Redis lookups

## Dependencies
- Redis infrastructure for document storage
- Vespa loader service updates
- Event consumer updates
- Test updates across multiple services
- Complete migration of chunking service and tests
