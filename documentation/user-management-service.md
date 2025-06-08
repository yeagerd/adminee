# User Management Service Design Document

## Overview

The `user-management-service` is a core backend microservice responsible for managing user profiles, preferences, OAuth integrations, and token storage for the Briefly application. It serves as the central authority for user data and provides secure token management for all external API integrations (Google, Microsoft). The service is built using Python, FastAPI, and Pydantic, following the same patterns as other services in the architecture.

---

## 1. API Endpoints

### 1.1. User Profile Management
- **GET /users/{user_id}**
    - **Input:** `user_id` (from Next.js API proxy, e.g., Clerk ID)
    - **Output:** Complete user profile including preferences and integration status
    - **Authentication:** Requires valid user token, only returns data for authenticated user

- **PUT /users/{user_id}**
    - **Input:** User profile updates (preferences, settings)
    - **Output:** Updated user profile
    - **Authentication:** User can only update their own profile

- **DELETE /users/{user_id}**
    - **Input:** `user_id` and optional data retention preferences
    - **Output:** Account deletion confirmation and cleanup status
    - **Authentication:** User can only delete their own account

### 1.2. User Preferences
- **GET /users/{user_id}/preferences**
    - **Output:** All user preferences (UI, notifications, AI, integrations)
    
- **PUT /users/{user_id}/preferences**
    - **Input:** Preference updates (partial or complete)
    - **Output:** Updated preferences object

- **POST /users/{user_id}/preferences/reset**
    - **Output:** Preferences reset to system defaults

### 1.3. OAuth Integration Management
- **GET /users/{user_id}/integrations**
    - **Output:** List of connected integrations with status and permissions
    
- **POST /users/{user_id}/integrations/{provider}**
    - **Input:** OAuth authorization code, state, and scope information
    - **Output:** Integration connection status and available permissions
    - **Note:** Called by Next.js API routes after OAuth callback

- **DELETE /users/{user_id}/integrations/{provider}**
    - **Output:** Integration disconnection status and cleanup confirmation
    - **Side Effects:** Revokes tokens, cleans up provider-specific data

- **PUT /users/{user_id}/integrations/{provider}/refresh**
    - **Output:** Token refresh status and new expiration time
    - **Internal:** Used by other services via service-to-service auth

### 1.4. Token Management (Service-to-Service)
- **POST /internal/tokens/get**
    - **Input:** `user_id`, `provider`, `required_scopes`
    - **Output:** Valid access token and metadata
    - **Authentication:** Service-to-service API key
    - **Security:** Automatic token refresh if needed

- **POST /internal/tokens/refresh**
    - **Input:** `user_id`, `provider`
    - **Output:** Token refresh status
    - **Authentication:** Service-to-service API key

### 1.5. User Lifecycle Events
- **POST /webhooks/clerk**
    - **Input:** Clerk webhook payload (user.created, user.updated, user.deleted)
    - **Output:** Webhook processing status
    - **Security:** Webhook signature validation

---

## 2. Core Modules

### 2.1. User Profile Manager
- Handles user CRUD operations and profile management
- Manages user lifecycle events from Clerk webhooks
- Supports profile data validation and sanitization
- Provides user search and lookup capabilities

### 2.2. Preferences Manager
- Manages hierarchical user preferences (UI, notifications, AI, integrations)
- Supports preference inheritance and defaults
- Validates preference values against schemas
- Handles preference migration for schema changes

### 2.3. OAuth Integration Manager
- Orchestrates OAuth flows for Google and Microsoft
- Manages OAuth state and PKCE verification
- Handles scope validation and permission management
- Coordinates with token storage for secure persistence

### 2.4. Token Storage & Encryption
- Encrypts/decrypts OAuth tokens using user-specific keys
- Manages token lifecycle (storage, refresh, revocation)
- Implements secure key derivation from Clerk user IDs
- Provides token retrieval with automatic refresh logic

### 2.5. Integration Status Tracker
- Monitors integration health and connectivity
- Tracks token expiration and refresh requirements
- Manages integration-specific metadata and permissions
- Provides integration status to other services

### 2.6. Audit Logger
- Logs all sensitive operations (token access, profile changes)
- Tracks user consent and permission changes
- Maintains audit trail for compliance and debugging
- Supports structured logging for analysis

