# Office Service Design Document

## Overview

The `office-service` is a backend microservice responsible for all external API interactions with Google and Microsoft services. It serves as the integration layer between Briefly and external productivity platforms, handling authentication, API calls, data normalization, rate limiting, and caching. The service abstracts away the complexity of different API formats and provides a consistent interface for other services to access user data from Gmail, Google Calendar, Google Drive, Outlook, Office 365 Calendar, OneDrive, and Microsoft Graph.

---

## 1. API Endpoints

### 1.1. Unified/Normalized Endpoints

#### 1.1.1. Cross-Platform Email
- **GET /email/messages**
    - **Input:** `user_id`, `providers` (optional: ["google", "microsoft"]), search parameters
    - **Output:** Unified email messages from all connected providers
    - **Logic:** Aggregates and normalizes emails from Gmail and Outlook
    - **Caching:** 15 minutes for message lists

- **GET /email/messages/{message_id}**
    - **Input:** `user_id`, `message_id`
    - **Output:** Full message content including body, attachments, headers
    - **Caching:** 30 minutes for message content

- **POST /email/search**
    - **Input:** `user_id`, `query`, `providers` (optional), `date_range` (optional)
    - **Output:** Unified search results across all email providers
    - **Performance:** Parallel API calls to all providers
    - **Caching:** 15 minutes

- **GET /email/threads/{thread_id}**
    - **Input:** `user_id`, `thread_id`
    - **Output:** Complete email thread with all messages from all providers
    - **Caching:** 15 minutes

- **POST /email/send**
    - **Input:** `user_id`, `to`, `subject`, `body`, `attachments` (optional), `reply_to_message_id` (optional), `provider` (optional, defaults to user preference)
    - **Output:** Sent message metadata and delivery status
    - **Side Effects:** Queues email for asynchronous sending via Email Service

#### 1.1.2. Cross-Platform Calendar
- **GET /calendar/calendars**
    - **Input:** `user_id`, `providers` (optional)
    - **Output:** List of all user's calendars from connected providers
    - **Logic:** Aggregates calendars from Google and Microsoft with unified format
    - **Caching:** 60 minutes

- **GET /calendar/events**
    - **Input:** `user_id`, `calendar_ids` (optional), `start_time`, `end_time`, `providers` (optional)
    - **Output:** Unified calendar events from all connected providers
    - **Logic:** Aggregates, normalizes, and deduplicates events
    - **Caching:** 15 minutes

- **POST /calendar/events**
    - **Input:** `user_id`, `calendar_id`, event details (summary, start, end, attendees, location)
    - **Output:** Created event metadata
    - **Side Effects:** Event created in specified calendar provider

- **PUT /calendar/events/{event_id}**
    - **Input:** `user_id`, `event_id`, updated event details
    - **Output:** Updated event metadata
    - **Side Effects:** Event updated in original provider

- **DELETE /calendar/events/{event_id}**
    - **Input:** `user_id`, `event_id`
    - **Output:** Deletion confirmation
    - **Side Effects:** Event deleted from original provider

- **GET /calendar/availability**
    - **Input:** `user_id`, `start_time`, `end_time`, `providers` (optional)
    - **Output:** Consolidated availability across all calendars
    - **Logic:** Merges free/busy data from all providers
    - **Caching:** 5 minutes (short due to scheduling sensitivity)

#### 1.1.3. Cross-Platform Files
- **GET /files**
    - **Input:** `user_id`, `query` (optional search query), `providers` (optional), `page_size` (default: 100), `page_token` (optional)
    - **Output:** List of files from all connected providers with unified metadata
    - **Logic:** Aggregates files from Google Drive and OneDrive
    - **Caching:** 30 minutes

- **GET /files/{file_id}**
    - **Input:** `user_id`, `file_id`
    - **Output:** File metadata and download links
    - **Caching:** 60 minutes

- **GET /files/{file_id}/content**
    - **Input:** `user_id`, `file_id`
    - **Output:** File content (for supported text formats)
    - **Caching:** 30 minutes
    - **Note:** Designed for consumption by future Content Service for RAG processing

