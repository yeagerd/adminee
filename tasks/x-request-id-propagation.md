# X-Request-Id Propagation and Distributed Tracing Task List

Implement proper propagation of X-Request-Id for true distributed tracing across all services.

- [ ] **Update FastAPI middleware** to extract `X-Request-Id` from incoming headers (if present) and use it for all logs and downstream calls; generate a new one only if missing.
- [ ] **Ensure all outgoing HTTP requests from backend services (API clients)** forward the current `X-Request-Id` header.
- [ ] **Update gateway proxy logic** to always forward or generate `X-Request-Id` for all proxied requests.
- [ ] **Audit all log calls** and ensure `request_id` is included as a structured field where relevant.
- [ ] **(Optional) Integrate OpenTelemetry trace/span IDs into logs** for true distributed tracing.
- [ ] **Add or update tests** to verify `X-Request-Id` propagation end-to-end across gateway and all backend services.
- [ ] **Update documentation** to describe the tracing and request ID propagation policy. 