---

## 3. Integration Patterns

### 3.1. Service-to-Service Token Retrieval
```python
# Example: Office Service requesting user tokens
async def get_user_token(user_id: str, provider: str, scopes: List[str]):
    response = await httpx.post(
        f"{USER_MANAGEMENT_URL}/internal/tokens/get",
        json={
            "user_id": user_id,
            "provider": provider,
            "required_scopes": scopes
        },
        headers={"Authorization": f"Bearer {SERVICE_API_KEY}"}
    )
    return response.json()
```

### 3.2. OAuth Flow Integration
- Next.js API routes handle OAuth redirects
- User Management Service processes authorization codes
- Secure token storage with immediate encryption
- Integration status broadcast to dependent services

---

## 4. Security & Authentication

### 4.1. User Authentication
- All user-facing endpoints require valid Clerk JWT tokens
- Token validation using Clerk's public key verification
- User identity extraction from JWT claims
- Rate limiting per user to prevent abuse

### 4.2. Service-to-Service Authentication
- Internal endpoints protected by API key authentication
- Service-specific API keys with scope restrictions
- Request signing for sensitive token operations
- IP allowlisting for additional security

### 4.3. Token Encryption Strategy
- **Encryption Method:** AES-256-GCM with user-specific keys
- **Key Derivation:** PBKDF2 using Clerk user ID and service salt
- **Storage:** Encrypted tokens in PostgreSQL, keys in memory/env
- **Rotation:** Support for key rotation without service downtime

---

## 5. Data Models

