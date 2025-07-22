# X-Request-Id Propagation and Distributed Tracing Task List

Implement proper propagation of X-Request-Id for true distributed tracing across all services.

- [x] **Update FastAPI middleware** to extract `X-Request-Id` from incoming headers (if present) and use it for all logs and downstream calls; generate a new one only if missing.
- [ ] **Audit and fix all backend API clients (especially Office Service)** to ensure they propagate the current `X-Request-Id` header instead of generating a new one for each outgoing request.
- [ ] **Verify and update gateway proxy logic** to always forward or generate `X-Request-Id` for all proxied requests.
- [x] **Audit all log calls** and ensure `request_id` is included as a structured field where relevant.
- [ ] **Integrate OpenTelemetry trace/span IDs into logs** for true distributed tracing.
- [ ] **Add or update tests** to verify `X-Request-Id` propagation end-to-end across gateway and all backend services, including full E2E coverage.
- [ ] **Update and expand documentation** to describe the tracing and request ID propagation policy, including E2E propagation and distributed tracing best practices. 