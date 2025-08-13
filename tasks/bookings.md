## Bookings (Calendar Slot Reservation) — Task List (MVP)

Scope: Implements all requirements in the PRD up to (but not including) the "Future concerns" section. Focus on evergreen booking links and one-time recipient links, core integrations (calendar, contacts, email), essential UI, configuration options, security/privacy, and API surface.

Conventions
- Keep tasks small and incremental
- Add tests for every new handler/util where practical
- Use feature flags or clearly scoped routes to avoid impacting existing flows

---

### 0. Scaffolding and Project Structure
- [x] Create frontend area for bookings
  - Path: `frontend/app/bookings/` (wizard, dashboard) and public page: `frontend/app/public/bookings/[token]/page.tsx`
  - Acceptance criteria:
    - Routing works for `/bookings` (authed) and `/public/bookings/[token]` (unauth)

 - [x] Prepare backend routes in meetings service
  - Add router module: `services/meetings/api/bookings.py`
  - Wire router in service startup (if using FastAPI include router under `/bookings`)
  - Acceptance criteria:
    - Health check route under `/bookings/health` returns 200

---

### 1. Data Models (Server)
- [x] Booking link models
  - Entities: `BookingLink` (evergreen), `OneTimeLink`, `BookingTemplate`, `Booking` (scheduled meeting), `AnalyticsEvent`
  - Fields (minimum):
    - BookingLink: id, owner_user_id, slug/uuid, is_active, settings (duration options, buffers, booking window, limits, timezone behavior), template_id, created_at, updated_at
    - OneTimeLink: id, booking_link_id (or owner_user_id), recipient_email, token, expires_at, status, created_at
    - BookingTemplate: id, owner_user_id, name, questions (JSON), email_followup_enabled, created_at, updated_at
    - Booking: id, link_id or one_time_link_id, start_at, end_at, attendee_email, answers (JSON), calendar_event_id, created_at
    - AnalyticsEvent: id, link_id, event_type (view, booked), occurred_at, referrer
  - Acceptance criteria:
    - SQLAlchemy/Pydantic (or project standard) models created and migratable
    - Migration added under `services/meetings/alembic/versions`

- [x] Migrations
  - Generate and apply initial migration for the above tables
  - Acceptance criteria:
    - Local DB migration succeeds and tables exist

---

### 2. Calendar Integration (Use existing integrations)
- [x] Availability check service
  - Service util to fetch busy/available blocks using existing Microsoft/Google clients
  - Inputs: user_id, date range, duration, buffers, business hours, limits
  - Acceptance criteria:
    - Given a time window, returns normalized free slot candidates

- [ ] Event creation util
  - Create calendar event in the owner’s connected calendar on booking
  - Include meeting details and description with Q&A answers
  - Acceptance criteria:
    - Returns calendar_event_id; event visible in owner’s calendar
    
- [x] Event creation util

---

### 3. Contacts Integration
- [x] Contact lookup
  - Auto-complete by email/name from Microsoft/Google contacts where available
  - Acceptance criteria:
    - Typing 3+ chars returns suggestions from connected provider(s)

- [x] Auto-create contact (new recipients)
  - If not found, create new contact record via existing integration when booking is confirmed
  - Acceptance criteria:
    - New contact appears in provider contacts after booking

---

### 4. Email Integration
- [x] Confirmation emails
  - Send confirmation to both parties after booking
  - Include calendar invite (ICS) or provider-native invite
  - Acceptance criteria:
    - Both recipient and owner receive a confirmation email with event details

- [x] Optional follow-up emails
  - If template has follow-up enabled, send a follow-up confirmation message
  - Acceptance criteria:
    - Follow-up only sent when `email_followup_enabled` is true

---

### 5. Public Booking Flow (Recipient)
- [x] Public page shell
  - `frontend/app/public/bookings/[token]/page.tsx` renders link details: title, duration choices, timezone awareness
  - Acceptance criteria:
    - Invalid/expired token → friendly error page

- [x] Availability display
  - Show available slots with timezone conversion
  - Acceptance criteria:
    - Changing timezone displays converted slots

- [x] Recipient form (from template)
  - Render dynamic questions from `BookingTemplate.questions`
  - Acceptance criteria:
    - Required questions enforced; minimal defaults applied