### 5.1. Ormar Models
```python
import ormar
import sqlalchemy
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import EmailStr

# Database and metadata setup
DATABASE_URL = "postgresql://user:password@localhost/briefly"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

class BaseMeta(ormar.ModelMeta):
    metadata = metadata
    database = database

class IntegrationProvider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"

class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"

class User(ormar.Model):
    class Meta(BaseMeta):
        tablename = "users"

    id: str = ormar.String(max_length=255, primary_key=True)
    email: EmailStr = ormar.String(max_length=255, unique=True)
    first_name: Optional[str] = ormar.String(max_length=100, nullable=True)
    last_name: Optional[str] = ormar.String(max_length=100, nullable=True)
    profile_image_url: Optional[str] = ormar.Text(nullable=True)
    onboarding_completed: bool = ormar.Boolean(default=False)
    onboarding_completed_at: Optional[datetime] = ormar.DateTime(nullable=True)
    created_at: datetime = ormar.DateTime(default=datetime.utcnow)
    updated_at: datetime = ormar.DateTime(default=datetime.utcnow)
    last_active_at: Optional[datetime] = ormar.DateTime(nullable=True)

class UserPreferences(ormar.Model):
    class Meta(BaseMeta):
        tablename = "user_preferences"

    user_id: str = ormar.ForeignKey(User, primary_key=True, ondelete="CASCADE")
    
    # UI Preferences
    theme: str = ormar.String(max_length=20, default="system")
    timezone: str = ormar.String(max_length=50, default="UTC")
    language: str = ormar.String(max_length=10, default="en")
    date_format: str = ormar.String(max_length=20, default="MM/DD/YYYY")
    time_format: str = ormar.String(max_length=10, default="12h")
    
    # Notification Preferences
    email_notifications: bool = ormar.Boolean(default=True)
    push_notifications: bool = ormar.Boolean(default=True)
    calendar_reminders: bool = ormar.Boolean(default=True)
    ai_suggestions: bool = ormar.Boolean(default=True)
    
    # AI Preferences
    preferred_ai_model: str = ormar.String(max_length=50, default="gpt-4")
    ai_response_style: str = ormar.String(max_length=20, default="balanced")
    ai_context_length: str = ormar.String(max_length=20, default="medium")
    
    # Integration Preferences
    default_calendar: Optional[str] = ormar.String(max_length=255, nullable=True)
    default_email_signature: Optional[str] = ormar.Text(nullable=True)
    sync_frequency: str = ormar.String(max_length=20, default="real-time")
    
    # Privacy Preferences
    data_sharing_analytics: bool = ormar.Boolean(default=True)
    data_sharing_improvements: bool = ormar.Boolean(default=True)
    
    created_at: datetime = ormar.DateTime(default=datetime.utcnow)
    updated_at: datetime = ormar.DateTime(default=datetime.utcnow)

class Integration(ormar.Model):
    class Meta(BaseMeta):
        tablename = "integrations"
        constraints = [ormar.UniqueColumns("user_id", "provider", "account_email")]

    id: str = ormar.UUID(primary_key=True, default=ormar.uuid4)
    user: User = ormar.ForeignKey(User, ondelete="CASCADE")
    provider: IntegrationProvider = ormar.String(max_length=50, choices=list(IntegrationProvider))
    status: IntegrationStatus = ormar.String(max_length=20, choices=list(IntegrationStatus), default=IntegrationStatus.CONNECTED)
    connected_at: datetime = ormar.DateTime(default=datetime.utcnow)
    last_refresh_at: Optional[datetime] = ormar.DateTime(nullable=True)
    expires_at: Optional[datetime] = ormar.DateTime(nullable=True)
    granted_scopes: List[str] = ormar.JSON(default=list)
    account_email: EmailStr = ormar.String(max_length=255)
    account_name: Optional[str] = ormar.String(max_length=255, nullable=True)
    metadata: Dict[str, Any] = ormar.JSON(default=dict)
    created_at: datetime = ormar.DateTime(default=datetime.utcnow)
    updated_at: datetime = ormar.DateTime(default=datetime.utcnow)

class EncryptedToken(ormar.Model):
    class Meta(BaseMeta):
        tablename = "encrypted_tokens"
        constraints = [ormar.UniqueColumns("integration_id", "token_type")]

    id: str = ormar.UUID(primary_key=True, default=ormar.uuid4)
    user: User = ormar.ForeignKey(User, ondelete="CASCADE")
    integration: Integration = ormar.ForeignKey(Integration, ondelete="CASCADE")
    token_type: str = ormar.String(max_length=50)  # access_token, refresh_token
    encrypted_value: bytes = ormar.LargeBinary()
    encryption_key_id: str = ormar.String(max_length=100)
    expires_at: Optional[datetime] = ormar.DateTime(nullable=True)
    created_at: datetime = ormar.DateTime(default=datetime.utcnow)
    updated_at: datetime = ormar.DateTime(default=datetime.utcnow)

class AuditLog(ormar.Model):
    class Meta(BaseMeta):
        tablename = "audit_logs"

    id: str = ormar.UUID(primary_key=True, default=ormar.uuid4)
    user: User = ormar.ForeignKey(User, ondelete="CASCADE")
    action: str = ormar.String(max_length=100)
    resource_type: str = ormar.String(max_length=50)
    resource_id: Optional[str] = ormar.String(max_length=255, nullable=True)
    details: Dict[str, Any] = ormar.JSON(default=dict)
    ip_address: Optional[str] = ormar.String(max_length=45, nullable=True)  # IPv6 compatible
    user_agent: Optional[str] = ormar.Text(nullable=True)
    created_at: datetime = ormar.DateTime(default=datetime.utcnow)
```

### 5.2. Database Indexes and Constraints

Since Ormar handles table creation automatically, we only need to define additional indexes for performance:

```python
# Additional indexes can be defined in Alembic migrations
# or using SQLAlchemy Index objects in the models

# Example indexes for performance optimization:
from sqlalchemy import Index

# Define indexes for frequently queried fields
integration_user_provider_idx = Index(
    'idx_integrations_user_provider', 
    Integration.__table__.c.user_id, 
    Integration.__table__.c.provider
)

integration_status_idx = Index(
    'idx_integrations_status',
    Integration.__table__.c.status
)

encrypted_tokens_integration_idx = Index(
    'idx_encrypted_tokens_integration',
    EncryptedToken.__table__.c.integration_id
)

audit_logs_user_action_idx = Index(
    'idx_audit_logs_user_action',
    AuditLog.__table__.c.user_id,
    AuditLog.__table__.c.action
)

audit_logs_created_at_idx = Index(
    'idx_audit_logs_created_at',
    AuditLog.__table__.c.created_at
)
```

---

## 6. ORM and Schema Management

- Use **Ormar** as the ORM for all database models and operations
- Use **Alembic** for schema migrations and management  
- Ormar automatically generates database tables from model definitions
- Implement **soft deletes** for user data with configurable retention periods
- Support **database connection pooling** for high-concurrency scenarios

