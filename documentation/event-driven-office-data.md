## Event-driven Office data architecture

This document proposes a well-architected, event-driven flow for both batch synchronization and real-time streaming of Office data (emails, calendars, contacts, documents, todos), aligned with existing Briefly services and code patterns under `services/`.

### Goals
- **Unified ingestion**: a consistent pipeline for batch sync and streaming updates across Microsoft and Google providers.
- **Loose coupling**: producers and consumers communicate via Pub/Sub topics; services scale independently.
- **Typed events**: use strongly-typed message schemas in `services.common.events.*` to standardize payloads and tracing metadata.
- **Idempotence & observability**: event correlation, structured logs, and safe retries.
- **Selective consumption**: downstream services subscribe only to data types they need.
- **Low-latency fan-out**: multiple downstream consumers (meetings, shipments, vespa loader, FE SSE notifier) consume relevant events.

### Existing building blocks
- `services/common/events/` defines typed events and a `BaseEvent` with tracing metadata.
- `services/common/pubsub_client.py` provides a shared publisher/consumer abstraction with tracing and logging and typed helpers like `publish_email_backfill`.
- `services/office/core/email_crawler.py` performs normalized retrieval from providers via the Office service’s own internal APIs.
- `services/office/api/backfill.py` constructs `EmailBackfillEvent` batches and publishes to Pub/Sub.
- Topics used today (see demos and vespa loader):
  - `email-backfill` (backfill batches of normalized emails)
  - `calendar-updates` (single or batch calendar updates)
  - `contact-updates` (single or batch contact updates)

**Note**: The current topic naming mixes data types with operation types, which creates confusion. We'll revise this to be data-type focused.

### High-level data flow
1) User connects an integration (Google or Microsoft)
- `services/user` persists the integration and issues provider tokens.
- Emits an internal action to trigger:
  - a backfill job request (enqueue to a job queue or call Office internal backfill start endpoint)
  - registration for streaming updates:
    - Microsoft: set up webhook subscription to Office service callback URL
    - Google: configure Google Pub/Sub push or pull subscription to Office’s project/topic

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
documents       # All document events (batch sync, incremental sync, real-time)
todos           # All todo events (batch sync, incremental sync, real-time)
```

#### Event Types
Each topic carries events that distinguish between sync strategies and operations:

**Immutable data (emails, calendar events):**
```python
class EmailEvent(BaseEvent):
    data: EmailData
    sync_type: Literal["batch_sync", "incremental_sync", "real_time"]
    operation: Literal["create"]  # emails can't be updated
    batch_id: Optional[str]      # for batch operations
    correlation_id: Optional[str] # for job tracking
```

**Mutable data (contacts, documents, drafts):**
```python
class ContactEvent(BaseEvent):
    data: ContactData  
    sync_type: Literal["batch_sync", "incremental_sync", "real_time"]
    operation: Literal["create", "update", "delete"]
    batch_id: Optional[str]      # for batch operations
    correlation_id: Optional[str] # for job tracking
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

- Meetings service (`services/meetings`)
  - Subscribes to `calendars` only to update meeting models, availability, polls, and booking artifacts.

- Shipments service (`services/shipments`)
  - Subscribes to `emails` only to extract and upsert package and tracking state.

- Vespa Loader (`services/vespa_loader`)
  - Subscribes to all data-type topics and indexes normalized content. Uses batching and backpressure controls already implemented.

- FE Client SSE Notifier (thin service)
  - Subscribes to relevant data-type topics and pushes user-scoped signals to the frontend via SSE/WebSockets.

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

### Idempotency strategies by data type
- **Immutable data (emails, calendar events)**: Use `provider_message_id` + `user_id` as idempotency key
- **Mutable data (contacts, documents, drafts)**: Use `provider_message_id` + `user_id` + `updated_at` timestamp
- **Batch operations**: Include `batch_id` + `correlation_id` for job tracking

### Consumer filtering and selective consumption
- **Vespa Loader**: Subscribes to all data types (`emails`, `calendars`, `contacts`, `documents`, `todos`) for comprehensive indexing
- **Meetings**: Subscribes to `calendars` only - no need for emails, contacts, or other data types
- **Shipments**: Subscribes to `emails` only - parses shipping events from email content
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
  - `documents` (all document events)
  - `todos` (all todo events)
- Subscription names (by consumer):
  - Vespa: `vespa-loader-emails`, `vespa-loader-calendars`, `vespa-loader-contacts`, `vespa-loader-documents`, `vespa-loader-todos`
  - Meetings: `meetings-calendars`
  - Shipments: `shipments-emails`
  - SSE: `client-sse-emails`, `client-sse-calendars`, etc.

### Open questions and near-term improvements
- Event type consolidation: migrate from `EmailBackfillEvent` to `EmailEvent` with `sync_type` field for cleaner semantics.
- Redis reference mode: introduce a shared small library to generate keys, set TTLs, and include reference envelopes in events.
- Calendar/contacts sync: mirror the email sync approach with typed events and shared crawler abstraction.
- Quotas and batch sizing: expose batch sizes via settings per consumer; align with provider limits.

### Appendix: Key code references
- Typed events: `services/common/events/*.py`
- Publisher: `services/common/pubsub_client.py`
- Office sync API: `services/office/api/backfill.py`
- Office crawler: `services/office/core/email_crawler.py`
- Vespa consumer: `services/vespa_loader/pubsub_consumer.py`
- Demo topic setup: `services/demos/setup_pubsub.py`