- [x] Submit booking
  - POST to API with chosen slot and answers
  - Acceptance criteria:
    - Success → confirmation screen; One-time link becomes inactive

---

### 6. Authenticated Booking Link Wizard (Owner)
- [x] Create evergreen link (stepper UI)
  - Steps: Basics → Availability → Duration/Buffer → Limits → Template → Review
  - Acceptance criteria:
    - Owner can save a new evergreen link; receives generated URL

- [x] Create one-time link (uses poll/slot picker)
  - Let owner select specific slots; generate recipient-specific tokenized URL
  - Acceptance criteria:
    - Generated URL expires on booking or timeout; status visible to owner

---

### 7. Management Dashboard (Owner)
- [ ] Links list
  - List all active/inactive links with quick actions (enable/disable, duplicate, edit)
  - Acceptance criteria:
    - Toggling active state reflects immediately in API and UI

- [ ] Bookings list and upcoming meetings view
  - Show bookings with date/time and recipient info; simple calendar-style view for upcoming
  - Acceptance criteria:
    - Bookings appear after creation; links to open calendar event

- [ ] Basic analytics
  - Track views and bookings per link; show simple counts and conversion rate
  - Acceptance criteria:
    - Visiting public page increments view count; successful booking increments bookings count; conversion displayed

---

### 8. API Endpoints (Server)
- [ ] POST `/bookings/links` — create evergreen link
- [ ] GET `/bookings/links` — list owner links
- [ ] GET `/bookings/links/{id}` — get link
- [ ] PATCH `/bookings/links/{id}` — update link settings
- [ ] POST `/bookings/links/{id}:duplicate` — duplicate link
- [ ] POST `/bookings/links/{id}:toggle` — enable/disable
- [ ] POST `/bookings/links/{id}/one-time` — create one-time link
- [ ] GET `/bookings/public/{token}` — public link metadata
- [ ] GET `/bookings/public/{token}/availability` — available slots
- [ ] POST `/bookings/public/{token}/book` — create booking
- [ ] GET `/bookings/links/{id}/analytics` — views/bookings
  - Acceptance criteria:
    - All endpoints return 2xx on success, validate inputs, and return errors with standard format

---

### 9. Configuration Options (Owner)
- [ ] Business hours per weekday
  - UI to set ranges per day; stored in link settings
- [ ] Holiday/vacation exclusions
  - Simple date list exclusion for MVP
- [ ] Duration presets and custom
  - 15m, 30m, 60m, 120m, custom
- [ ] Buffers before/after
  - Enforced in availability calculation
- [ ] Max meetings/day and week
  - Enforced in availability calculation
- [ ] Advance booking windows (min/max) and last-minute cutoff
  - Enforced in availability and submit validation
  - Acceptance criteria:
    - Availability respects all settings; booking submit rejects invalid times

---

### 10. Security and Privacy
- [ ] Token generation util
  - Cryptographically random tokens for public links; expirable for one-time links
  - Acceptance criteria:
    - Tokens are URL-safe; one-time tokens expire after booking/timeout

- [ ] Rate limiting and abuse protection
  - Rate limit public endpoints; add basic bot protection (e.g., simple challenge or provider-supported checks)
  - Acceptance criteria:
    - Excess requests return 429; logs indicate limited attempts

- [ ] Audit logging
  - Log link creation, updates, and booking events
  - Acceptance criteria:
    - Logs include who/when and action summary

---

### 11. UX/Polish
- [ ] Mobile-responsive public booking page
- [ ] Friendly error screens (expired link, no availability)
- [ ] Loading/skeleton states for availability fetches
  - Acceptance criteria:
    - Lighthouse/ basic responsive checks pass; no layout shift on load

---

### 12. Documentation and Tests
- [ ] API docs
  - Describe endpoints, auth, params, and examples
- [ ] Owner guide
  - Short README on creating links and sharing URLs
- [ ] Unit tests (server)
  - Models, availability util, booking creation, token utils
- [ ] Component tests (frontend)
  - Wizard steps render; public form validates; booking submit happy-path
  - Acceptance criteria:
    - CI passes; tests cover critical paths

---

### Nice-to-have (still within MVP if time allows)
- [ ] Calendar overlay (multiple calendars) in availability
- [ ] Template library (starter templates)

Out of scope for this doc: Items listed under PRD "Future concerns" section.