- **POST /files/search**
    - **Input:** `user_id`, `query`, `providers` (optional), `file_types` (optional), `modified_since` (optional)
    - **Output:** Unified file search results from Drive and OneDrive
    - **Performance:** Parallel searches with result ranking
    - **Caching:** 15 minutes

**Design Note**: File operations are included in Office Service for MVP simplicity, leveraging existing Google/Microsoft OAuth tokens. Future Content Service can consume these endpoints for document RAG and creation features.

#### 1.1.4. Cross-Platform Contacts
- **GET /contacts**
    - **Input:** `user_id`, `providers` (optional), `page_size` (default: 1000), `page_token` (optional)
    - **Output:** List of contacts from all connected providers with unified format
    - **Logic:** Aggregates and deduplicates contacts from Google and Microsoft
    - **Caching:** 2 hours

### 1.2. Health and Diagnostics
- **GET /health**
    - **Output:** Service health status and dependency checks

- **GET /health/integrations/{user_id}**
    - **Input:** `user_id`
    - **Output:** Integration status for all connected providers
    - **Logic:** Validates tokens and API connectivity

---

## 2. Core Modules

### 2.1. Token Manager
- Interfaces with User Management Service for token retrieval
- Handles automatic token refresh with exponential backoff
- Manages token scope validation and upgrade requests
- Implements token caching to reduce User Management Service calls
- Provides token health monitoring and error reporting

### 2.2. API Client Factory
- Creates provider-specific API clients (Google, Microsoft) for internal use
- Manages authentication headers and request signing
- Implements retry logic with circuit breaker pattern
- Handles rate limiting and quota management per provider
- Provides request/response logging and metrics collection
- **Note**: Provider-specific clients are internal modules only, not exposed as HTTP endpoints

### 2.3. Data Normalizer
- Converts provider-specific API responses to unified schemas
- Handles data type conversions and field mapping
- Manages timezone conversions and date formatting
- Provides data validation and sanitization
- Implements extensible transformation pipelines

### 2.4. Cache Manager
- Redis-based caching with TTL management
- Implements cache invalidation strategies
- Provides cache warming for frequently accessed data
- Handles cache versioning for schema changes
- Supports cache compression for large responses

### 2.5. Rate Limiter
- Per-provider rate limiting with quota tracking
- User-level rate limiting to prevent abuse
- Implements sliding window and token bucket algorithms
- Provides rate limit status in API responses
- Manages rate limit recovery and backoff strategies

### 2.6. Error Handler
- Standardized error response format across all endpoints
- Provider-specific error code translation
- Implements retry logic for transient failures
- Provides detailed error logging and monitoring
- Handles partial failure scenarios in unified endpoints

### 2.7. Background Task Manager
- Asynchronous processing for non-critical operations
- Token refresh scheduling and monitoring
- Cache warming and preloading tasks
- Integration health checks and monitoring
- Cleanup tasks for expired data

---

## 3. Integration with Other Services

### 3.1. User Management Service Integration
```python
class TokenManager:
    async def get_user_token(self, user_id: str, provider: str, scopes: List[str]) -> Optional[TokenData]:
        """Retrieve valid token from User Management Service"""
        try:
            response = await self.http_client.post(
                f"{USER_MANAGEMENT_URL}/internal/tokens/get",
                json={
                    "user_id": user_id,
                    "provider": provider,
                    "required_scopes": scopes
                },
                headers={"Authorization": f"Bearer {SERVICE_API_KEY}"}
            )
            if response.status_code == 200:
                return TokenData(**response.json())
            return None
        except Exception as e:
            logger.error(f"Token retrieval failed: {e}")
            return None
```

### 3.2. Chat Service Integration
- Provides context data for LLM conversations
- Handles tool requests for data retrieval and modification
- Returns structured data for context injection
- Supports streaming responses for large datasets

### 3.3. Email Service Integration
- Provides email sending capabilities via provider APIs
- Handles email template processing and personalization
- Manages email queue integration for background sending
- Supports email tracking and delivery status updates

### 3.4. Content Service Integration
- Provides file content for document management
- Handles file synchronization between providers and local storage
- Manages file change notifications and webhooks
- Supports collaborative editing workflow

---

## 4. Security & Authentication

