# Briefly - Backend Architecture Design

## Overview
Next.js API routes serve as the gateway layer, handling authentication and routing to independent FastAPI services deployed on Cloud Run.

## Architecture Flow
```
Client ↔ Next.js (Frontend + API Routes) ↔ [Service Auth] ↔ Cloud Run Services
```

## Gateway Layer (Next.js API Routes)

### Responsibilities
- Validate Clerk sessions (built-in SDK)
- Handle OAuth flows for Google/Microsoft integrations
- Route requests to appropriate backend services
- Request/response transformation and error handling
- Rate limiting and request logging

### Benefits
- No CORS configuration needed
- Seamless Clerk integration with webhooks
- Better OAuth UX (no external redirects)
- TypeScript end-to-end

## Backend Services (FastAPI on Cloud Run)

### 1. User Management Service
- **Purpose**: User profiles and integration token storage
- **Responsibilities**:
  - **User Preferences**: UI settings (theme, timezone), default calendars, email signatures, AI chat preferences, notification settings, privacy controls
  - **OAuth Token Management**: Encrypted storage of Google/Microsoft tokens (access, refresh, scopes), automatic token refresh, secure token retrieval for other services
  - **User Lifecycle**: Account creation/deletion, integration connection/disconnection, data export/retention policies
  - **Security**: User-specific encryption keys, token revocation, audit logging of sensitive operations
- **Auth**: Receives user ID from Next.js via service-to-service auth
- **Data Model**: Users table, UserPreferences table, EncryptedTokens table, UserSessions table

### 2. Office Service
- **Purpose**: External API interactions (Google/Microsoft)
- **Responsibilities**:
  - **Google APIs**: Gmail (read/send emails), Calendar (events, availability), Drive (file access, search), Contacts (address book sync)
  - **Microsoft APIs**: Outlook (email operations), Calendar (Office 365 events), OneDrive (file storage), Graph API (user data)
  - **API Management**: Rate limiting, error handling, retry logic, response caching, quota monitoring
  - **Data Normalization**: Convert different API responses to consistent internal formats, handle API version differences
  - **Token Handling**: Retrieve tokens from User Management Service, handle token refresh failures, scope validation
- **Dependencies**: User Management Service for token retrieval
- **Performance**: Response caching (15-30 minutes), batch API calls where possible, async processing for non-critical updates

### 3. AI Chat Service
- **Purpose**: AI conversation and context management
- **Responsibilities**:
  - **LLM Integration**: OpenAI GPT-4/Claude API calls, model selection based on user preferences, streaming response handling
  - **Context Management**: Inject relevant calendar events, recent emails, document snippets into prompts, maintain conversation history with context pruning
  - **Conversation Storage**: Chat threads, message history, user feedback (thumbs up/down), conversation search and retrieval
  - **Response Processing**: Token streaming via SSE, response formatting (markdown, code blocks), error handling and fallbacks
  - **Personalization**: Learn user communication patterns, adapt response style, remember user preferences within conversations
- **Dependencies**: Integration Service for context data, Usage Service for LLM tracking
- **Data Model**: Conversations table, Messages table, ContextSnippets table, UserFeedback table

### 4. Content Service
- **Purpose**: Notes, docs, and content management
- **Responsibilities**:
  - **Document Management**: Rich text notes, markdown documents, file attachments, document templates, version history
  - **Search & Discovery**: Full-text search, vector embeddings for semantic search, tag-based organization, recent/favorites
  - **Collaboration**: Document sharing, comment threads, real-time editing status, permission management
  - **Sync Integration**: Two-way sync with Google Drive/OneDrive, conflict resolution, selective sync preferences
  - **AI Features**: Document summarization, auto-tagging, content suggestions, writing assistance
- **Dependencies**: Integration Service for Google Drive/OneDrive sync
- **Data Model**: Documents table, DocumentVersions table, Tags table, DocumentShares table, Comments table

### 8. Email Service
- **Purpose**: Asynchronous email operations
- **Responsibilities**:
  - **Email Operations**: Send emails via Gmail/Outlook APIs, handle attachments, manage email threads, track delivery status
  - **Template Management**: Email templates for different use cases, personalization variables, A/B testing support
  - **Queue Processing**: Background job processing (Celery/RQ), retry logic for failed sends, priority queue for urgent emails
  - **Analytics**: Open/click tracking (where permitted), delivery success rates, bounce handling, unsubscribe management
  - **AI Integration**: Email drafting assistance, smart replies, sentiment analysis, auto-categorization
- **Dependencies**: User Management Service for tokens, Usage Service for tracking
- **Data Model**: EmailJobs table, EmailTemplates table, EmailStatus table, EmailAnalytics table

### 7. Usage Service
- **Purpose**: Usage tracking, metering, and abuse detection
- **Responsibilities**:
  - **Usage Tracking**: API call counts/costs per service, LLM token consumption (input/output), storage usage, email send volume
  - **Rate Limiting**: Enforce daily/monthly quotas, temporary throttling for abuse, premium user priority queues
  - **Analytics**: Usage dashboards, cost analysis, user behavior patterns, service performance metrics
  - **Abuse Detection**: Unusual API spikes, token farming patterns, automated behavior detection, account flagging
  - **Billing Foundation**: Usage-based pricing calculations, premium feature metering, invoice generation data
