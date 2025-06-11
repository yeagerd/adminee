# API Key Security Strategy

## Overview
This document outlines our granular API key security model that implements the **principle of least privilege** for service-to-service and frontend-to-service communication.

## Naming Convention

```
api-{client}-{service}-key
```

**Components:**
- `api`: Prefix indicating this is an API access key
- `{client}`: The calling entity (frontend, chat-service, office-service, etc.)
- `{service}`: The target service being accessed (user, office, chat)
- `key`: Suffix indicating this is an access key

## Current API Keys

### Frontend Keys (Full Permissions)
```bash
api-frontend-user-key       # Frontend → User Management Service
api-frontend-office-key     # Frontend → Office Service  
api-frontend-chat-key       # Frontend → Chat Service
```

### Service-to-Service Keys (Limited Permissions)
```bash
api-chat-user-key          # Chat Service → User Management (read-only)
api-chat-office-key        # Chat Service → Office Service (read-only)
api-office-user-key        # Office Service → User Management (token management)
```

## Permission Matrix

| API Key | Service Access | Permissions |
|---------|---------------|-------------|
| `api-frontend-user-key` | User Management | `read_users`, `write_users`, `read_tokens`, `write_tokens`, `read_preferences`, `write_preferences` |
| `api-frontend-office-key` | Office Service | `read_emails`, `send_emails`, `read_calendar`, `write_calendar`, `read_files`, `write_files` |
| `api-frontend-chat-key` | Chat Service | `read_chats`, `write_chats`, `read_threads`, `write_threads` |
| `api-chat-user-key` | User Management | `read_users`, `read_preferences` |
| `api-chat-office-key` | Office Service | `read_emails`, `read_calendar`, `read_files` |
| `api-office-user-key` | User Management | `read_users`, `read_tokens`, `write_tokens` |

## Use Case Examples

### 1. Email Security
```python
# ✅ Frontend can send emails
POST /api/emails/send
Headers: X-API-Key: api-frontend-office-key
Result: SUCCESS (has send_emails permission)

# ❌ Chat service cannot send emails  
POST /api/emails/send
Headers: X-API-Key: api-chat-office-key
Result: 403 Forbidden (lacks send_emails permission)

# ✅ Both can read emails
GET /api/emails
Headers: X-API-Key: api-frontend-office-key
Result: SUCCESS (has read_emails permission)

GET /api/emails  
Headers: X-API-Key: api-chat-office-key
Result: SUCCESS (has read_emails permission)
```

### 2. User Data Protection
```python
# ✅ Frontend can modify user profiles
PUT /api/users/profile
Headers: X-API-Key: api-frontend-user-key
Result: SUCCESS (has write_users permission)

# ❌ Chat service cannot modify user profiles
PUT /api/users/profile
Headers: X-API-Key: api-chat-user-key  
Result: 403 Forbidden (lacks write_users permission)

# ✅ Chat service can read user data for context
GET /api/users/profile
Headers: X-API-Key: api-chat-user-key
Result: SUCCESS (has read_users permission)
```

### 3. Token Management
```python
# ✅ Office service can refresh OAuth tokens
POST /api/tokens/refresh
Headers: X-API-Key: api-office-user-key
Result: SUCCESS (has write_tokens permission)

# ❌ Chat service cannot manage tokens
POST /api/tokens/refresh
Headers: X-API-Key: api-chat-user-key
Result: 403 Forbidden (lacks write_tokens permission)
```

## Implementation Usage

### Basic Route Protection
```python
from fastapi import Depends
from services.user_management.auth.service_auth import ServicePermissionRequired

@app.post("/api/emails/send")
async def send_email(
    service_name: str = Depends(ServicePermissionRequired(["send_emails"]))
):
    # Only api-frontend-office-key can access this
    pass
```

### Multi-Permission Requirements
```python
@app.post("/api/calendar/events")
async def create_event(
    service_name: str = Depends(ServicePermissionRequired(["read_calendar", "write_calendar"]))
):
    # Requires both read AND write calendar permissions
    pass
```

### Authentication Only (No Permissions)
```python
@app.get("/api/health")
async def health_check(
    service_name: str = Depends(verify_service_authentication)
):
    # Any valid API key can access
    pass
```

## Security Benefits

### 1. **Blast Radius Limitation**
- If `api-chat-office-key` is compromised, attacker can only READ office data
- Cannot send emails, modify calendars, or access user management
- Frontend operations remain unaffected

### 2. **Granular Revocation**
- Revoke `api-chat-user-key` without affecting frontend or office service
- Disable specific capabilities without breaking entire service

### 3. **Clear Audit Trail**  
- Logs show both client and service: `"chat-service accessed office-service-access"`
- Easy to identify which component performed which action

### 4. **Compliance Ready**
- Each access is explicitly authorized with documented permissions
- Clear separation of duties between services
- Principle of least privilege enforced

## Environment Strategy

### Development
```bash
api-frontend-user-key
api-frontend-office-key
api-chat-user-key
# etc.
```

### Staging
```bash
staging-frontend-user-key
staging-frontend-office-key  
staging-chat-user-key
# etc.
```

### Production
```bash
prod-frontend-user-key
prod-frontend-office-key
prod-chat-user-key
# etc.
```

## Migration Strategy

### Phase 1: Add New Keys (Backward Compatible)
- Keep existing `dev-service-key` for backward compatibility
- Add new granular keys alongside existing ones
- Update new endpoints to use granular permissions

### Phase 2: Migrate Existing Endpoints
- Update existing routes to use `ServicePermissionRequired`
- Test thoroughly with new key system
- Monitor for any access issues

### Phase 3: Remove Legacy Keys
- Remove `dev-service-key` from API_KEYS mapping
- Update all docker-compose environment variables
- Complete migration to granular system

## Best Practices

### 1. **Key Rotation**
- Rotate keys quarterly or after security incidents
- Use environment variables, never hardcode keys
- Store production keys in secure vault (AWS Secrets Manager, etc.)

### 2. **Monitoring**
- Log all API key usage with client/service information
- Alert on failed authentication attempts
- Monitor for unusual access patterns

### 3. **Documentation**
- Keep permission matrix up to date
- Document which services need which permissions
- Review permissions quarterly for necessary changes

### 4. **Testing**
- Include permission testing in integration tests
- Test both positive (allowed) and negative (denied) cases
- Verify revocation works as expected

This strategy provides enterprise-grade security while maintaining flexibility for future growth and changes. 