### 4.1. User Authentication
- All endpoints require valid user authentication via Next.js API proxy
- User identity extracted from JWT tokens or session data
- Request validation and sanitization for all inputs
- Audit logging for all user actions and data access

### 4.2. Service-to-Service Authentication
- Internal endpoints protected by API key authentication
- Service-specific API keys with scope restrictions
- Request signing for sensitive operations
- Rate limiting per service to prevent abuse

### 4.3. Data Privacy and Security
- All API requests over HTTPS with certificate validation
- User data isolation enforced at all levels
- Sensitive data not logged or cached inappropriately
- Compliance with provider API terms of service and privacy policies

---

## 5. Data Models

### 5.1. SqlModel Models

```python
import sqlmodel
import sqlalchemy
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr

DB_URL_OFFICE = "postgresql://user:password@localhost/briefly"
database = databases.Database(DB_URL_OFFICE)
metadata = sqlalchemy.MetaData()

class BaseMeta(sqlmodel.SQLModel): # TODO: Check if this is the correct base class
    metadata = metadata
    database = database

class Provider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"

class ApiCallStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error" 
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"

# API Call Tracking
class ApiCall(sqlmodel.SQLModel, table=True):
    __tablename__ = "api_calls"

    id: int = sqlmodel.Field(default=None, primary_key=True)
    user_id: str = sqlmodel.Field(default=None, max_length=255, index=True)
    provider: Provider = sqlmodel.Field(default=None, max_length=20) # TODO: Check choices=list(Provider)
    endpoint: str = sqlmodel.Field(default=None, max_length=200)
    method: str = sqlmodel.Field(default=None, max_length=10)
    status: ApiCallStatus = sqlmodel.Field(default=None, max_length=20) # TODO: Check choices=list(ApiCallStatus)
    response_time_ms: Optional[int] = sqlmodel.Field(default=None)
    error_message: Optional[str] = sqlmodel.Field(default=None)
    created_at: datetime = sqlmodel.Field(default_factory=datetime.utcnow, index=True)

# Cache Entries
class CacheEntry(sqlmodel.SQLModel, table=True):
    __tablename__ = "cache_entries"

    id: int = sqlmodel.Field(default=None, primary_key=True)
    cache_key: str = sqlmodel.Field(default=None, max_length=500, unique=True, index=True)
    user_id: str = sqlmodel.Field(default=None, max_length=255, index=True)
    provider: Provider = sqlmodel.Field(default=None, max_length=20) # TODO: Check choices=list(Provider)
    endpoint: str = sqlmodel.Field(default=None, max_length=200)
    data: Dict[str, Any] = sqlmodel.Field(default_factory=dict) # TODO: Check JSON type
    expires_at: datetime = sqlmodel.Field(default=None, index=True)
    created_at: datetime = sqlmodel.Field(default_factory=datetime.utcnow)
    last_accessed: datetime = sqlmodel.Field(default_factory=datetime.utcnow)

# Rate Limiting
class RateLimitBucket(sqlmodel.SQLModel, table=True):
    __tablename__ = "rate_limit_buckets"

    id: int = sqlmodel.Field(default=None, primary_key=True)
    user_id: str = sqlmodel.Field(default=None, max_length=255, index=True)
    provider: Provider = sqlmodel.Field(default=None, max_length=20) # TODO: Check choices=list(Provider)
    bucket_type: str = sqlmodel.Field(default=None, max_length=50)  # "user_hourly", "provider_daily", etc.
    current_count: int = sqlmodel.Field(default=0)
    window_start: datetime = sqlmodel.Field(default=None, index=True)
    last_reset: datetime = sqlmodel.Field(default_factory=datetime.utcnow)
```

### 5.2. Pydantic Response Models

