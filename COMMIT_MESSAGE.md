feat: unify authentication to use X-User-Id header from gateway

- Update office service calendar endpoints to extract user ID from X-User-Id header
- Update office service files endpoints to extract user ID from X-User-Id header  
- Update chat service tests to use X-User-Id header instead of query params
- Update all office service tests to use new authentication pattern
- Add auth_headers fixture to test infrastructure for consistent testing
- Remove user_id from query parameters across all endpoints
- Complete Phase 2 of authentication unification project

All tests passing (728 passed, 2 skipped). Endpoints now properly extract
user identity from gateway headers instead of query parameters for improved
security and consistency. 