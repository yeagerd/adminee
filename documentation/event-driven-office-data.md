## Event-driven Office data architecture

This document describes the implemented event-driven architecture for both batch synchronization and real-time streaming of Office data (emails, calendars, contacts, documents, todos), aligned with existing Briefly services and code patterns under `services/`.

### Goals
- **Unified ingestion**: a consistent pipeline for batch sync and streaming updates across Microsoft and Google providers.
- **Loose coupling**: producers and consumers communicate via Pub/Sub topics; services scale independently.
- **Typed events**: use strongly-typed message schemas in `services.common.events.*` to standardize payloads and tracing metadata.
- **Idempotence & observability**: event correlation, structured logs, and safe retries.
- **Selective consumption**: downstream services subscribe only to data types they need.
- **Low-latency fan-out**: multiple downstream consumers (meetings, shipments, vespa loader, FE SSE notifier) consume relevant events.

### Existing building blocks
- `services/common/events/` defines typed events and a `BaseEvent` with tracing metadata.
- `services/common/pubsub_client.py` provides a shared publisher/consumer abstraction with tracing and logging and typed helpers like `publish_email_event`.
- `services/office/core/email_crawler.py` performs normalized retrieval from providers via the Office service's own internal APIs.
- `services/office/api/backfill.py` constructs `EmailEvent` batches and publishes to Pub/Sub.
- Topics used today (see demos and vespa loader):
  - `emails` (replaces `email-backfill` - all email events)
  - `calendars` (replaces `calendar-updates` - all calendar events)
  - `contacts` (replaces `contact-updates` - all contact events)
  - `word_documents` (new - Word document events)
  - `sheet_documents` (new - Excel/Sheet document events)
  - `presentation_documents` (new - PowerPoint/Presentation events)
  - `todos` (new - Todo and task events)

**Note**: The topic naming has been revised to be data-type focused, eliminating confusion between data types and operation types.

### High-level data flow
1) User connects an integration (Google or Microsoft)
- `services/user` persists the integration and issues provider tokens.
- Emits an internal action to trigger:
  - a backfill job request (enqueue to a job queue or call Office internal backfill start endpoint)
  - registration for streaming updates:
    - Microsoft: set up webhook subscription to Office service callback URL
    - Google: configure Google Pub/Sub push or pull subscription to Office's project/topic

2) Batch sync path
- A sync request handler (thin orchestrator) enqueues or directly calls the Office sync internal endpoint with parameters (user, provider, date range, batch size).
- The Office sync runner:
  - crawls normalized data in batches via `EmailCrawler` (and analogous calendar/contacts crawlers when implemented).
  - for each batch, builds a typed event, e.g. `EmailEvent`, and publishes to the appropriate data-type topic using `PubSubClient`.
  - includes `EventMetadata` with `correlation_id` (job id), `source_service`, and trace context.

3) Streaming path
- Office service maintains provider-specific streaming subscriptions:
  - Microsoft Graph change notifications → Office webhook endpoint → normalize → publish typed events to data-type topics.
  - Google: provider push/pull delivers deltas to an Office consumer task → normalize → publish typed events to data-type topics.

4) Fan-out to downstream services
- Consumers subscribe to the data-type topics they need:
  - Vespa Loader (`services/vespa_loader`): subscribes to all data types for indexing.
  - Meetings (`services/meetings`): subscribe to `calendars` only for meeting contexts and availability.
  - Shipments (`services/shipments`): subscribe to `emails` only for shipping event parsing.
  - Contact Discovery (`services/user`): subscribes to `emails`, `calendars`, `word_documents`, `sheet_documents`, `presentation_documents` for contact management.
  - FE Client SSE Notifier: subscribes to relevant data types for user notifications.

5) Content access pattern
- For large payloads or heavy content, producers can store the normalized document in Redis with a short TTL and place only a reference (key) plus essential metadata in the event. Consumers then fetch content from Redis by key, process, and ack.
- Current code already includes Redis helpers (`services/office/core/cache_manager.py`, `services/common/config_secrets.get_redis_url`) and widely configured `REDIS_URL`. For batch operations that may exceed Pub/Sub message size limits, prefer the Redis pointer model.