- **Dependencies**: Called by all services for usage logging
- **Data Model**: UsageEvents table, UserQuotas table, ServiceMetrics table, AbuseFlags table

### 8. Calendar Service
- **Purpose**: Calendar data aggregation and management
- **Responsibilities**:
  - **Multi-Source Sync**: Aggregate Google Calendar, Outlook, iCal feeds, handle sync conflicts, maintain sync status per calendar
  - **Event Management**: Create/edit/delete events across platforms, handle recurring events, timezone management, attendee management
  - **Availability Logic**: Calculate free/busy times, meeting suggestions, conflict detection, travel time considerations
  - **Smart Features**: Meeting insights (frequency, duration patterns), automatic scheduling, calendar analytics, time blocking suggestions
  - **Notifications**: Event reminders, schedule changes, meeting prep notifications
- **Dependencies**: Integration Service for calendar data
- **Data Model**: Calendars table, Events table, Availability table, MeetingInsights table, CalendarSync table

## Authentication & Security

### Client-to-Gateway (Next.js)
- Clerk session validation (built-in)
- CSRF protection via Next.js
- Secure cookie handling

### Gateway-to-Services
- Service-to-service authentication via API keys or JWT
- User context passed in request headers
- Request signing for sensitive operations

### OAuth Flow
1. User initiates OAuth in Next.js frontend
2. Next.js API route handles OAuth redirect
3. Tokens stored via User Management Service
4. OAuth state managed in Next.js session

## Infrastructure

### Database
- **Primary**: PostgreSQL (shared across services)
- **Schemas**: Service-specific with clear boundaries
- **Migrations**: Per-service migration management

### Caching & Queues
- **Redis**: Caching + message queue backend
- **Celery/RQ**: Background job processing for async tasks

### File Storage
- **Primary**: Google Cloud Storage or AWS S3
- **CDN**: Cloudflare for static assets

### Deployment
- **Frontend**: Vercel (Next.js)
- **Backend**: Google Cloud Run (auto-scaling FastAPI services)
- **Database**: Google Cloud SQL or AWS RDS
- **Cache/Queue**: Redis Cloud or Google Memorystore

## Real-time Streaming (SSE for MVP)

### LLM Response Streaming
```
Client EventSource ↔ Next.js API Route ↔ AI Chat Service
```

**Implementation**:
- Client opens EventSource connection to `/api/chat/stream`
- Next.js validates Clerk session (standard HTTP auth)
- Next.js streams responses from AI Chat Service to client
- Automatic reconnection and error handling built-in

**Benefits for MVP**:
- Simple authentication (reuses existing Clerk session)
- No WebSocket complexity or connection management
- Built-in browser reconnection on network issues
- Standard HTTP request/response pattern

### Code Flow
1. Client sends chat message via POST to `/api/chat`
2. Next.js starts streaming response via GET to `/api/chat/stream/{chatId}`
3. AI Chat Service streams tokens back through Next.js
4. Client renders tokens in real-time via EventSource

## Service Communication

### Synchronous
- Next.js → Backend services via HTTP/REST
- Inter-service communication for real-time operations
- Circuit breaker pattern for resilience

### Asynchronous
- Background jobs via Redis queues
- Event-driven updates between services
- Webhook processing from external APIs

### Real-time Streaming
- Server-sent events for LLM response streaming
- Redis pub/sub for future multi-user collaboration features

## Usage Tracking Strategy

### What to Track
**Per User/Per Service**:
- API call counts and response times
- LLM tokens (input/output) and associated costs
- Integration API calls (Google/Microsoft quotas)
- Storage usage (documents, files)
- Email send volume

**Per Message/Chat**:
- LLM model used and token consumption
- Context retrieval costs (embeddings, search)
- Response generation time and success rate

### Implementation Pattern
```python
# In AI Chat Service
async def generate_response(user_id: str, message: str):
    start_time = time.time()
    
    # Generate response
    response = await llm_client.chat(message)
    
    # Track usage
    await usage_service.track_llm_usage(
        user_id=user_id,
        service="ai_chat",
        model="gpt-4",
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost=response.cost,
        duration_ms=int((time.time() - start_time) * 1000)
    )
    
    return response
```

## Data Flow Examples

### AI Chat with Context
1. Client sends message via Next.js API route
2. Next.js validates session, forwards to AI Chat Service
3. AI Chat Service requests context from Integration Service
4. Integration Service fetches calendar/email data using stored tokens
5. AI generates response with full context

### Async Email Sending
1. User composes email in frontend
2. Next.js API route queues email job
3. Email Service processes job in background
4. Uses stored tokens to send via Gmail/Outlook API
5. Status updates stored and pushed to frontend

## Security Considerations
- All OAuth tokens encrypted at rest with user-specific keys
- Service-to-service authentication prevents unauthorized access
- User data isolation enforced at database and service levels
- Token refresh handled automatically with fallback to re-auth
- Audit logging for all sensitive operations