```python
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# Unified Email Models
class EmailAddress(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class EmailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[EmailAddress] = None
    to_addresses: List[EmailAddress] = []
    cc_addresses: List[EmailAddress] = []
    bcc_addresses: List[EmailAddress] = []
    date: datetime
    labels: List[str] = []
    is_read: bool = False
    has_attachments: bool = False
    # Provenance Information
    provider: Provider
    provider_message_id: str
    account_email: EmailStr  # Which account this message belongs to
    account_name: Optional[str] = None  # Display name for the account
    
class EmailThread(BaseModel):
    id: str
    subject: Optional[str] = None
    messages: List[EmailMessage]
    participant_count: int
    last_message_date: datetime
    is_read: bool = False
    providers: List[Provider]

# Unified Calendar Models
class CalendarEvent(BaseModel):
    id: str
    calendar_id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    location: Optional[str] = None
    attendees: List[EmailAddress] = []
    organizer: Optional[EmailAddress] = None
    status: str = "confirmed"  # confirmed, tentative, cancelled
    visibility: str = "default"  # default, public, private
    # Provenance Information
    provider: Provider
    provider_event_id: str
    account_email: EmailStr  # Which account this calendar belongs to
    account_name: Optional[str] = None  # Display name for the account
    calendar_name: str  # Name of the specific calendar
    created_at: datetime
    updated_at: datetime

class Calendar(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    is_primary: bool = False
    access_role: str  # owner, reader, writer, etc.
    # Provenance Information
    provider: Provider
    provider_calendar_id: str
    account_email: EmailStr  # Which account this calendar belongs to
    account_name: Optional[str] = None  # Display name for the account

class FreeBusyInfo(BaseModel):
    calendar_id: str
    busy_times: List[Dict[str, datetime]]  # [{"start": datetime, "end": datetime}]
    # Provenance Information
    provider: Provider
    account_email: EmailStr  # Which account this calendar belongs to
    calendar_name: str  # Name of the specific calendar

# Unified File Models
class DriveFile(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: datetime
    modified_time: datetime
    web_view_link: Optional[str] = None
    download_link: Optional[str] = None
    thumbnail_link: Optional[str] = None
    parent_folder_id: Optional[str] = None
    is_folder: bool = False
    # Provenance Information
    provider: Provider
    provider_file_id: str
    account_email: EmailStr  # Which account this file belongs to
    account_name: Optional[str] = None  # Display name for the account

# API Response Models
class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str

class PaginatedResponse(BaseModel):
    items: List[Any]
    total_count: Optional[int] = None
    next_page_token: Optional[str] = None
    has_more: bool = False
```

---

## 6. Caching Strategy

### 6.1. Cache Layers
- **Redis L1 Cache**: Fast, frequently accessed data (15-30 min TTL)
- **Database L2 Cache**: Persistent cache for expensive API calls (60+ min TTL)
- **Application Cache**: In-memory cache for configuration and tokens (5-15 min TTL)

### 6.2. Cache Keys
```python
def generate_cache_key(user_id: str, provider: str, endpoint: str, params: Dict) -> str:
    """Generate consistent cache keys"""
    param_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    return f"office_service:{user_id}:{provider}:{endpoint}:{param_hash}"
```

### 6.3. Cache Invalidation
- **Time-based**: TTL expiration for all cached data
- **Event-based**: Invalidation on data modification operations
- **Manual**: Admin endpoints for cache clearing during issues
- **Version-based**: Schema version tags for safe cache migration

---

## 7. Error Handling

### 7.1. Standardized Error Format
```python
class ApiError(BaseModel):
    type: str  # "validation_error", "auth_error", "provider_error", etc.
    message: str
    details: Optional[Dict[str, Any]] = None
    provider: Optional[Provider] = None
    retry_after: Optional[int] = None  # seconds
    request_id: str
```

### 7.2. Error Types
- **validation_error**: Invalid request parameters or format
- **auth_error**: Authentication or authorization failures
- **provider_error**: External API errors from Google/Microsoft
- **rate_limit_error**: Rate limiting from providers or internal limits
- **timeout_error**: Request timeouts or slow responses
- **internal_error**: Unexpected server errors
- **integration_error**: User integration issues (disconnected, expired)

### 7.3. Retry Logic
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    reraise=True
)
async def api_call_with_retry(self, method: str, url: str, **kwargs):
    """API call with exponential backoff retry"""
    pass
