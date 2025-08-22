## Event-driven backfill and streaming architecture for Office data

This document proposes a well-architected, event-driven flow for both backfill and streaming updates of Office data (email, calendar, contacts), aligned with existing Briefly services and code patterns under `services/`.

### Goals
- **Unified ingestion**: a consistent pipeline for backfill and streaming updates across Microsoft and Google providers.
- **Loose coupling**: producers and consumers communicate via Pub/Sub topics; services scale independently.
- **Typed events**: use strongly-typed message schemas in `services.common.events.*` to standardize payloads and tracing metadata.
- **Idempotence & observability**: event correlation, structured logs, and safe retries.
- **Low-latency fan-out**: multiple downstream consumers (meetings, shipments, vespa loader, FE SSE) consume the same new-data events.

### Existing building blocks
- `services/common/events/` defines typed events and a `BaseEvent` with tracing metadata.
- `services/common/pubsub_client.py` provides a shared publisher/consumer abstraction with tracing and logging and typed helpers like `publish_email_backfill`.
- `services/office/core/email_crawler.py` performs normalized retrieval from providers via the Office service’s own internal APIs.
- `services/office/api/backfill.py` constructs `EmailBackfillEvent` batches and publishes to Pub/Sub.
- Topics used today (see demos and vespa loader):
  - `email-backfill` (backfill batches of normalized emails)
  - `calendar-updates` (single or batch calendar updates)
  - `contact-updates` (single or batch contact updates)

We will keep these canonical topic names and expand the event taxonomy as needed.

### High-level data flow
1) User connects an integration (Google or Microsoft)
- `services/user` persists the integration and issues provider tokens.
- Emits an internal action to trigger:
  - a backfill job request (enqueue to a job queue or call Office internal backfill start endpoint)
  - registration for streaming updates:
    - Microsoft: set up webhook subscription to Office service callback URL
    - Google: configure Google Pub/Sub push or pull subscription to Office’s project/topic

2) Backfill path
- A backfill request handler (thin orchestrator) enqueues or directly calls the Office backfill internal endpoint `services/office/api/backfill.py:/internal/backfill/start` with parameters (user, provider, date range, batch size).
- The Office backfill runner:
  - crawls normalized data in batches via `EmailCrawler` (and analogous calendar/contacts crawlers when implemented).
  - for each batch, builds a typed event, e.g. `EmailBackfillEvent`, and publishes to `email-backfill` using `PubSubClient.publish_email_backfill`.
  - includes `EventMetadata` with `correlation_id` (job id), `source_service`, and trace context.

3) Streaming path
- Office service maintains provider-specific streaming subscriptions:
  - Microsoft Graph change notifications → Office webhook endpoint → normalize → publish typed `EmailUpdateEvent`/`CalendarUpdateEvent`/`ContactUpdateEvent` to update topics.
  - Google: provider push/pull delivers deltas to an Office consumer task → normalize → publish typed update events to the same topics (`email-backfill` is strictly for batches; per-item updates go to `*-updates`).

4) Fan-out to downstream services
- Consumers subscribe to the topics that match their domain:
  - Vespa Loader (`services/vespa_loader`): subscribes to `email-backfill`, `calendar-updates`, `contact-updates`; turns payloads into search documents and indexes.
  - Meetings (`services/meetings`): subscribe to `calendar-updates` to upsert meeting contexts, attendees, and possible availability impacts.
  - Shipments (`services/shipments`): subscribe to `email-backfill` and/or `email-updates` if we add one, parse shipping events from email content and update package tracking.
  - FE Client SSE Notifier: a thin service that listens to updates and pushes user-scoped notifications via SSE/WebSockets.

5) Content access pattern
- For large payloads or heavy content, producers can store the normalized document in Redis with a short TTL and place only a reference (key) plus essential metadata in the event. Consumers then fetch content from Redis by key, process, and ack.
- Current code already includes Redis helpers (`services/office/core/cache_manager.py`, `services/common/config_secrets.get_redis_url`) and widely configured `REDIS_URL`. For backfill batches that may exceed Pub/Sub message size limits, prefer the Redis pointer model.

### Topics and event taxonomy
- Email
  - `email-backfill`: carries `EmailBackfillEvent` (batch) for historical data.
  - `email-updates` (optional to formalize): carries `EmailUpdateEvent` for single create/update/delete during streaming.
- Calendar
  - `calendar-updates`: carries `CalendarUpdateEvent` and `CalendarBatchEvent`.
- Contacts
  - `contact-updates`: carries `ContactUpdateEvent` and `ContactBatchEvent`.

All events extend `BaseEvent` and include `metadata` (trace_id/span_id, correlation_id, user_id, source_service, source_version). Use typed events from `services.common.events.*` to ensure schema consistency.

### Service boundaries and responsibilities
- Office service (`services/office`)
  - Owns provider integrations, normalization, rate limiting, and batching.
  - Backfill runner: crawls, chunks, emits typed batch events to Pub/Sub.
  - Streaming bridge: receives provider deltas (webhook/GCPPubSub), normalizes, emits typed single-item update events.
  - Optional: writes large payloads to Redis and publishes references.

- User service (`services/user`)
  - Manages user identities, integrations, tokens.
  - Triggers backfill start and streaming subscriptions when an integration is created or refreshed.

- Meetings service (`services/meetings`)
  - Subscribes to `calendar-updates` to update meeting models, availability, polls, and booking artifacts.