---

## 7. Error Handling

### 7.1. Standard Error Response Format
```json
{
  "error": {
    "type": "validation_error|auth_error|integration_error|encryption_error|not_found|internal_error",
    "message": "Human-readable error message",
    "details": {
      "field": "specific error details",
      "code": "ERROR_CODE"
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "uuid"
  }
}
```

### 7.2. Error Types and Handling
- **ValidationError**: Pydantic validation failures, preference schema violations
- **AuthenticationError**: Invalid tokens, unauthorized access attempts
- **IntegrationError**: OAuth failures, provider API errors, token refresh failures
- **EncryptionError**: Token encryption/decryption failures, key derivation issues
- **NotFoundError**: User not found, integration not found, preference not found
- **InternalError**: Database errors, service unavailable, unexpected exceptions

---

## 8. Authentication & Authorization

### 8.1. User Authentication Flow
1. Next.js API route validates Clerk session
2. Extracts user ID from Clerk JWT token
3. Forwards request to User Management Service with user context
4. Service validates user exists and is active
5. Processes request with appropriate authorization checks

### 8.2. Service-to-Service Authentication
```python
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_service_token(token: str = Depends(security)):
    if token.credentials != os.getenv("SERVICE_API_KEY"):
        raise HTTPException(
            status_code=401,
            detail="Invalid service authentication"
        )
    return token.credentials
```

---

## 9. Token Management Implementation

### 9.1. Encryption Strategy
```python
import os
import hashlib
from cryptography.fernet import Fernet
from typing import Tuple

class TokenEncryption:
    def __init__(self):
        self.service_salt = os.getenv("TOKEN_ENCRYPTION_SALT").encode()
    
    def derive_user_key(self, user_id: str) -> bytes:
        """Derive encryption key from user ID and service salt"""
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            user_id.encode(),
            self.service_salt,
            100000  # iterations
        )
        return base64.urlsafe_b64encode(key_material[:32])
    
    def encrypt_token(self, token: str, user_id: str) -> Tuple[bytes, str]:
        """Encrypt token and return encrypted bytes + key ID"""
        key = self.derive_user_key(user_id)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(token.encode())
        key_id = hashlib.sha256(key).hexdigest()[:16]
        return encrypted, key_id
    
    def decrypt_token(self, encrypted_token: bytes, user_id: str) -> str:
        """Decrypt token using user-derived key"""
        key = self.derive_user_key(user_id)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_token).decode()
```

### 9.2. Token Refresh Logic
```python
async def get_valid_token(user_id: str, provider: str, required_scopes: List[str]):
    """Get valid access token, refreshing if necessary"""
    # Query integration using Ormar
    integration = await Integration.objects.select_related("user").get_or_none(
        user__id=user_id, 
        provider=provider,
        status=IntegrationStatus.CONNECTED
    )
    if not integration:
        raise IntegrationNotFoundError()
    
    # Get access token using Ormar relationship
    access_token_record = await EncryptedToken.objects.get_or_none(
        integration=integration,
        token_type="access_token"
    )
    
    if not access_token_record:
        raise TokenNotFoundError()
    
    # Check if token is expired or expiring soon
    if is_token_expired(access_token_record, buffer_minutes=5):
        refresh_token_record = await EncryptedToken.objects.get_or_none(
            integration=integration,
            token_type="refresh_token"
        )
        
        if not refresh_token_record:
            raise RefreshTokenNotFoundError()
            
        # Decrypt and refresh token
        decrypted_refresh_token = decrypt_token(
            refresh_token_record.encrypted_value,
            user_id
        )
        
        new_tokens = await refresh_oauth_token(provider, decrypted_refresh_token)
        
        # Update tokens in database
        await access_token_record.update(
            encrypted_value=encrypt_token(new_tokens.access_token, user_id)[0],
            expires_at=new_tokens.expires_at,
            updated_at=datetime.utcnow()
        )
        
        access_token = new_tokens.access_token
    else:
        # Decrypt existing token
        access_token = decrypt_token(
            access_token_record.encrypted_value,
            user_id
        )
    
    # Validate scopes
    if not has_required_scopes(integration.granted_scopes, required_scopes):
        raise InsufficientScopesError()
    
    return access_token
```

