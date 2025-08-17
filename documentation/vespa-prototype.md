### Vespa Prototype Design (Local Streaming Mode, Hybrid Search)

This document proposes a prototype to demonstrate using Vespa for unified search across a user’s emails, calendar events, contacts, and files (docs in Microsoft OneDrive and a test Gmail account). The goal is to ingest data per user, index in a local Vespa instance configured for streaming mode, and showcase hybrid retrieval (lexical + vector) over normalized content and metadata.

The prototype must not change production data and should operate on demo/test accounts only.

### Objectives

- Show end-to-end ingestion from existing services:
  - Emails and threads via `services/office/api/email.py` (Google + Microsoft)
  - Calendar events via `services/office/api/calendar.py` (Google + Microsoft)
  - Files via `services/office/api/files.py` (Google Drive + Microsoft OneDrive)
  - Contacts via new or extended Office endpoints (Google People API + Microsoft Graph People/Contacts)
- Index into a local Vespa cluster in streaming mode with strict per-user partitioning and isolation.
- Demonstrate hybrid retrieval that returns the most relevant emails and calendar events for a free-text query, with optional filters and facets.
- Make a clear decision on content normalization for emails (text vs HTML vs HTML→Markdown) and apply consistently across types.
- Provide a reproducible demo dataset seeding plan for both Microsoft and Google test accounts.

### Non-Goals (for the prototype)

- Not replacing Pinecone in production.
- Not building a full multi-tenant Vespa cloud deployment.
- Not implementing full security hardening beyond demo scope.

### High-Level Architecture

- Data sources: Office Service fronting Microsoft Graph and Google APIs.
- Ingestion workers: Pull from Office endpoints, normalize content, enrich with metadata, and feed documents to Vespa via HTTP Document API.
- Vespa cluster: Single-node local instance in streaming search mode. Documents are partitioned by user.
- Query path: A simple query service or script sends hybrid queries to Vespa, always scoping by user.

### Data Model (conceptual)

Each indexed item is a “document” with common fields and type-specific fields. Avoid schema drift by maintaining a normalized superset where absent fields are empty.

- Core fields
  - user_id: external auth user identifier used across services
  - doc_id: unique ID within the user’s partition; should be stable and derivable from provider and original object ID
  - provider: google or microsoft
  - source_type: email, email_thread, calendar_event, file, contact
  - title: subject (email), summary (calendar), file name (file), full name (contact)
  - search_text: canonical plain-text body used for BM25 and embeddings (see normalization)
  - text_format: one of text, html, markdown
  - created_at, updated_at: ISO timestamps
  - tags: string list for quick filtering (labels, categories, folders)

- Email-specific
  - from, to, cc, bcc: normalized address lists
  - thread_id and message_id (original provider IDs preserved)
  - sent_time

- Calendar-specific
  - start_time, end_time, timezone
  - attendees (emails + roles)
  - location

- File-specific
  - mime_type, size_bytes
  - drive_path or folder_id
  - optional extracted_text (if we add text extraction later)

- Contact-specific
  - primary_email, other_emails
  - phones
  - org, title

Notes:

- For streaming mode partitioning, include user_id in doc_id to ensure stable routing. For example, use a prefix pattern that guarantees all docs for a user share a consistent partitioning key.
- Keep original provider IDs for traceability and potential deep links back to Microsoft/Google.

### Content Normalization Strategy (emails in particular)

- Preferred order for emails
  - Use text/plain part if present and non-trivial.
  - Otherwise, convert HTML to Markdown using a high-fidelity conversion that preserves links, list semantics, and simple tables; strip tracking pixels, scripts, styles.
  - As fallback, convert HTML to plain text if Markdown introduces excessive noise for the index.

- Why HTML→Markdown can be preferable
  - Retains semantic structure with minimal noise compared to raw HTML.
  - Improves snippet quality and BM25 matching versus flattened plain text in some cases.
  - More consistent across providers than relying on text/plain, which can be missing or poorly formatted.

- Store both the original form (e.g., body_html) and the normalized search_text. Only search_text participates in BM25 and embeddings. Keep the original for UI rendering or future use.

### Vespa Mode Selection and Partitioning

- Use streaming search mode for the prototype because
  - Simple per-user partitioning by doc_id, good for isolation and easy teardown.
  - Fast feed with minimal indexing overhead during ingestion trials.
  - Simplifies delete-all-for-user operations by filtering on partition keys.

- Partitioning key
  - Derive doc_id so that all documents for a given user share a stable key prefix or grouping based on user_id.
  - All queries must include a strict user_id filter to avoid cross-tenant leakage.

### Hybrid Retrieval Plan

- Query features
  - Required: user_id filter; optional filters by source_type, date ranges, label/folder, provider.
  - Free-text query mapped to both keyword terms and vector embedding.
  - Hybrid scoring: combine BM25-like lexical score on search_text with ANN similarity on embeddings.