- Shipments service (`services/shipments`)
  - Subscribes to email events to extract and upsert package and tracking state.

- Vespa Loader (`services/vespa_loader`)
  - Subscribes to all relevant topics and indexes normalized content. Uses batching and backpressure controls already implemented.

- FE Client SSE Notifier (thin service)
  - Subscribes to updates and pushes user-scoped signals to the frontend via SSE/WebSockets.

### Sequence of operations
1. Integration connected
   - User service persists integration, schedules backfill start and streaming subscription creation.
2. Backfill job published
   - Backfill orchestrator (thin) enqueues/requests backfill through Office internal API with job parameters.
3. Office crawls and publishes
   - Office backfill runner produces `EmailBackfillEvent` batches to `email-backfill` (and analogous calendar/contacts in future), with correlation_id = backfill job id.
4. Consumers process and ack
   - Each consumer independently processes events; if using Redis references, they fetch payloads by key, process, and ack. Failures can `nack` for retry.
5. Streaming continues
   - Office streaming bridge publishes `*-updates` for low-latency deltas. Consumers handle idempotently.

### Redis usage pattern
- Write pattern (producer):
  - Normalize document(s); serialize and write to Redis with key `office:{user_id}:{doc_type}:{doc_id}` and TTL (e.g., 24h) or no TTL for backfill windows.
  - Publish event with key references and essential metadata (sizes, types, counts).
- Read pattern (consumer):
  - On event, fetch by key(s); if missing, optionally fetch from Office internal API as fallback; process and ack.
- When to embed vs reference:
  - If batch or item fits under Pub/Sub limits and downstream prefers direct payload, embed typed data (already done for `EmailBackfillEvent`).
  - If events risk exceeding size or contain heavy bodies/attachments, reference via Redis.

### Error handling, idempotence, and retries
- All events include IDs (`email.id`, `calendar.event.id`, etc.) and `user_id` to enable consumer-level idempotence keys.
- On transient failures, consumers `nack` to trigger retry; use dead-letter topics for poison messages.
- Include `correlation_id` for backfill jobs to aggregate metrics and trace.
- Keep consumers stateless; track progress in their own stores if necessary.

### Security and tenancy
- Do not place PII beyond what downstream strictly needs into event bodies; prefer Redis references.
- Topic names are shared; per-tenant filtering is performed by the consumer using `user_id` in the payload or key.
- Use service-to-service auth and network policies for Office internal APIs and webhooks.

### Deployment model: serverless vs Cloud Run (or long-lived services)
- Good fits for thin serverless functions:
  - Backfill orchestrator: receives integration-created events and calls Office internal backfill start endpoint. Stateless, bursty.
  - SSE Notifier: small subscribers that bridge Pub/Sub → SSE/WebSocket can be serverless if they don’t hold long-lived connections; otherwise a lightweight Cloud Run.
  - Provider webhook adapters for Microsoft (if minimal logic before handing off to Office service).
- Good fits for Cloud Run/long-lived services:
  - Office backfill runner and streaming bridge: sustained throughput, batching, rate limiting, and complex normalization.
  - Vespa loader consumer: parallel batch processing and indexing.
  - Meetings and Shipments consumers: may require DB transactions and stable scaling profiles.

### Backfill service: separate service vs part of Office
- Recommendation: keep backfill as part of the Office service.
  - Pros: shared normalization, one code path for provider adapters, reuse of settings and caching, simpler ownership.
  - Cons: larger service scope. Mitigation: keep backfill as a dedicated module (`api/backfill.py`, `core/email_crawler.py`) with clear interfaces.
- Consider a separate thin orchestrator (serverless) that just triggers Office backfill and monitors progress by calling internal endpoints.

### Observability and ops
- Use `PubSubClient` tracing hooks to propagate trace/span IDs; `BaseEvent` carries trace context.
- Emit structured logs with job IDs, message IDs, batch sizes, and user IDs.
- Per-topic subscriptions per consumer (e.g., `vespa-loader-email-backfill`) enable isolated scaling and troubleshooting.
- Provide `setup_pubsub.py` convenience to create topics locally and in CI.

### Topic and subscription naming
- Topics (canonical):
  - `email-backfill`, `email-updates` (optional now, recommended for parity)
  - `calendar-updates`
  - `contact-updates`
- Subscription names (by consumer):
  - Vespa: `vespa-loader-email-backfill`, `vespa-loader-calendar-updates`, `vespa-loader-contact-updates`
  - Meetings: `meetings-calendar-updates`
  - Shipments: `shipments-email-backfill` and/or `shipments-email-updates`
  - SSE: `client-sse-email-updates`, etc.

### Open questions and near-term improvements
- Email updates topic: formalize `email-updates` with `EmailUpdateEvent` for streaming parity with calendar/contacts.
- Redis reference mode: introduce a shared small library to generate keys, set TTLs, and include reference envelopes in events.
- Calendar/contacts backfill: mirror the email backfill approach with typed batch events and shared crawler abstraction.
- Quotas and batch sizing: expose batch sizes via settings per consumer; align with provider limits.

### Appendix: Key code references
- Typed events: `services/common/events/*.py`
- Publisher: `services/common/pubsub_client.py`
- Office backfill API: `services/office/api/backfill.py`
- Office crawler: `services/office/core/email_crawler.py`
- Vespa consumer: `services/vespa_loader/pubsub_consumer.py`
- Demo topic setup: `services/demos/setup_pubsub.py`


