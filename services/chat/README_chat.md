## API Endpoint Patterns

- **User-facing endpoints:**
  - Use header-based user extraction (X-User-Id set by gateway)
  - No user_id in path or query
  - Require user authentication (JWT/session)

- **Internal/service endpoints:**
  - Use /internal prefix
  - Require API key/service authentication
  - Used for service-to-service and background job calls 