```

---

## 8. Performance Optimization

### 8.1. Parallel Processing
- Concurrent API calls for unified endpoints
- Async/await for all I/O operations
- Connection pooling for HTTP clients
- Background task processing for non-critical operations

### 8.2. Response Optimization
- Response compression (gzip) for large payloads
- Streaming responses for large datasets
- Pagination for list endpoints
- Field selection to reduce response size

### 8.3. Monitoring and Metrics
- Response time tracking per endpoint and provider
- Error rate monitoring with alerting
- Cache hit rate analysis and optimization
- API quota usage monitoring and forecasting

---

## 9. Deployment Configuration

### 9.1. Environment Variables
```python
# Service Configuration
SERVICE_NAME = "office-service"
SERVICE_VERSION = "1.0.0"
LOG_LEVEL = "INFO"
DEBUG = False

# Database
DB_URL_OFFICE = "postgresql://user:password@host:5432/briefly"

# Redis
REDIS_URL = "redis://redis:6379/0"

# Service Dependencies
USER_MANAGEMENT_SERVICE_URL = "http://user-management-service:8000"
SERVICE_API_KEY = "secure-service-key"

# External APIs
GOOGLE_CLIENT_ID = "google-oauth-client-id"
GOOGLE_CLIENT_SECRET = "google-oauth-client-secret"
MICROSOFT_CLIENT_ID = "microsoft-oauth-client-id"
MICROSOFT_CLIENT_SECRET = "microsoft-oauth-client-secret"

# Rate Limiting
DEFAULT_RATE_LIMIT_PER_HOUR = 1000
PREMIUM_RATE_LIMIT_PER_HOUR = 5000

