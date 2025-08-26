## Office API path prefix update: add "office" segment

Goal: Change frontend and gateway paths for Office APIs to include an "office" segment, e.g. `/api/v1/office/email` instead of `/api/v1/email` (likewise for calendar and contacts). Backend Office service routing remains unchanged (`/v1/email`, `/v1/calendar`, `/v1/contacts`).

### Scope
- Affects only gateway route definitions and frontend API client calls for Office endpoints
- Endpoints in scope: email, calendar, contacts
- Backend Office service stays the same; gateway pathRewrite handles the mapping

### Gateway changes
- [x] Add new service route keys in `gateway/express_gateway.tsx` `serviceRoutes` for:
  - [x] `/api/v1/office/email` → `OFFICE_SERVICE_URL`
  - [x] `/api/v1/office/calendar` → `OFFICE_SERVICE_URL`
  - [x] `/api/v1/office/contacts` → `OFFICE_SERVICE_URL`
- [x] Add proxy `app.use` handlers for the new routes with path rewrites:
  - [x] `/api/v1/office/email` and `/api/v1/office/email/*` → rewrite `^/api/v1/office/email` → `/v1/email`
  - [x] `/api/v1/office/calendar` and `/api/v1/office/calendar/*` → rewrite `^/api/v1/office/calendar` → `/v1/calendar`
  - [x] `/api/v1/office/contacts` and `/api/v1/office/contacts/*` → rewrite `^/api/v1/office/contacts` → `/v1/contacts`
- [x] Update WebSocket upgrade routing to recognize new paths (grouped with Office service):
  - [x] Replace checks for `/api/v1/(calendar|email|contacts)` with `/api/v1/office/(calendar|email|contacts)`
  - [x] Keep legacy checks temporarily if enabling a deprecation window
- [x] Update gateway startup logging to print the new routes; optionally mark legacy routes as deprecated
- [x] Decide on backward compatibility policy:
  - [x] Option A: Keep legacy routes (`/api/v1/email|calendar|contacts`) active for N weeks with deprecation warnings

### Frontend changes
- [x] Update `frontend/api/clients/office-client.ts` to use the new prefixed paths:
  - [x] Calendar: replace `/api/v1/calendar/...` → `/api/v1/office/calendar/...`
  - [x] Email: replace `/api/v1/email/...` → `/api/v1/office/email/...`
  - [x] Contacts: replace `/api/v1/contacts...` → `/api/v1/office/contacts...`
- [x] Search the frontend for any additional hard-coded Office API paths and update if found
  - [x] Grep: `/api/v1/(email|calendar|contacts)` across `frontend/`
- [x] Run frontend type-check and tests
  - [x] `cd frontend && npm run lint && npx tsc --noEmit && npm test`

### Documentation updates (optional but recommended)
- [ ] Update any docs/specs mentioning the old paths to include `/api/v1/office/...`:
  - [ ] `documentation/microsoft-email-threading-implementation.md`
  - [ ] `tasks/api-versioning-v1.md` (service mapping examples)
  - [ ] Any other docs referencing `/api/v1/(email|calendar|contacts)`

### Validation
- [ ] Local verification of gateway routing:
  - [ ] `GET /api/v1/office/calendar/events` routes to Office service `/v1/calendar/events`
  - [ ] `GET /api/v1/office/email/threads` routes to Office service `/v1/email/threads`
  - [ ] `GET /api/v1/office/contacts` routes to Office service `/v1/contacts`
- [ ] Manual smoke test from the app UI paths that exercise calendar, email, and contacts features
- [ ] Confirm required headers are still proxied (auth, API keys)
- [ ] If legacy routes retained: confirm both old and new paths work during the deprecation window

### No Backwards compatibility
- [ ] Remove legacy routes:
  - [ ] Delete old `/api/v1/(email|calendar|contacts)` handlers and route keys in the gateway
  - [ ] Remove deprecation logs

### Acceptance criteria
- [ ] Frontend only uses `/api/v1/office/(email|calendar|contacts)`
- [ ] Gateway proxies the new routes correctly to `/v1/(email|calendar|contacts)`
- [ ] No regressions in Office features (email, calendar, contacts) verified via UI and API
- [ ] Documentation reflects new paths