### Topics and event taxonomy

**Key principle**: Organize topics by **data type**, not by operation type. This enables selective consumption and clearer semantics.

#### Topic Structure
```
emails          # All email events (batch sync, incremental sync, real-time)
calendars       # All calendar events (batch sync, incremental sync, real-time)  
contacts        # All contact events (batch sync, incremental sync, real-time)
word_documents  # All Word document events (batch sync, incremental sync, real-time)
sheet_documents # All Excel/Sheet document events (batch sync, incremental sync, real-time)
presentation_documents # All PowerPoint/Presentation events (batch sync, incremental sync, real-time)
todos           # All todo and task events (batch sync, incremental sync, real-time)
```

#### Event Types
Each topic carries events that distinguish between operations and provide tracking information:

**Immutable data (emails, calendar events):**
```python
class EmailEvent(BaseEvent):
    data: EmailData
    operation: Literal["create"]  # emails can't be updated
    batch_id: Optional[str]      # for batch operations
    correlation_id: Optional[str] # for job tracking
    last_updated: datetime       # when the content was last modified
    sync_timestamp: datetime     # when we last synced this data
```

**Mutable data (contacts, documents, drafts):**
```python
class ContactEvent(BaseEvent):
    data: ContactData  
    operation: Literal["create", "update", "delete"]
    batch_id: Optional[str]      # for batch operations
    correlation_id: Optional[str] # for job tracking
    last_updated: datetime       # when the content was last modified
    sync_timestamp: datetime     # when we last synced this data
```

**Document events (Word, Sheet, Presentation):**
```python
class DocumentEvent(BaseEvent):
    data: DocumentData
    operation: Literal["create", "update", "delete"]
    batch_id: Optional[str]      # for batch operations
    correlation_id: Optional[str] # for job tracking
    last_updated: datetime       # when the content was last modified
    sync_timestamp: datetime     # when we last synced this data
```

**Todo events:**
```python
class TodoEvent(BaseEvent):
    data: TodoData
    operation: Literal["create", "update", "delete"]
    batch_id: Optional[str]      # for batch operations
    correlation_id: Optional[str] # for job tracking
    last_updated: datetime       # when the content was last modified
    sync_timestamp: datetime     # when we last synced this data
```

All events extend `BaseEvent` and include `metadata` (trace_id/span_id, correlation_id, user_id, source_service, source_version). Use typed events from `services.common.events.*` to ensure schema consistency.

### Service boundaries and responsibilities
- Office service (`services/office`)
  - Owns provider integrations, normalization, rate limiting, and batching.
  - Sync runner: crawls, chunks, emits typed events to data-type topics.
  - Streaming bridge: receives provider deltas (webhook/GCPPubSub), normalizes, emits typed events to data-type topics.
  - Optional: writes large payloads to Redis and publishes references.

- User service (`services/user`)
  - Manages user identities, integrations, tokens.
  - Triggers batch sync start and streaming subscriptions when an integration is created or refreshed.
  - **Contact Discovery Service**: Processes events from multiple sources to maintain email contact lists.

- Meetings service (`services/meetings`)
  - Subscribes to `calendars` only to update meeting models, availability, polls, and booking artifacts.

- Shipments service (`services/shipments`)
  - Subscribes to `emails` only to extract and upsert package and tracking state.

- Vespa Loader (`services/vespa_loader`)
  - Subscribes to all data-type topics and indexes normalized content. Uses batching and backpressure controls already implemented.
  - **Document Type Strategy**: Creates type-appropriate Vespa documents (EmailDocument, CalendarDocument, ContactDocument, etc.) while maintaining unified search capabilities.
  - Uses factory pattern to instantiate correct document type based on event data.

- FE Client SSE Notifier (thin service)
  - Subscribes to relevant data-type topics and pushes user-scoped signals to the frontend via SSE/WebSockets.

### Vespa Document Type Design