# Caching
DEFAULT_CACHE_TTL_SECONDS = 900  # 15 minutes
MAX_CACHE_SIZE_MB = 512
```

### 9.2. Health Checks
```python
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    checks = {
        "database": await check_database_connection(),
        "redis": await check_redis_connection(),
        "user_management_service": await check_service_connection(USER_MANAGEMENT_SERVICE_URL),
        "google_api": await check_google_api_status(),
        "microsoft_api": await check_microsoft_api_status()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

---

## 10. Testing Strategy

### 10.1. Unit Tests
- Provider-specific API client testing with mocked responses
- Data normalization testing with sample provider data
- Cache manager testing with Redis mock
- Rate limiter testing with various scenarios
- Error handling testing for all error types

### 10.2. Integration Tests
- End-to-end API testing with test accounts
- Service-to-service communication testing
- Database migration and schema testing
- Cache invalidation and consistency testing
- Performance testing with concurrent requests

### 10.3. Mock Data
```python
# Test fixtures for provider responses
GOOGLE_GMAIL_MESSAGE_RESPONSE = {
    "id": "test_message_id",
    "threadId": "test_thread_id",
    "labelIds": ["INBOX", "UNREAD"],
    "snippet": "Test email content...",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Test Subject"},
            {"name": "From", "value": "test@example.com"},
            {"name": "Date", "value": "Tue, 1 Jan 2024 12:00:00 +0000"}
        ]
    }
}
```

---

## 11. Areas of Concern / Open Questions

### 11.1. Rate Limiting Strategy
- **Question**: How should we handle rate limiting when users have multiple integrations (Google + Microsoft)?
- **Options**: 
  - Separate rate limits per provider
  - Combined rate limit across all providers
  - Dynamic rate limiting based on user tier
- **Recommendation**: Need input on business requirements and user tiers

### 11.2. Data Consistency
- **Question**: How should we handle data synchronization conflicts between providers?
- **Example**: Same event exists in both Google Calendar and Outlook with different details
- **Decision**: The unified endpoints return clear provenance information for all data items, including:
  - **Provider**: Which service (Google, Microsoft) the data comes from
  - **Account Email**: Which specific account the data belongs to (users may have multiple accounts per provider)
  - **Account Name**: Display name for the account
  - **Calendar Name**: For calendar events, which specific calendar within the account
  - **Provider IDs**: Original provider-specific identifiers for debugging and actions

This approach gives users full transparency about data sources and enables informed decision-making when conflicts arise. For MVP, we display all items with clear provenance rather than attempting automatic conflict resolution.

### 11.3. Webhook Integration
- **Question**: Should we implement webhooks for real-time updates from providers?
- **Benefits**: Reduced API calls, real-time data updates
- **Challenges**: Webhook verification, handling duplicates, failure recovery
- **Recommendation**: Defer to v2 unless real-time requirements are critical
- **Decision**: Defer this feature to v2.

### 11.4. File Content Processing
- **Question**: What file types should we support for content extraction?
- **Options**: 
  - Basic text files only
  - Office documents (Word, Excel, PowerPoint)
  - PDFs with OCR
  - Google Docs native format
- **Recommendation**: Need requirements for AI context injection
- **Decision**: Defer this feature to v2.

### 11.5. Search Performance
- **Question**: How should we optimize search across multiple providers?
- **Challenges**: Different search syntaxes, result ranking, response time
- **Options**:
  - Parallel search with client-side merging
  - Pre-indexed search with background sync
  - Provider-specific search endpoints
- **Recommendation**: Start with parallel search, evaluate performance

---

## 12. Implementation Phases

### 12.1. Phase 1: Core Infrastructure (MVP)
1. Basic FastAPI setup with SqlModel and Alembic
2. Token management integration with User Management Service
3. Google and Microsoft API clients (internal modules)
4. Basic unified endpoints (email, calendar, files, contacts)
5. Simple caching with Redis
6. Basic error handling and logging
7. Health check endpoints

### 12.2. Phase 2: Enhanced Features
1. Advanced data normalization and deduplication
2. Enhanced caching strategies and performance optimization
3. Comprehensive rate limiting and quota management
4. Advanced error handling and retry logic

### 12.3. Phase 3: Advanced Features
1. Webhook integration for real-time updates
2. Advanced search and filtering capabilities
3. File content extraction and processing
4. Background task processing for optimization
5. Advanced conflict resolution

### 12.4. Phase 4: Production Scale
1. Comprehensive monitoring and metrics
2. Performance optimization and load testing
3. Analytics and usage reporting
4. Advanced security features
5. Enterprise-grade reliability improvements

---

## 13. Future Enhancements

- **Additional Providers**: Slack, Zoom, Dropbox, Box integration
- **Real-time Collaboration**: WebSocket support for live data updates
- **Advanced Analytics**: Usage patterns, productivity insights
- **Machine Learning**: Smart categorization, duplicate detection
- **Offline Support**: Local caching for offline access
- **Enterprise Features**: SSO integration, admin dashboards
- **API Versioning**: Support for multiple API versions
- **Data Export**: Comprehensive data export and backup features

---

## OpenTelemetry Configuration for Google Cloud Run

### IAM Permissions
The service account used by your Cloud Run service needs permission to write traces.
- Navigate to the IAM page in the Google Cloud Console.
- Find the service account your Cloud Run service uses (by default, it's `[PROJECT_NUMBER]-compute@developer.gserviceaccount.com`).
- Grant it the "Cloud Trace Agent" role (`roles/cloudtrace.agent`).

### Environment Variables
Deploy your service with the following environment variables:
- `OTEL_TRACES_EXPORTER=gcp_trace`
- `OTEL_SERVICE_NAME=office-service` (or a unique name for your service)
- `OTEL_PYTHON_TRACER_PROVIDER=sdk_tracer_provider` (This is required for the GCP Trace Exporter)

### Deployment Command
Example `gcloud run deploy` command:
```bash
gcloud run deploy office-service \
  --image gcr.io/[PROJECT_ID]/[YOUR_IMAGE_NAME] \
  --platform managed \
  --region [YOUR_REGION] \
  --allow-unauthenticated \
  --set-env-vars="OTEL_TRACES_EXPORTER=gcp_trace" \
  --set-env-vars="OTEL_SERVICE_NAME=office-service" \
  --set-env-vars="OTEL_PYTHON_TRACER_PROVIDER=sdk_tracer_provider"
```
Replace `[PROJECT_ID]`, `[YOUR_IMAGE_NAME]`, and `[YOUR_REGION]` with your specific values.

---

## Local Development with OpenTelemetry

For local development, you can configure OpenTelemetry to print traces directly to your console. This is useful for verifying that instrumentation is working without sending data to Google Cloud Trace.

Use the following command to run your service locally with console tracing:
```bash
OTEL_TRACES_EXPORTER=console \
OTEL_SERVICE_NAME=local-office-service \
opentelemetry-instrument uvicorn services.office.app.main:app --reload --host 0.0.0.0 --port 8080
```
When you make a request to your local service, you will see trace data printed as JSON in your terminal.