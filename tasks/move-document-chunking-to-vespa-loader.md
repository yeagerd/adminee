# Move Document Chunking to Vespa Loader Service

## Overview
Move the document chunking functionality from `services/common/` into the `services/vespa_loader` service, and simplify pubsub events to handle full documents with large payloads stored in Redis.

## Current State
- Document chunking models are in `services/common/models/document_chunking.py`
- Document chunking service is in `services/common/services/document_chunking_service.py`
- Document chunking tests are in `services/common/tests/test_document_chunking_service.py`
- Pubsub events include `DocumentFragmentData` and `DocumentFragmentEvent` for chunked documents
- Vespa loader service handles document ingestion and processing

## Current Vespa Loader Chunking State
- **VespaDocumentType** already has `content_chunks: Optional[List[str]]` field
- **Document Factory** creates documents with empty `content_chunks=[]` by default
- **No active chunking logic** - chunks field exists but is not populated
- **Content processing** happens in `content_normalizer.py` and `embeddings.py`
- **Document ingestion** is handled by `ingest_service.py` and `vespa_client.py`
- **Existing test infrastructure** for document processing and Vespa integration

## Phase 1 Analysis Results
- **DocumentFragmentData/Event Usage**: Only used in `services/common/events/` module
- **Document Chunking Dependencies**: 
  - `test_document_chunking_service.py` imports models and service
  - `test_event_driven_architecture_integration.py` imports service
  - No other services currently use chunking functionality
- **Vespa Loader Integration**: Already processes `DocumentEvent` and `DocumentData`
- **Current Document Structure**: `DocumentData.content` field holds full document content
- **Redis Strategy**: Store large content in Redis, reference via key in events
- **Simplified Events**: Remove fragment events, enhance `DocumentEvent` with Redis key

## Target State
- Document chunking functionality moved to `services/vespa_loader`
- Pubsub events simplified to handle full documents
- Large document payloads stored in Redis instead of chunked events
- Cleaner separation of concerns between services

## Migration Checklist

### Phase 1: Analysis and Planning
- [x] Audit current usage of `DocumentFragmentData` and `DocumentFragmentEvent` across services
- [x] Identify all imports and dependencies on `document_chunking.py`
- [x] Identify all imports and dependencies on `document_chunking_service.py`
- [x] Review how vespa_loader currently processes documents
- [x] Plan Redis storage strategy for large document payloads
- [x] Design new simplified document event structure

### Phase 2: Create New Vespa Loader Structure
- [x] Create `services/vespa_loader/models/` directory
- [x] Move `document_chunking.py` to `services/vespa_loader/models/document_chunking.py`
- [x] Create `services/vespa_loader/services/` directory
- [x] Move `document_chunking_service.py` to `services/vespa_loader/services/document_chunking_service.py`
- [x] Update import paths within the moved files
- [x] Integrate chunking service with existing `VespaDocumentType.content_chunks` field
- [x] Update `document_factory.py` to populate content_chunks using chunking service
- [x] Ensure chunking service works with existing vespa_loader infrastructure

### Phase 3: Move and Update Tests
- [ ] Create `services/vespa_loader/tests/` directory if it doesn't exist
- [ ] Move `test_document_chunking_service.py` to `services/vespa_loader/tests/test_document_chunking_service.py`
- [ ] Update test imports to use new vespa_loader paths
- [ ] Update test fixtures and mocks as needed
- [ ] Ensure all document chunking tests pass in new location
- [ ] Remove old test file from common services

### Phase 4: Update Vespa Loader Service
- [ ] Update `services/vespa_loader/document_factory.py` to populate `content_chunks` field
- [ ] Integrate chunking service into document creation pipeline
- [ ] Update `services/vespa_loader/ingest_service.py` to handle chunked documents
- [ ] Ensure `services/vespa_loader/vespa_client.py` properly indexes chunked content
- [ ] Update existing vespa_loader tests to work with new chunking functionality
- [ ] Leverage existing `content_normalizer.py` and `embeddings.py` for chunk processing

### Phase 5: Simplify Pubsub Events
- [ ] Remove `DocumentFragmentData` from `services/common/events/document_events.py`
- [ ] Remove `DocumentFragmentEvent` from `services/common/events/document_events.py`
- [ ] Update `DocumentData` to handle full document content
- [ ] Remove chunking-related fields from document events
- [ ] Update `services/common/events/__init__.py` to remove fragment exports
- [ ] Update `scripts/pubsub_manager.sh' to remove fragments

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

### Leveraging Existing Vespa Loader Infrastructure
- **VespaDocumentType.content_chunks**: Already exists and ready for chunk data
- **Content Normalizer**: Can be extended to process individual chunks
- **Embedding Generator**: Already handles content processing for search
- **Document Factory**: Has pipeline for creating Vespa-ready documents
- **Ingest Service**: Can be enhanced to handle chunked document ingestion
- **Vespa Client**: Already supports indexing with chunked content structure

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

### Integration with Existing Vespa Loader
```python
# Current VespaDocumentType already supports chunks
class VespaDocumentType:
    content_chunks: Optional[List[str]] = None  # Ready for chunk data
    
# Document Factory will be updated to populate chunks
def create_document_document(event: DocumentEvent) -> VespaDocumentType:
    # Use chunking service to create chunks
    chunks = chunking_service.chunk_document(
        document_id=event.document.id,
        content=event.document.content,
        document_type=event.document.type
    )
    
    return VespaDocumentType(
        # ... other fields ...
        content_chunks=[chunk.content for chunk in chunks.chunks]
    )
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
- **Leverages Existing Infrastructure**: Builds on vespa_loader's existing chunk support
- **Cleaner Separation of Concerns**: Moves chunking logic to appropriate service
- **Simplified Pubsub Event Structure**: Full documents instead of fragmented events
- **Better Performance**: Large documents stored in Redis, chunks created on-demand
- **Reduced Memory Usage**: Event queues no longer carry large chunked content
- **More Focused Services**: Common service focuses on events, vespa_loader handles processing
- **Existing Test Coverage**: vespa_loader already has comprehensive test infrastructure

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