**Strategy**: Hybrid approach with unified base and type-specific extensions for optimal search and flexibility.

#### Document Structure
```python
class BaseVespaDocument(BaseEvent):
    id: str
    user_id: str
    type: Literal["email", "calendar", "contact", "document", "todo", "llm_chat", "shipment_event", "meeting_poll", "booking", "word_document", "word_fragment", "sheet_document", "sheet_fragment", "presentation_document", "presentation_fragment", "task_document"]
    provider: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_updated: datetime       # when the content was last modified
    sync_timestamp: datetime     # when we last synced this data
    metadata: Dict[str, Any]
    content_chunks: List[str]
    search_text: str

class EmailDocument(BaseVespaDocument):
    type: Literal["email"]
    subject: str
    body: str
    from_address: str
    to_addresses: List[str]
    thread_id: str
    # email-specific fields

class CalendarDocument(BaseVespaDocument):
    type: Literal["calendar"]
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    attendees: List[str]
    # calendar-specific fields

class LLMChatDocument(BaseVespaDocument):
    type: Literal["llm_chat"]
    conversation_id: str
    user_message: str
    assistant_response: str
    context: Dict[str, Any]
    # chat-specific fields

class ShipmentEventDocument(BaseVespaDocument):
    type: Literal["shipment_event"]
    package_id: str
    event_type: str
    location: str
    description: str
    # shipment-specific fields

class MeetingPollDocument(BaseVespaDocument):
    type: Literal["meeting_poll"]
    meeting_id: str
    poll_question: str
    poll_options: List[str]
    responses: Dict[str, str]
    # poll-specific fields

class BookingDocument(BaseVespaDocument):
    type: Literal["booking"]
    booking_id: str
    meeting_id: str
    slot_start: datetime
    slot_end: datetime
    attendee_email: str
    # booking-specific fields

class ContactDocument(BaseVespaDocument):
    type: Literal["contact"]
    display_name: str
    email_addresses: List[str]
    phone_numbers: List[str]
    company: Optional[str]
    job_title: Optional[str]
    # contact-specific fields

class TaskDocument(BaseVespaDocument):
    type: Literal["task_document"]
    title: str
    description: str
    due_date: Optional[datetime]
    priority: str
    status: str
    assignee: Optional[str]
    # task-specific fields

class WordDocument(BaseVespaDocument):
    type: Literal["word_document"]
    title: str
    content: str
    author: str
    last_modified_by: str
    word_count: int
    # word document-specific fields

class WordFragmentDocument(BaseVespaDocument):
    type: Literal["word_fragment"]
    parent_document_id: str
    fragment_index: int
    fragment_content: str
    page_range: Optional[Tuple[int, int]]
    section_heading: Optional[str]
    # fragment-specific fields for large documents

class SheetDocument(BaseVespaDocument):
    type: Literal["sheet_document"]
    title: str
    sheet_names: List[str]
    cell_data: Dict[str, Any]
    formulas: Dict[str, str]
    # spreadsheet-specific fields

class SheetFragmentDocument(BaseVespaDocument):
    type: Literal["sheet_fragment"]
    parent_document_id: str
    sheet_name: str
    fragment_range: str  # e.g., "A1:Z100"
    fragment_content: str
    # fragment-specific fields for large spreadsheets

class PresentationDocument(BaseVespaDocument):
    type: Literal["presentation_document"]
    title: str
    slide_count: int
    slide_content: List[str]
    presenter_notes: List[str]
    # presentation-specific fields

class PresentationFragmentDocument(BaseVespaDocument):
    type: Literal["presentation_fragment"]
    parent_document_id: str
    slide_number: int
    slide_content: str
    presenter_notes: Optional[str]
    # fragment-specific fields for individual slides

...
```