---

## 10. Integration with External Services

### 10.1. Clerk Webhook Integration
```python
from clerk_backend_api import Clerk

clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

@app.post("/webhooks/clerk")
async def handle_clerk_webhook(request: Request):
    # Verify webhook signature
    signature = request.headers.get("svix-signature")
    webhook_secret = os.getenv("CLERK_WEBHOOK_SECRET")
    
    if not verify_webhook_signature(signature, await request.body(), webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = await request.json()
    event_type = payload.get("type")
    user_data = payload["data"]
    
    if event_type == "user.created":
        # Create user profile using Ormar
        await User.objects.create(
            id=user_data["id"],
            email=user_data["email_addresses"][0]["email_address"],
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            profile_image_url=user_data.get("image_url")
        )
        
        # Create default preferences
        await UserPreferences.objects.create(user_id=user_data["id"])
        
    elif event_type == "user.updated":
        # Update user profile using Ormar
        user = await User.objects.get_or_none(id=user_data["id"])
        if user:
            await user.update(
                email=user_data["email_addresses"][0]["email_address"],
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                profile_image_url=user_data.get("image_url"),
                updated_at=datetime.utcnow()
            )
            
    elif event_type == "user.deleted":
        # Soft delete user and cascade to related records
        user = await User.objects.get_or_none(id=user_data["id"])
        if user:
            # Ormar will handle CASCADE deletes automatically
            await user.delete()
            
            # Log audit event
            await AuditLog.objects.create(
                user_id=user_data["id"],
                action="user_deleted",
                resource_type="user",
                details={"source": "clerk_webhook"}
            )
    
    return {"status": "processed"}
```

### 10.2. OAuth Provider Integration
```python
async def complete_oauth_flow(
    user_id: str, 
    provider: str, 
    auth_code: str, 
    state: str
):
    """Complete OAuth flow and store tokens"""
    # Validate state parameter
    if not validate_oauth_state(state, user_id):
        raise InvalidOAuthStateError()
    
    # Exchange auth code for tokens
    token_response = await exchange_auth_code(provider, auth_code)
    
    # Get user info from provider
    user_info = await get_provider_user_info(
        provider, 
        token_response.access_token
    )
    
    # Store integration
    integration = await create_integration(
        user_id=user_id,
        provider=provider,
        account_email=user_info.email,
        account_name=user_info.name,
        granted_scopes=token_response.scope.split()
    )
    
    # Store encrypted tokens
    await store_encrypted_tokens(integration.id, token_response)
    
    return integration
```

---

## 11. Background Jobs & Maintenance

### 11.1. Token Refresh Job
```python
from celery import Celery
from datetime import datetime, timedelta

celery_app = Celery('user-management')

@celery_app.task
async def refresh_expiring_tokens():
    """Proactively refresh tokens expiring in the next hour"""
    expiring_soon = await get_tokens_expiring_soon(
        hours=1
    )
    
    for token_info in expiring_soon:
        try:
            await refresh_user_token(
                token_info.user_id,
                token_info.provider
            )
            await log_audit_event(
                user_id=token_info.user_id,
                action="token_refreshed",
                resource_type="integration",
                resource_id=token_info.integration_id
            )
        except Exception as e:
            await log_token_refresh_failure(token_info, e)
```

### 11.2. Data Cleanup Job
```python
@celery_app.task
async def cleanup_deleted_user_data():
    """Clean up data for users deleted more than 30 days ago"""
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    
    deleted_users = await get_soft_deleted_users(before=cutoff_date)
    
    for user_id in deleted_users:
        await hard_delete_user_data(user_id)
        await log_audit_event(
            user_id=user_id,
            action="data_permanently_deleted",
            resource_type="user"
        )
```

---

## 12. Testing Strategy

### 12.1. Unit Tests
- **Token Encryption/Decryption**: Test key derivation, encryption correctness
- **OAuth Flow Logic**: Test state validation, token exchange, error handling
- **Preference Management**: Test validation, defaults, inheritance
- **API Endpoints**: Test request/response validation, authorization

### 12.2. Integration Tests
- **Database Operations**: Test CRUD operations, constraints, migrations
- **External API Integration**: Test OAuth flows with mock providers
- **Service-to-Service**: Test token retrieval by other services
- **Webhook Processing**: Test Clerk webhook handling end-to-end