- Ranking blending
  - Weighted linear combination of lexical score and vector similarity.
  - Early exit top-k on ANN then rerank using the blend to ensure text relevance.
  - Optional freshness boost for emails and events (decay by age) and attendance/participant boosts if the query contains people names or emails.

- Facets and metadata filtering
  - source_type facets to demo mixed results
  - date range quick-filters for calendar/events and emails
  - provider facets for debugging and transparency

### Ingestion Flow

- Source discovery and fetch
  - Emails: use Office unified endpoints to list messages and threads, with include_body where available.
  - Calendar: use Office unified events endpoint with time windows.
  - Files: use Office files endpoint to list OneDrive/Drive files. For the prototype, index metadata and titles; optional text extraction is a stretch goal.
  - Contacts: add minimal Office contacts endpoint(s) or a direct client wrapper for Google People and Microsoft Graph Contacts/People.

- Normalization and enrichment
  - Build search_text using the normalization strategy above for body content.
  - Extract named entities and participants (emails, person names) for additional fields and boosts.
  - Compute document-level vectors from search_text using our standard embedding model for consistency with existing RAG components.

- Feed into Vespa
  - Use the HTTP Document API to upsert documents with the fields above.
  - Idempotency via doc_id to avoid duplicates on re-runs.
  - Maintain a per-user ingestion cursor to support incremental updates (e.g., newest message timestamp, latest event sync token if available in Office providers).

- Deletion and re-indexing
  - Provide a per-user wipe by filtering all docs with the user’s partition key.
  - Support targeted deletes by provider object IDs when items are removed upstream.

### Demo Scenarios to Showcase

- Mixed results: “Quarterly planning doc and invites from last month” returning OneDrive files and related calendar events.
- Email relevance: “Travel receipt from Acme” returning the email and any attached file references.
- Person-centric: “Threads with Alex Chen about SOW” returning emails and the latest calendar event mentioning Alex.
- Time-scoped: “Meetings next week with finance” returning calendar events, with highlights from descriptions.

### Seeding Demo Data (Microsoft OneDrive and Outlook)

See the comprehensive seeding guide in `documentation/data-seeding.md` for end-to-end options, cleanup, and validation checklists.

- Accounts and scopes
  - Use a dedicated Microsoft 365 test tenant or a demo user with Mail.Read, Calendars.Read, Files.Read, and People.Read scopes.

- OneDrive documents
  - Create a demo folder hierarchy for projects and meetings; upload a curated set of docs (planning notes, SOWs, invoices, trip itineraries, and short PDFs or DOCX files).
  - Ensure file names and content include the entities referenced in demo queries (people, companies, dates).

- Emails and calendar
  - Seed a small set of realistic email threads, including HTML-heavy newsletters and transactional receipts.
  - Populate calendar with events that reference the same entities and documents.

- Contacts
  - Create or import a small address book that includes demo participants with consistent names and emails used in emails and events.

### Seeding Demo Data (Google Drive and Gmail)

See the comprehensive seeding guide in `documentation/data-seeding.md` for Google-specific import options (CSV/ICS), API usage, and cleanup.

- Test account
  - Use a dedicated Gmail test account separate from any personal or production data. Enable required OAuth scopes analogous to Microsoft.

- Gmail
  - Seed threads that mirror the Microsoft dataset themes to validate cross-provider normalization.
  - Include a mix of text/plain and HTML-only messages to validate normalization strategy.

- Google Drive
  - Upload a parallel set of documents with similar naming and content conventions.

- Google Contacts
  - Add contacts that match the demo people used across email and events.

### Privacy, Security, and Multi-Tenancy Considerations

- Always filter by user_id on both ingestion and query.
- Keep provider tokens and secrets out of logs; use existing `services/common` logging and API-key auth conventions when calling Office.
- Avoid indexing sensitive PII beyond what’s necessary for the demo. Consider hashing or redacting personal phone numbers in contacts.
- Support rapid teardown by user to leave no demo residue.

### Success Criteria

- Data from both Microsoft and Google sources flow into Vespa for at least one test user.
- A single free-text query returns mixed-type results (emails + events, optionally files and contacts) ranked sensibly by hybrid scoring.
- Demonstrable, deterministic scenarios where top results include documents seeded for the demo queries.
- End-to-end run is repeatable on a clean environment.

### Risks and Mitigations

- HTML noise in emails reduces lexical relevance
  - Mitigation: HTML→Markdown normalization and quote/boilerplate stripping.

- Sparse vectors for very short messages
  - Mitigation: lexical weight increased for messages under a length threshold.

- Streaming mode limitations for large-scale cross-user aggregation
  - Acceptable for prototype; future deployments can use indexed mode with global posting lists.

### Work Plan and Milestones

- Milestone 1: Vespa local environment and schema
  - Bring up a local Vespa in streaming mode with a document schema that supports core fields and embeddings.
  - Define per-user partitioning strategy and enforce user filter in all queries.

- Milestone 2: Ingestion from Office (emails, events, files)
  - Implement mappers from Office endpoints to the normalized document model.
  - Normalize content and compute embeddings for search_text.
  - Feed into Vespa; verify upserts and deletes.