#### Benefits of This Approach
- **Type-appropriate fields**: Each document type has relevant fields (no `from_address` for contacts)
- **Unified search**: Cross-type queries work seamlessly
- **Flexible indexing**: Can optimize per document type while maintaining unified pipeline
- **Clean event handling**: Vespa consumer uses factory pattern to create appropriate document types
- **Future extensibility**: Easy to add new document types (sheets, presentations, etc.)
- **Internal tool integration**: LLM chats, shipment events, meeting polls, and bookings become searchable
- **Practical tracking**: `last_updated` and `sync_timestamp` provide useful data freshness information

#### Implementation Details
- Vespa consumer processes events from unified topics (`emails`, `calendars`, `contacts`)
- Factory pattern determines document type based on event data
- All document types share common base fields for unified search
- Type-specific fields enable optimized search within each category
- Internal tools emit events that get converted to appropriate Vespa document types

### Document Chunking Strategy

**Strategy**: Large Office documents are chunked into searchable fragments while maintaining parent-child relationships.

#### Chunking Benefits
- **Search Relevance**: Smaller chunks enable more precise search results
- **Performance**: Faster indexing and search with manageable fragment sizes
- **Context Preservation**: Parent document metadata maintained across fragments
- **Scalability**: Handle documents of any size without Vespa document limits

#### Fragment Types and Relationships
```python
# Parent documents contain metadata and overview
class WordDocument(BaseVespaDocument):
    type: Literal["word_document"]
    title: str
    author: str
    total_pages: int
    # ... other metadata

# Fragments contain searchable content with parent reference
class WordFragmentDocument(BaseVespaDocument):
    type: Literal["word_fragment"]
    parent_document_id: str  # Links to parent WordDocument
    fragment_index: int      # Order within document
    fragment_content: str    # Searchable text chunk
    page_range: Optional[Tuple[int, int]]
    section_heading: Optional[str]
```

#### Chunking Rules
- **Word Documents**: Chunk by sections, pages, or semantic boundaries (e.g., 1000 words)
- **Spreadsheets**: Chunk by sheet or logical ranges (e.g., data tables, formula sections)
- **Presentations**: Chunk by individual slides for granular search
- **Fragment Size**: Target 500-2000 words per fragment for optimal search performance

#### Search and Navigation
- **Fragment Search**: Users search within specific document sections
- **Parent Context**: Search results show fragment content with parent document title/author
- **Navigation**: Click-through from fragment to full document view
- **Aggregation**: Search can aggregate results across fragments of the same parent

### Email Contacts Management

**Strategy**: Maintain user-specific email contact lists for enhanced search relevance and contact discovery.

#### Contact Data Structure
```python
class EmailContact(BaseModel):
    user_id: str
    email_address: str
    display_name: str
    last_seen: datetime
    event_counts: Dict[str, int]  # {"email": 5, "calendar": 2, "document": 1}
    first_seen: datetime
    metadata: Dict[str, Any]
```

#### Contact Discovery Flow
1. **Email Processing**: Extract sender/recipient emails from email events
2. **Calendar Processing**: Extract attendee emails from calendar events  
3. **Document Processing**: Extract author/contributor emails from Word, Sheet, and Presentation documents
4. **Contact Service**: Maintains contact list with event type counters and last_seen timestamps

#### Contact Service Responsibilities
- **Location**: Can be in `services/user` (user data) or `services/office` (office data)
- **Event Processing**: Subscribes to `emails`, `calendars`, `word_documents`, `sheet_documents`, `presentation_documents` topics
- **Contact Updates**: Emits contact update events when new contacts discovered or existing ones updated
- **Vespa Integration**: Triggers Vespa updates when contact relevance changes significantly

#### Vespa Integration Strategy
- **Contact Documents**: Create `ContactDocument` in Vespa for each email contact
- **Search Relevance**: Use `last_seen` and event counts for ranking
- **Update Triggers**: Update Vespa when:
  - New contact discovered
  - `last_seen` changes significantly (e.g., >7 days)
  - Event counts change substantially
  - Contact metadata updates

#### Benefits
- **Enhanced Search**: "John" searches rank by recency and interaction frequency
- **Contact Discovery**: Users discover contacts they interact with across all tools
- **Unified Contact View**: Single source of truth for email contacts across services
- **Search Optimization**: Vespa can optimize for contact-specific queries

