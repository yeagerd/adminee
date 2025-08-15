### Data Seeding Guide (Microsoft 365 and Google)

This guide outlines practical options to seed demo/test data for emails, calendar events, files, and contacts across Microsoft 365 and Google, to support local demos and the Vespa prototype. Use only demo tenants/accounts and avoid real customer data.

### TL;DR (Recommended Combo)

- Microsoft: Enable Microsoft 365 Developer Program Sample Data Pack → add a small curated layer via SMTP + OneDrive uploads; tag everything with a DEMO prefix.
- Google: Import Contacts (CSV) and Calendar (ICS) → upload a small Drive set → send a few SMTP-seeded emails; tag/prefix consistently.
- Size: Start with <300 total items per user; favor coherence over volume.

### Provider: Microsoft 365 (Outlook, OneDrive, Calendar, Contacts)

- Sample Data Packs
  - In a Microsoft 365 developer tenant, enable Sample Data Packs to instantly seed realistic mail, events, SharePoint/OneDrive content, and users.

- Microsoft Graph API
  - Use batch calls to create messages, threads, events, contacts, and upload or create files in OneDrive. Throttle and backoff for quotas.

- Imports and Clients
  - ICS import for calendar; CSV import for contacts; bulk OneDrive uploads via web or CLI.
  - SMTP seeding: send templated emails to the mailbox to generate realistic threads and categories.
  - IMAP import (Thunderbird/Outlook) for historical messages if needed.

### Provider: Google (Gmail, Drive, Calendar, Contacts)

- Google APIs
  - Gmail/Drive/Calendar/People APIs to programmatically create messages, files, events, and contacts (use batch where available).

- Imports and Clients
  - ICS import for calendar; CSV import for contacts; bulk uploads to Drive.
  - SMTP seeding to create threads; IMAP client import via Thunderbird for historical MBOX if needed.
  - Google Apps Script can generate Drive docs and send emails inside the account.

### Cross-Cutting Strategies

- Manual curation: Hand-upload a compact, high-signal set; create a few events and threads manually for realism.
- Synthetic generator: A script that creates personas, companies, and projects; emits coherent emails, events, and files referencing the same entities for stronger hybrid search.
- Use Office service endpoints where possible to keep auth/logging consistent; otherwise call provider APIs directly.
- Import small public templates (non-sensitive) to avoid crafting everything from scratch.

### Practical Tips

- Aim for 50–200 items per type with overlapping entities (people, companies, dates) to showcase hybrid search.
- Include both HTML-heavy and plain-text emails; vary recency for freshness signals.
- Keep all seeded content under a DEMO namespace/folder; use consistent subject/file/folder prefixes.

### Removal and Reset

- Label- and folder-based cleanup: Put all seeded items in DEMO-labeled folders/labels for bulk deletion.
- Maintain a manifest (CSV/JSON/DB) of created provider IDs to enable precise, idempotent cleanup.
- Provide a “wipe user” routine that deletes by tag/date range.

### Constraints and Scopes

- Mind API quotas and rate limits; use batching and exponential backoff.
- Ensure OAuth scopes: Microsoft (Mail.Read/Send, Calendars.ReadWrite, Files.Read, People.Read); Google analogs.
- Use consistent time zones and ensure every item has meaningful `title` and body content.

### Minimal Viable Plan (Per User)

- Seed 3–5 projects/entities; for each, create:
  - 5–10 emails (some HTML-only, some text/plain)
  - 3–5 calendar events (include attendees/locations)
  - 3–5 documents (PDF/DOCX/MD) with relevant titles
  - 3–5 contacts (names/emails used elsewhere)
- Suggested order: Contacts → Calendar → Files → Emails (emails reference people and docs).

### Stretch Options

- Add attachments that match email content; consider later text extraction.
- Create reply chains with quoted content to evaluate HTML→Markdown normalization.
- Include recurring calendar events and a few newsletters/receipts.

### Tracking and Verification

- Record all created object IDs, timestamps, and tags in a manifest.
- Smoke-test canonical queries (e.g., “SOW with Acme next week”) to confirm mixed-type retrieval.
- Ensure indexing captures `title` and normalized `search_text` for every item.

### Cleanup Plan

- Single command to delete items with DEMO prefixes/tags within a date window.
- Verify cleanup via provider UIs and a zero-result check in the index for DEMO tags.

### Security and Isolation

- Use dedicated demo tenants/accounts; never seed personal or production accounts.
- Avoid sensitive PII; keep personas professional and neutral.
- Store secrets only in the local dev environment; rotate after demos.

### Orchestration (Suggested Flow)

- One script or Make target that performs, in order:
  1) Contacts CSV import
  2) Calendar ICS import
  3) File uploads (Drive/OneDrive)
  4) SMTP email send (templates)
  5) Optional API-based fine-tuning (threads/events)
- Log all outcomes and update the manifest for reproducibility and cleanup.

### Validation and Success Metrics

- Maintain 5–10 canonical queries (e.g., “Travel receipts from July”, “Threads with Alex about onboarding”).
- Success: Mixed-type results (emails + events, optionally files/contacts) in top results with >80% precision for curated queries.
- Indexing and cleanup complete within a single session without manual recovery.

### Maintenance and Refresh

- Refresh monthly; rotate personas and entities; keep a small template pack for reseeding.
- Keep counts low but content rich; document exact scopes and steps.

### Risks and Contingencies

- HTML normalization can degrade newsletters; include a few to validate.
- IMAP imports can be slow; prefer API/SMTP for speed.
- If provider auth blocks progress, index locally generated synthetic documents to validate ranking and UI until auth is resolved.

### Example Validation Queries

- “SOW with Acme next week”
- “Travel receipts from July”
- “Threads with Alex Chen about onboarding”
- “Planning doc for Q3”

### Governance and Ownership

- Assign owner per provider (Microsoft/Google); coordinate timelines and cleanup responsibilities.
- Keep a short runbook and a manifest in a `demo-seed/` directory alongside templates.


