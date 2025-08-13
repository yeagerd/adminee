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
- [x] Links list
  - List all active/inactive links with quick actions (enable/disable, duplicate, edit)
  - Acceptance criteria:
    - Toggling active state reflects immediately in API and UI

- [x] Bookings list and upcoming meetings view
  - Show bookings with date/time and recipient info; simple calendar-style view for upcoming
  - Acceptance criteria:
    - Bookings appear after creation; links to open calendar event

- [x] Basic analytics
  - Track views and bookings per link; show simple counts and conversion rate
  - Acceptance criteria:
    - Visiting public page increments view count; successful booking increments bookings count; conversion displayed

---

### 8. API Endpoints (Server)
- [x] POST `/bookings/links` — create evergreen link
- [x] GET `/bookings/links` — list owner links
- [x] GET `/bookings/links/{id}` — get link
- [x] PATCH `/bookings/links/{id}` — update link settings
- [x] POST `/bookings/links/{id}:duplicate` — duplicate link
- [x] POST `/bookings/links/{id}:toggle` — enable/disable
- [x] POST `/bookings/links/{id}/one-time` — create one-time link
- [x] GET `/bookings/public/{token}` — public link metadata
- [x] GET `/bookings/public/{token}/availability` — available slots
- [x] POST `/bookings/public/{token}/book` — create booking
- [x] GET `/bookings/links/{id}/analytics` — views/bookings
  - Acceptance criteria:
    - All endpoints return 2xx on success, validate inputs, and return errors with standard format

---

### 9. Configuration Options (Owner)
- [x] Business hours per weekday
  - UI to set ranges per day; stored in link settings
- [x] Holiday/vacation exclusions
  - Simple date list exclusion for MVP
- [x] Duration presets and custom
  - 15m, 30m, 60m, 120m, custom
- [x] Buffers before/after
  - Enforced in availability calculation
- [x] Max meetings/day and week
  - Enforced in availability calculation
- [x] Advance booking windows (min/max) and last-minute cutoff
  - Enforced in availability and submit validation
  - Acceptance criteria:
    - Availability respects all settings; booking submit rejects invalid times

---

### 10. Security and Privacy
- [x] Token generation util
  - Cryptographically random tokens for public links; expirable for one-time links
  - Acceptance criteria:
    - Tokens are URL-safe; one-time tokens expire after booking/timeout

- [x] Rate limiting and abuse protection
  - Rate limit public endpoints; add basic bot protection (e.g., simple challenge or provider-supported checks)
  - Acceptance criteria:
    - Excess requests return 429; logs indicate limited attempts

- [x] Audit logging
  - Log link creation, updates, and booking events
  - Acceptance criteria:
    - Logs include who/when and action summary

---

### 11. UX/Polish
- [x] Mobile-responsive public booking page
- [x] Friendly error screens (expired link, no availability)
- [x] Loading/skeleton states for availability fetches
  - Acceptance criteria:
    - Lighthouse/ basic responsive checks pass; no layout shift on load

---

### 12. Documentation and Tests
- [x] API docs
  - Describe endpoints, auth, params, and examples
- [x] Owner guide
  - Short README on creating links and sharing URLs
- [x] Unit tests (server)
  - Models, availability util, booking creation, token utils
- [ ] Component tests (frontend)
  - Wizard steps render; public form validates; booking submit happy-path
  - Acceptance criteria:
    - CI passes; tests cover critical paths

---

### 13. Follow-up Tasks (Incomplete Work)

The following items were marked as complete but contain significant incomplete work that needs to be addressed:

#### 13.1 Database Integration (Critical)
- [x] Replace mock data structures with actual database operations
  - **Current state**: All endpoints use `mock_booking_links`, `mock_bookings`, etc.
  - **Required**: Implement proper SQLAlchemy database operations
  - **Files**: `services/meetings/api/bookings.py` (lines 69, 233, 293, 314, 335, 388, 440, 480)
  - **Acceptance criteria**: All CRUD operations persist to database; no more mock data

#### 13.2 Authentication Integration (Critical)
- [x] Implement proper user authentication and authorization
  - **Current state**: All endpoints use `"mock_user_id"` hardcoded
  - **Required**: Integrate with existing auth system (JWT, session, etc.)
  - **Files**: `services/meetings/api/bookings.py` (lines 239, 262, 365, 411, 451, 508, 566)
  - **Acceptance criteria**: User ID extracted from auth token; proper permission checks

#### 13.3 Calendar Event Creation (High Priority)
- [x] Implement actual calendar event creation
  - **Current state**: `# TODO: Create calendar event` with mock response
  - **Required**: Call Office Service to create real calendar events
  - **Files**: `services/meetings/api/bookings.py` (line 197)
  - **Acceptance criteria**: Real calendar events created and visible in user's calendar

#### 13.4 Email Service Integration (High Priority)
- [x] Implement actual email sending
  - **Current state**: `# TODO: Send confirmation emails` with no implementation
  - **Required**: Call email service to send real confirmation emails
  - **Files**: `services/meetings/api/bookings.py` (line 200)
  - **Acceptance criteria**: Real emails sent to both parties with meeting details

#### 13.5 Analytics Tracking (Medium Priority)
- [ ] Implement actual analytics event tracking
  - **Current state**: `# TODO: Track analytics` with no implementation
  - **Required**: Store analytics events in database for real tracking
  - **Files**: `services/meetings/api/bookings.py` (line 203)
  - **Acceptance criteria**: View and booking events properly tracked and queryable

#### 13.6 Availability Calculation (Medium Priority)
- [ ] Implement business hours, buffers, and limits enforcement
  - **Current state**: `# TODO: post-process availability to enforce buffers, business hours, limits`
  - **Required**: Apply configuration settings to filter available slots
  - **Files**: `services/meetings/services/booking_availability.py` (line 32)
  - **Acceptance criteria**: Available slots respect all owner configuration settings

#### 13.7 Frontend API Integration (High Priority)
- [x] Replace alert() calls with actual API calls
  - **Current state**: All actions show alerts instead of calling backend
  - **Required**: Implement proper API calls for all CRUD operations
  - **Files**: `frontend/app/bookings/page.tsx` (lines 532, 571, 576, 581, 586, 759, 768)
  - **Acceptance criteria**: All frontend actions properly communicate with backend

#### 13.8 Template Management (Medium Priority)
- [ ] Implement booking template creation and management
  - **Current state**: `# TODO: Create template if provided` with no implementation
  - **Required**: Full CRUD operations for booking templates
  - **Files**: `services/meetings/api/bookings.py` (line 253)
  - **Acceptance criteria**: Templates can be created, updated, and applied to booking links

#### 13.9 One-time Link Storage (Medium Priority)
- [ ] Implement one-time link persistence
  - **Current state**: `# TODO: Store in database` with no implementation
  - **Required**: Store one-time links in database with proper expiration handling
  - **Files**: `services/meetings/api/bookings.py` (line 503)
  - **Acceptance criteria**: One-time links properly stored and can be retrieved/validated

#### 13.10 Error Handling and Validation (Medium Priority)
- [ ] Implement comprehensive input validation and error handling
  - **Current state**: Basic validation only; many edge cases not handled
  - **Required**: Proper Pydantic models, validation, and error responses
  - **Acceptance criteria**: All endpoints properly validate input and return meaningful errors

---

### Nice-to-have (still within MVP if time allows)
- [ ] Calendar overlay (multiple calendars) in availability
- [ ] Template library (starter templates)

Out of scope for this doc: Items listed under PRD "Future concerns" section.