### Sequence of operations
1. Integration connected
   - User service persists integration, schedules batch sync start and streaming subscription creation.
2. Batch sync job published
   - Sync orchestrator (thin) enqueues/requests sync through Office internal API with job parameters.
3. Office crawls and publishes
   - Office sync runner produces typed events to data-type topics (e.g., `EmailEvent` to `emails`), with correlation_id = sync job id.
4. Consumers process and ack
   - Each consumer independently processes events; if using Redis references, they fetch payloads by key, process, and ack. Failures can `nack` for retry.
5. Streaming continues
   - Office streaming bridge publishes events to data-type topics for low-latency deltas. Consumers handle idempotently.

### Redis usage pattern
- Write pattern (producer):
  - Normalize document(s); serialize and write to Redis with key `office:{user_id}:{doc_type}:{doc_id}` and TTL (e.g., 24h) or no TTL for batch sync windows.
  - Publish event with key references and essential metadata (sizes, types, counts).
- Read pattern (consumer):
  - On event, fetch by key(s); if missing, optionally fetch from Office internal API as fallback; process and ack.
- When to embed vs reference:
  - If batch or item fits under Pub/Sub limits and downstream prefers direct payload, embed typed data.
  - If events risk exceeding size or contain heavy bodies/attachments, reference via Redis.

### Error handling, idempotence, and retries
- All events include IDs (`email.id`, `calendar.event.id`, etc.) and `user_id` to enable consumer-level idempotence keys.
- On transient failures, consumers `nack` to trigger retry; use dead-letter topics for poison messages.
- Include `correlation_id` for batch sync jobs to aggregate metrics and trace.
- Keep consumers stateless; track progress in their own stores if necessary.

### Idempotency Implementation

**Strategy**: Comprehensive idempotency system using SHA-256 hashed keys and Redis-backed reference patterns for reliable event processing.

#### Idempotency Key Generation
```python
class IdempotencyKeyGenerator:
    @staticmethod
    def generate_email_key(event: EmailEvent) -> str:
        # For emails, use provider_message_id + user_id as the base
        base_key = f"{event.provider}:{event.email.provider_message_id}:{event.user_id}"
        
        # For mutable data, include updated_at timestamp
        if event.operation in ["update", "delete"] and event.last_updated:
            base_key += f":{int(event.last_updated.timestamp())}"
        
        # For batch operations, include batch_id
        if event.batch_id:
            base_key += f":{event.batch_id}"
        
        return IdempotencyKeyGenerator._hash_key(base_key)
```

#### Idempotency Strategies by Data Type
- **Immutable data (emails, calendar events)**: Use `provider_message_id` + `user_id` as idempotency key
- **Mutable data (contacts, documents, drafts)**: Use `provider_message_id` + `user_id` + `updated_at` timestamp
- **Batch operations**: Include `batch_id` + `correlation_id` for job tracking

#### Redis Reference Pattern
The system implements a shared library for Redis key generation and management:

```python
class RedisReferencePattern:
    KEY_PATTERNS = {
        "office": "office:{user_id}:{doc_type}:{doc_id}",
        "email": "email:{user_id}:{provider}:{doc_id}",
        "calendar": "calendar:{user_id}:{provider}:{doc_id}",
        "contact": "contact:{user_id}:{provider}:{doc_id}",
        "document": "document:{user_id}:{provider}:{doc_id}",
        "todo": "todo:{user_id}:{provider}:{doc_id}",
        "idempotency": "idempotency:{key}",
        "batch": "batch:{batch_id}:{correlation_id}",
        "fragment": "fragment:{parent_doc_id}:{fragment_id}",
    }
    
    TTL_SETTINGS = {
        "office": 86400 * 7,  # 7 days
        "idempotency": 86400,  # 24 hours
        "batch": 86400 * 3,    # 3 days
        "fragment": 86400 * 30, # 30 days
    }
```

#### Idempotency Service
High-level service that orchestrates idempotency checks for event and batch processing:

```python
class IdempotencyService:
    def process_event_with_idempotency(
        self,
        event: Union[EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent],
        processor_func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        # Generate idempotency key
        # Check if already processed
        # Store processing status
        # Execute processor function
        # Update with results
```

#### Benefits
- **Reliable Processing**: Events are processed exactly once, even with retries
- **Performance**: Redis-backed storage enables fast idempotency checks
- **Flexibility**: Different strategies for different data types
- **Monitoring**: Full visibility into processing status and retry patterns
- **Scalability**: Stateless design enables horizontal scaling

### Consumer filtering and selective consumption
- **Vespa Loader**: Subscribes to all data types (`emails`, `calendars`, `contacts`, `word_documents`, `word_fragments`, `sheet_documents`, `sheet_fragments`, `presentation_documents`, `presentation_fragments`, `task_documents`, `todos`) for comprehensive indexing
- **Meetings**: Subscribes to `calendars` only - no need for emails, contacts, or other data types
- **Shipments**: Subscribes to `emails` only - parses shipping events from email content
- **Contact Service**: Subscribes to `emails`, `calendars`, `word_documents`, `sheet_documents`, `presentation_documents` to maintain email contact lists
- **FE SSE**: Subscribes to relevant data types based on user preferences and notification settings

This selective consumption model:
- Reduces unnecessary message processing for domain-specific services
- Enables independent scaling per data type
- Simplifies consumer logic and reduces resource usage
- Makes debugging and monitoring more focused

### Security and tenancy
- Do not place PII beyond what downstream strictly needs into event bodies; prefer Redis references.
- Topic names are shared; per-tenant filtering is performed by the consumer using `user_id` in the payload or key.
- Use service-to-service auth and network policies for Office internal APIs and webhooks.

### Deployment model: serverless vs Cloud Run (or long-lived services)
- Good fits for thin serverless functions:
  - Sync orchestrator: receives integration-created events and calls Office internal sync start endpoint. Stateless, bursty.
  - SSE Notifier: small subscribers that bridge Pub/Sub → SSE/WebSocket can be serverless if they don’t hold long-lived connections; otherwise a lightweight Cloud Run.
  - Provider webhook adapters for Microsoft (if minimal logic before handing off to Office service).
- Good fits for Cloud Run/long-lived services:
  - Office sync runner and streaming bridge: sustained throughput, batching, rate limiting, and complex normalization.
  - Vespa loader consumer: parallel batch processing and indexing.
  - Meetings and Shipments consumers: may require DB transactions and stable scaling profiles.

### Sync service: separate service vs part of Office
- Recommendation: keep batch sync as part of the Office service.
  - Pros: shared normalization, one code path for provider adapters, reuse of settings and caching, simpler ownership.
  - Cons: larger service scope. Mitigation: keep sync as a dedicated module (`api/backfill.py`, `core/email_crawler.py`) with clear interfaces.
- Consider a separate thin orchestrator (serverless) that just triggers Office sync and monitors progress by calling internal endpoints.

### Observability and ops
- Use `PubSubClient` tracing hooks to propagate trace/span IDs; `BaseEvent` carries trace context.
- Emit structured logs with job IDs, message IDs, batch sizes, and user IDs.
- Per-topic subscriptions per consumer (e.g., `vespa-loader-email-backfill`) enable isolated scaling and troubleshooting.
- Provide `setup_pubsub.py` convenience to create topics locally and in CI.

### Topic and subscription naming
- Topics (canonical):
  - `emails` (all email events)
  - `calendars` (all calendar events)
  - `contacts` (all contact events)
  - `word_documents` (all Word document events)
  - `sheet_documents` (all Excel/Sheet document events)
  - `presentation_documents` (all PowerPoint/Presentation events)
  - `todos` (all todo and task events)