### 12.3. Security Tests
- **Token Security**: Test encryption strength, key derivation
- **Access Control**: Test unauthorized access prevention
- **Data Isolation**: Test user data separation
- **Audit Logging**: Test sensitive operation logging

---

## 13. Observability & Monitoring

### 13.1. Metrics to Track
- **Token Operations**: Refresh success/failure rates, encryption/decryption performance
- **API Performance**: Response times, error rates by endpoint
- **Integration Health**: Connection status, OAuth flow success rates
- **User Activity**: Profile updates, preference changes, integration connections

### 13.2. Logging Strategy
```python
import structlog

logger = structlog.get_logger()

async def log_audit_event(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str = None,
    details: dict = None
):
    """Structured audit logging"""
    await logger.info(
        "audit_event",
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        timestamp=datetime.utcnow().isoformat()
    )
```

---

## 14. Security Considerations

### 14.1. Data Protection
- **Token Encryption**: AES-256-GCM with user-specific keys
- **Key Management**: Secure key derivation, no plaintext key storage
- **Data in Transit**: TLS 1.3 for all communications
- **Database Security**: Encrypted at rest, connection pooling with auth

### 14.2. Privacy & Compliance
- **Data Minimization**: Store only necessary user data
- **Right to Deletion**: Complete data removal capabilities
- **Audit Trail**: Comprehensive logging of data access
- **Consent Management**: Track user permissions and preferences

### 14.3. Rate Limiting & Abuse Prevention
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.get("/users/{user_id}")
async def get_user_profile(
    user_id: str,
    ratelimit: str = Depends(RateLimiter(times=100, seconds=60))
):
    # Rate limited to 100 requests per minute per user
    pass
```

---

## 15. Areas of Concern / Open Questions

### 15.1. Technical Concerns
- **Token Rotation**: Strategy for rotating encryption keys without downtime
- **Scalability**: Database performance with large user bases and token volumes
- **Backup & Recovery**: Encrypted data backup and disaster recovery procedures
- **Cross-Service Consistency**: Maintaining data consistency across service boundaries

### 15.2. Security Concerns
- **Key Compromise**: Recovery procedures if encryption keys are compromised
- **Token Leakage**: Detection and response to potential token exposure
- **Audit Compliance**: Meeting regulatory requirements for financial/healthcare data
- **Service Account Security**: Securing service-to-service authentication

### 15.3. Operational Concerns
- **Monitoring**: Comprehensive observability for token operations and user lifecycle
- **Incident Response**: Procedures for OAuth provider outages or security incidents
- **Data Migration**: Safe migration strategies for schema changes and data moves
- **Performance Optimization**: Query optimization for large-scale user and token data

---

## 16. Future Enhancements

### 16.1. Advanced Features
- **Multi-Factor Authentication**: Additional security layers for sensitive operations
- **OAuth Scope Management**: Dynamic scope requests based on feature usage
- **Token Analytics**: Detailed analytics on token usage and integration health
- **User Segmentation**: Advanced user grouping for feature rollouts and preferences

### 16.2. Integration Expansions
- **Additional Providers**: Slack, Notion, Salesforce, and other productivity tools
- **Enterprise SSO**: SAML/OIDC integration for enterprise customers
- **API Gateway Integration**: Advanced routing and rate limiting capabilities
- **Real-time Sync**: WebSocket-based real-time preference and status updates

---

## 17. Implementation Phases

### 17.1. Phase 1: Core Foundation (Week 1-2)
- Basic user profile CRUD operations
- Preference management with validation
- Database schema and migrations
- Clerk webhook integration

### 17.2. Phase 2: OAuth & Token Management (Week 3-4)
- OAuth flow implementation (Google, Microsoft)
- Token encryption and storage
- Service-to-service token retrieval API
- Basic audit logging

### 17.3. Phase 3: Advanced Features (Week 5-6)
- Proactive token refresh
- Comprehensive error handling
- Rate limiting and security hardening
- Integration health monitoring

### 17.4. Phase 4: Production Readiness (Week 7-8)
- Comprehensive testing suite
- Performance optimization
- Monitoring and observability
- Documentation and deployment automation

---

*This document is a living specification and should be updated as requirements evolve and implementation details are refined.* 