- Milestone 3: Contacts ingestion (minimum viable)
  - Add an Office contacts endpoint or narrow client to fetch and normalize contacts.
  - Index contacts for person-centric queries and boosting.

- Milestone 4: Hybrid query path and ranking
  - Implement a simple query runner that issues hybrid queries to Vespa with user scoping and optional filters.
  - Tune blending weights and freshness boosts on a small validation set.

- Milestone 5: Demo dataset seeding and scripts
  - Prepare curated data in Microsoft and Google test accounts (documents, emails, events, contacts).
  - Validate that canonical demo queries return expected cross-type results.

- Milestone 6: Polishing
  - Add facets (source_type, provider, date) and snippets.
  - Produce a concise runbook for reproducing the demo.

### Alternate Plan: Mocked Providers or Direct Vespa Load

If provider auth, quota, or time constraints block end-to-end tests, use one of these alternatives to focus on Vespa schema, hybrid ranking, and user partitioning:

- Option A: Mock Google/Microsoft APIs while keeping the Office ingestion path
  - Approach
    - Run a lightweight mock server that implements the subset of Gmail/Graph endpoints used by `services/office` (messages, threads, events, files, contacts), serving deterministic JSON fixtures.
    - Or inject mocks at the HTTP client level (e.g., request interceptors or recorded fixtures) so Office’s normalization/mapping code runs unchanged.
    - Keep `user_id` flows intact; return provider-like IDs to preserve doc_id stability.
  - Pros
    - Validates our normalization, mapping, and ingestion logic end-to-end.
    - Deterministic, repeatable datasets; easy CI usage.
  - Cons
    - Requires building/maintaining fixtures and endpoint shims.
  - Success
    - Office endpoints produce normalized items; Vespa contains expected docs; canonical hybrid queries return the expected mixed-type results.

- Option B: Bypass providers and feed normalized test data directly to Vespa
  - Approach
    - Handcraft or generate a small set of normalized documents (emails, events, files, contacts) matching the schema in this doc.
    - Compute embeddings offline for `search_text` and include them in the feed payload.
    - POST to Vespa’s HTTP Document API; preserve `user_id` and `doc_id` conventions for partitioning and idempotency.
  - Pros
    - Fastest path to validate Vespa schema, hybrid ranking, facets, and user scoping.
    - No dependency on OAuth, quotas, or provider availability.
  - Cons
    - Skips exercising the Office ingestion and normalization code paths.
  - Success
    - With a minimal dataset (e.g., ~20–50 docs), hybrid queries reliably retrieve relevant emails and events; facets and freshness work as intended.

- When to choose which
  - Prefer Option A if we want to validate our Office ingestion logic and data shapes.
  - Prefer Option B if the goal is to quickly tune Vespa ranking and verify partitioning and query UX.

- Minimal datasets
  - Emails: 10–20 items across 2–3 projects/entities, mix of text/plain and HTML-normalized `search_text`.
  - Events: 6–10 items with attendees and time windows aligned to the email topics.
  - Files: 5–10 items with titles referencing the same entities; text extraction optional.
  - Contacts: 5–10 personas used throughout emails/events.

- Cleanup
  - Use `user_id` partitioning and a DEMO tag to bulk-delete all direct-fed docs.
  - Maintain a manifest of `doc_id`s for deterministic teardown.

### Open Questions

- Do we want to index attachments' text in the first iteration or limit files to metadata and file names?
- Should we include threads as first-class documents or denormalize last-message signals onto message docs?
- What embedding model do we standardize on for parity with existing `services/vector_db` usage, while keeping the prototype self-contained?

### Future Work: Document Chunking

The current prototype stores documents as single units with their full content in the `content` field. For improved search precision and better handling of long documents, implementing document chunking should be considered as future work.

#### Current Limitations
- **No automatic chunking**: Documents are stored as single units with entire content
- **Full-document search**: Queries search across entire documents without paragraph-level precision
- **Content truncation**: `search_text` is limited to 10,000 characters
- **No section targeting**: Cannot target specific paragraphs or sections within documents

#### Proposed Chunking Approach
- **Pre-processing**: Implement chunking logic before sending documents to Vespa
- **Chunked schemas**: Create paragraph-level fields or separate chunk documents
- **Chunk relationships**: Handle parent document references, chunk order, and metadata inheritance
- **Hybrid search**: Combine document-level and chunk-level search for better relevance

#### Benefits
- **Improved precision**: Target specific sections within long documents
- **Better relevance**: Rank results based on chunk-level matching
- **Enhanced snippets**: Generate more focused search result previews
- **Scalability**: Handle very long documents without content truncation

#### Implementation Considerations
- **Chunk size**: Determine optimal paragraph or sentence boundaries
- **Overlap strategy**: Consider overlapping chunks for context preservation
- **Metadata handling**: Preserve document-level metadata across chunks
- **Search coordination**: Coordinate search across document and chunk levels