- Subscription names (by consumer):
  - Vespa: `vespa-loader-emails`, `vespa-loader-calendars`, `vespa-loader-contacts`, `vespa-loader-word-documents`, `vespa-loader-sheet-documents`, `vespa-loader-presentation-documents`, `vespa-loader-todos`
  - Contact Discovery: `contact-discovery-emails`, `contact-discovery-calendars`, `contact-discovery-word-documents`, `contact-discovery-sheet-documents`, `contact-discovery-presentation-documents`
  - Meetings: `meetings-calendars`
  - Shipments: `shipments-emails`
  - SSE: `client-sse-emails`, `client-sse-calendars`, etc.

**Note**: All subscription names follow the pattern `{service-prefix}-{topic-name}` for consistency and easy identification.

### Open questions and near-term improvements
- ~~Event type consolidation: migrate from `EmailBackfillEvent` to `EmailEvent` with `sync_type` field for cleaner semantics.~~ ✅ **COMPLETED**
- ~~Redis reference mode: introduce a shared small library to generate keys, set TTLs, and include reference envelopes in events.~~ ✅ **COMPLETED**
- ~~Calendar/contacts sync: mirror the email sync approach with typed events and shared crawler abstraction.~~ ✅ **COMPLETED**
- ~~Quotas and batch sizing: expose batch sizes via settings per consumer; align with provider limits.~~ ✅ **COMPLETED**
- **Testing and Validation**: ✅ **COMPLETED** - Comprehensive test suite covering all aspects of the new architecture
- **Documentation**: ✅ **COMPLETED** - Updated documentation reflecting the implemented architecture
- **Deployment Guides**: Update deployment guides to reflect new topic names and subscription patterns
- **Monitoring and Observability**: Implement monitoring dashboards for the new event-driven architecture

### Appendix: Key code references
- Typed events: `services/common/events/*.py`
- Publisher: `services/common/pubsub_client.py`
- Office sync API: `services/office/api/backfill.py`
- Office crawler: `services/office/core/email_crawler.py`
- Vespa consumer: `services/vespa_loader/pubsub_consumer.py`
- Demo topic setup: `services/demos/setup_pubsub.py`
- **Idempotency System**: `services/common/idempotency/*.py`
- **Subscription Configuration**: `services/common/config/subscription_config.py`
- **Contact Discovery Service**: `services/user/services/contact_discovery_service.py`
- **Document Chunking Service**: `services/common/services/document_chunking_service.py`
- **Integration Tests**: `services/common/tests/test_event_driven_architecture_integration.py`

### Consumer Subscription Management

**Strategy**: Centralized configuration for Pub/Sub subscription naming and management across all services.

#### Subscription Configuration
The system provides a centralized configuration for subscription naming and management:

```python
class SubscriptionConfig:
    SERVICE_PREFIXES = {
        "vespa_loader": "vespa-loader",
        "contact_discovery": "contact-discovery",
        "meetings": "meetings",
        "shipments": "shipments",
        "client_sse": "client-sse",
    }
    
    TOPIC_NAMES = {
        "emails": "emails",
        "calendars": "calendars",
        "contacts": "contacts",
        "word_documents": "word_documents",
        "sheet_documents": "sheet_documents",
        "presentation_documents": "presentation_documents",
        "todos": "todos",
    }
    
    SERVICE_SUBSCRIPTIONS = {
        "vespa_loader": {
            "emails": {
                "subscription_name": "vespa-loader-emails",
                "batch_size": 50,
                "ack_deadline_seconds": 120,
            },
            "calendars": {
                "subscription_name": "vespa-loader-calendars",
                "batch_size": 50,
                "ack_deadline_seconds": 120,
            },
            # ... other topics
        },
        "contact_discovery": {
            "emails": {
                "subscription_name": "contact-discovery-emails",
                "batch_size": 100,
                "ack_deadline_seconds": 60,
            },
            # ... other topics
        },
    }
```

#### Benefits
- **Consistent Naming**: Standardized subscription naming convention across all services
- **Centralized Configuration**: Single source of truth for subscription settings
- **Selective Consumption**: Services only subscribe to topics they need
- **Easy Maintenance**: Configuration changes in one place
- **Validation**: Built-in validation of subscription configurations
- **Monitoring**: Centralized subscription statistics and health checks


