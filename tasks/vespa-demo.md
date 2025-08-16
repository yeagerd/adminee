# Vespa Demo Implementation Checklist

## Overview
This document provides a step-by-step checklist to implement a Vespa-powered demo that showcases hybrid search across Microsoft and Gmail data. The demo focuses on a backfill job approach to initially populate Vespa, with the infrastructure designed to support future webhook-based real-time updates.

## Architecture Components
- **Backfill Job**: Crawls historical emails via office-service and publishes to pubsub
- **Email Router**: Routes email data to multiple services (shipments, contacts, vespa, notifications)
- **Vespa Loader**: Consumes email data and indexes into local Vespa instance
- **Chat Demo**: Enhanced chatbot that queries Vespa instead of/alongside office service calls

## Prerequisites
- Office service running with Microsoft/Google OAuth configured
- User service with demo user and valid integrations
- Local Vespa instance capability
- Pubsub emulator (from email-sync-service-new branch)

---

## Phase 1: Infrastructure Setup

### 1.1 Set Up Local Vespa Environment
**Goal**: Get a local Vespa instance running in streaming mode
- [x] Install Vespa locally (use their Docker container or create a Dockerfile)
- [x] Create Vespa application package with streaming search configuration
- [x] Define document schema supporting email/calendar/files/contacts data model, normalized by the office-service
- [x] Configure per-user partitioning strategy (user_id-based routing)
- [x] Test basic email ingestion
- [x] Verify user isolation with sample emails

**Files to create/modify**:
- `vespa/schemas/briefly_document.sd` - Main document schema
- `vespa/services.xml` - Vespa service configuration
- `vespa/hosts.xml` - Host configuration for local setup
- `scripts/start-vespa-local.sh` - Vespa startup script

### 1.2 Create Office Router Service
**Goal**: Central routing service for office (eg. email) data distribution
- [x] Create new service: `services/office_router/`
- [x] Set up FastAPI service with pubsub consumer
- [x] Implement routing logic to multiple downstream services
- [x] Add configuration for routing rules and service endpoints
- [x] Include error handling and retry logic
- [x] Add health checks and monitoring endpoints

**Files to create**:
- `services/office_router/main.py` - Main FastAPI application
- `services/office_router/router.py` - Core routing logic
- `services/office_router/models.py` - Data models
- `services/office_router/settings.py` - Configuration
- `services/office_router/pubsub_consumer.py` - Pubsub integration

### 1.3 Set Up Pubsub Infrastructure
**Goal**: Message queue for backfill job → router communication
- [x] Set up local Google Cloud Pubsub emulator
- [x] Create topics: `email-backfill`, `email-updates`
- [x] Create subscriptions for email router
- [x] Test pubsub connectivity and message flow


**Files to create/modify**:
- `scripts/start-pubsub-emulator.sh` - Pubsub emulator startup
- `scripts/setup-pubsub-topics.sh` - Topic/subscription creation
- `services/common/pubsub_client.py` - Shared pubsub utilities

---

## Phase 2: Data Ingestion Pipeline

### 2.1 Create Vespa Loader Service
**Goal**: Service to consume email data and index into Vespa
- [x] Create new service: `services/vespa_loader/`
- [x] Implement Vespa document mapper from office service format
- [x] Add content normalization (HTML→Markdown for emails)
- [x] Implement embedding generation for search_text field
- [x] Create batch indexing capabilities
- [x] Add document deduplication and update handling

**Files to create**:
- `services/vespa_loader/main.py` - Main service
- `services/vespa_loader/vespa_client.py` - Vespa HTTP API client
- `services/vespa_loader/content_normalizer.py` - Content processing
- `services/vespa_loader/embeddings.py` - Vector embedding generation
- `services/vespa_loader/mapper.py` - Office→Vespa data mapping

### 2.2 Enhance Office Service for Backfill
**Goal**: Add backfill capabilities to office service
- [x] Add new endpoint: `POST /api/backfill/start` for triggering backfill jobs
- [x] Implement pagination for large email datasets
- [x] Add configurable batch sizes and rate limiting
- [x] Include progress tracking and resumption capability
- [x] Add filtering options (date ranges, folders, etc.)
- [x] Integrate with pubsub for publishing crawled emails

**Files to modify**:
- `services/office/api/backfill.py` - New backfill endpoints
- `services/office/core/email_crawler.py` - Email crawling logic
- `services/office/core/pubsub_publisher.py` - Message publishing

### 2.3 Create Backfill Job Controller
**Goal**: Orchestration service for managing backfill jobs
- [x] Create backfill management in `services/demos/` 
- [x] Add job status tracking and progress reporting
- [x] Implement user-specific backfill isolation
- [x] Add job cancellation and cleanup capabilities
- [x] Include error recovery and restart mechanisms
- [x] Add demo data seeding scripts

**Files to create**:
- `services/demos/backfill_manager.py` - Job orchestration
- `services/demos/README_backfill.md` - Usage documentation
- `scripts/seed-demo-data.py` - Demo data generation

---

## Phase 3: Search Integration

### 3.1 Create Vespa Query Service
**Goal**: Query interface for hybrid search capabilities
- [x] Create query service: `services/vespa_query/`
- [x] Implement hybrid search (BM25 + vector similarity)
- [x] Add user isolation filtering to all queries
- [x] Support faceting by source_type, provider, date ranges
- [x] Implement result ranking and relevance tuning
- [x] Add query analytics and performance monitoring

**Files to create**:
- `services/vespa_query/main.py` - Query service
- `services/vespa_query/search_engine.py` - Core search logic
- `services/vespa_query/query_builder.py` - YQL query construction
- `services/vespa_query/result_processor.py` - Result formatting

### 3.2 Enhance Chat Service for Vespa Integration
**Goal**: Integrate Vespa search into chat workflows
- [x] Add Vespa search tools to existing agents
- [x] Create user-data search tool using Vespa instead of office service
- [x] Implement semantic search capabilities for chat queries
- [x] Add mixed result presentation (emails + calendar + files + contacts + ...)
- [x] Include relevance scoring and snippet generation
- [x] Maintain fallback to office service to read a specific email, eg.

**Files to modify**:
- `services/chat/agents/llm_tools.py` - Add Vespa search tools
- `services/chat/agents/email_agent.py` - Integrate Vespa search
- `services/chat/service_client.py` - Add Vespa query client

---

## Phase 4: Demo Implementation

### 4.1 Create Vespa Demo Scripts
**Goal**: End-to-end demo showcasing Vespa capabilities
- [x] Create comprehensive demo: `services/demos/vespa_full.py`
- [x] Implement backfill-based data seeding for Microsoft and Google test accounts
- [x] Add demo queries showcasing hybrid search capabilities
- [x] Include performance benchmarking
- [x] Add data quality validation and verification
- [x] Create cleanup and teardown procedures

**Files to create**:
- `services/demos/vespa_full.py` - Main demo script
- `services/demos/README_vespa_demo.md` - Demo documentation
- `services/demos/demo_queries.py` - Predefined demo queries
- `scripts/vespa-demo-setup.sh` - Automated demo setup

### 4.2 Create Chatbot Demo Enhancement
**Goal**: Enhanced chat experience using Vespa data
- [x] Create specialized demo: `services/demos/vespa_chat.py`
- [x] Implement semantic search queries through chat interface
- [x] Add mixed result types in chat responses
- [x] Include relevance explanations and source attribution
- [x] Support follow-up questions and refinement

**Files to create**:
- `services/demos/vespa_chat.py` - Vespa-powered chat demo
- `services/demos/README_vespa_chat.md` - Chat demo documentation

---

## Phase 5: Integration and Testing

### 5.1 End-to-End Integration Testing
**Goal**: Verify complete data flow from office service to Vespa to chat
- [x] Create integration test suite
- [x] Test backfill job → pubsub → router → Vespa loader flow
- [x] Verify data consistency and deduplication
- [x] Test user isolation and security
- [x] Validate search relevance and performance
- [x] Test error handling and recovery scenarios

**Files to create**:
- `services/vespa_query/tests/test_vespa_flow.py` - E2E tests
- `services/vespa_query/tests/test_data_consistency.py` - Data validation tests

### 5.2 Performance Optimization
**Goal**: Optimize for demo responsiveness and reliability
- [ ] Benchmark indexing performance and throughput
- [ ] Optimize query response times and relevance
- [ ] Tune batch sizes and concurrency settings
- [ ] Add caching for frequently accessed data
- [ ] Implement connection pooling and resource management
- [ ] Add monitoring dashboards and alerting
- [ ] Add monitoring and dead letter queue handling

### 5.3 Documentation and Runbook
**Goal**: Complete documentation for demo reproduction
- [ ] Create comprehensive setup guide
- [ ] Document all configuration options and environment variables
- [ ] Add troubleshooting guide for common issues
- [ ] Include demo script walkthroughs and expected outputs
- [ ] Create video or presentation materials
- [ ] Add cleanup and maintenance procedures

**Files to create**:
- `documentation/vespa-demo-setup.md` - Complete setup guide
- `documentation/vespa-demo-troubleshooting.md` - Troubleshooting guide
- `documentation/vespa-demo-walkthrough.md` - Demo script guide

---

## Demo Scenarios to Implement

### Scenario 1: Cross-Platform Email Search
- **Query**: "Quarterly planning doc and invites from last month"
- **Expected**: Mixed results showing OneDrive files and related calendar events
- **Demonstrates**: Hybrid search, cross-provider results, temporal filtering

### Scenario 2: Person-Centric Search  
- **Query**: "Threads with Alex Chen about SOW"
- **Expected**: Email threads and calendar events mentioning Alex Chen
- **Demonstrates**: Person entity recognition, thread grouping, semantic search

### Scenario 3: Semantic Document Discovery
- **Query**: "Travel receipts and expense reports"
- **Expected**: Emails with travel-related content and file attachments
- **Demonstrates**: Semantic understanding, attachment association, content classification

### Scenario 4: Time-Scoped Search
- **Query**: "Meetings next week with finance team"
- **Expected**: Calendar events with finance-related attendees
- **Demonstrates**: Temporal queries, attendee analysis, team identification

---

## Technical Considerations

### Data Model Consistency
- Use the existing (external) user_id format across all services
- Maintain provider ID mappings for traceability
- Implement proper JSON schema validation for pubsub messages
- Use UTC timestamps consistently across all services

### Security and Privacy
- Implement strict user isolation in all queries
- Encrypt sensitive data in transit and at rest
- Add audit logging for all data access
- Ensure demo data cleanup and privacy compliance

### Scalability Preparation
- Design for horizontal scaling of router and loader services
- Use async/await throughout for high concurrency
- Implement proper error handling and circuit breakers
- Add metrics and monitoring for all components

### Development Workflow
- Use feature branches for each service development
- Implement comprehensive testing for each component
- Add docker-compose configuration for local development
- Create automated CI/CD pipeline for testing

---

## Success Criteria

### Functional Requirements
- [ ] Successfully index emails from both Microsoft and Google accounts
- [ ] Demonstrate hybrid search returning relevant mixed-type results
- [ ] Show chat interface enhanced with Vespa search capabilities
- [ ] Prove user isolation and data security
- [ ] Complete end-to-end demo in under 5 minutes

### Performance Requirements
- [ ] Index 1000+ emails within 10 minutes
- [ ] Search queries return results in under 2 seconds
- [ ] Chat responses enhanced with search in under 5 seconds
- [ ] Handle concurrent demo users without degradation
- [ ] 99%+ uptime during demo periods

### Quality Requirements
- [ ] Comprehensive error handling and graceful degradation
- [ ] Complete documentation and reproducible setup
- [ ] Automated testing covering critical paths
- [ ] Clean separation of concerns between services
- [ ] Monitoring and observability for all components

---

## Implementation Timeline

### Week 1: Infrastructure (Phase 1)
- Set up Vespa local environment
- Create email router service
- Establish pubsub infrastructure

### Week 2: Data Pipeline (Phase 2)  
- Implement Vespa loader service
- Enhance office service for backfill
- Create backfill job controller

### Week 3: Search Integration (Phase 3)
- Create Vespa query service
- Enhance chat service integration
- Implement hybrid search capabilities

### Week 4: Demo and Testing (Phases 4-5)
- Create demo scripts and scenarios
- End-to-end integration testing
- Documentation and optimization

---

## Notes for Junior Engineers

### Getting Started
1. Start with Phase 1.1 (Vespa setup) to understand the core technology
2. Read the vespa-prototype.md document for architectural context
3. Examine existing office service APIs to understand data formats
4. Test with small datasets before attempting full backfill

### Common Pitfalls
- **User Isolation**: Always include user_id filters in Vespa queries
- **Data Consistency**: Ensure doc_id uniqueness across providers
- **Error Handling**: Network failures are common; implement retries
- **Resource Management**: Close HTTP connections and clean up resources

### Debugging Tips
- Use Vespa query tracing for search relevance issues
- Monitor pubsub message flow for data pipeline problems
- Check office service logs for authentication failures
- Verify demo user OAuth tokens are valid and have proper scopes

### Best Practices
- Follow existing code patterns in services/common
- Use the established logging and telemetry systems
- Add comprehensive tests for new services
- Document configuration options and environment variables
- Keep services stateless and horizontally scalable

---

## Phase 6: Service-to-Service Backfill Communication

### 6.1 Implement Internal Backfill Endpoints
**Goal**: Create service-to-service communication endpoints that bypass JWT authentication for backend jobs

#### 6.1.1 Add Internal Backfill Endpoints to Office Service
**Files to modify**: `services/office/api/backfill.py`

**New Endpoints to Add**:
- [ ] `POST /internal/backfill/start?user_id={email}` - Start backfill job for specific user
- [ ] `GET /internal/backfill/status/{job_id}?user_id={email}` - Get job status
- [ ] `DELETE /internal/backfill/{job_id}?user_id={email}` - Cancel job
- [ ] `GET /internal/backfill/status?user_id={email}` - List user's jobs

**Authentication**: API key only (no JWT required)
**User Identification**: Via `user_id` query parameter (email address)
**Security**: API key must have `backfill` permission

**Implementation Details**:
```python
@router.post("/internal/start", response_model=BackfillResponse)
async def start_internal_backfill(
    request: BackfillRequest,
    user_id: str = Query(..., description="User email address"),
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_backfill_api_key)
):
    """Internal endpoint for starting backfill jobs (service-to-service)"""
    # Validate user_id format (email)
    # Check if user exists and has valid integrations
    # Start backfill job with specified user_id
    # Return job_id and status
```

#### 6.1.2 Update BackfillRequest Model
**Files to modify**: `services/office/models/backfill.py`

**Add New Fields**:
- [ ] Add `max_emails: Optional[int]` field with validation (ge=1, le=10000)
- [ ] Add `user_id: Optional[str]` field for internal endpoints
- [ ] Update model validation and documentation

#### 6.1.3 Create Internal API Key Authentication
**Files to modify**: `services/office/core/auth.py`

**Add New API Key Type**:
- [ ] Add `api_backfill_key` configuration with `backfill` permission
- [ ] Include permissions: `backfill`, `read_emails`, `read_calendar`, `read_contacts`, `health`
- [ ] Add `verify_backfill_api_key` function for permission checking

### 6.2 Update Demo Scripts to Use Internal Endpoints

#### 6.2.1 Modify VespaBackfillDemo Class
**Files to modify**: `services/demos/vespa_backfill.py`

**Changes Required**:
- [ ] Remove user_id parameter from API calls - Use query parameter instead
- [ ] Update API endpoints - Change from `/v1/api/backfill/start` to `/internal/backfill/start`
- [ ] Add user_id to query params - Pass email as `user_id` query parameter
- [ ] Update API key - Use backfill API key instead of frontend key
- [ ] Pass `max_emails` parameter to API request

#### 6.2.2 Update API Key Configuration
**Files to modify**: `services/demos/settings_demos.py`

**Add Backfill API Key**:
- [ ] Add `api_backfill_key` property to DemoSettings class
- [ ] Update `get_api_keys()` method to include backfill key
- [ ] Set default value to `test-BACKFILL_KEY`

#### 6.2.3 Update VespaSearchDemo Class
**Files to modify**: `services/demos/vespa_search.py`

**Changes Required**:
- [ ] Use internal endpoints - Change from public API to internal endpoints
- [ ] Pass user_id as query param - Include email in query parameters
- [ ] Update API key - Use appropriate service API key

### 6.3 Update Office Service Backfill Logic

#### 6.3.1 Modify EmailCrawler to Respect max_emails
**Files to modify**: `services/office/core/email_crawler.py`

**Changes Required**:
- [ ] Accept `max_emails` parameter in `crawl_emails` method
- [ ] Respect email limit - Stop crawling after reaching max_emails
- [ ] Update progress tracking - Show progress relative to max_emails
- [ ] Add early termination logic when max_emails is reached

#### 6.3.2 Update Backfill Job Execution
**Files to modify**: `services/office/api/backfill.py`

**Changes Required**:
- [ ] Pass `max_emails` to EmailCrawler constructor
- [ ] Update progress calculation - Use max_emails for progress percentage
- [ ] Respect email limits - Stop processing after reaching max_emails
- [ ] Update job status tracking with max_emails information

### 6.4 Environment Configuration Updates

#### 6.4.1 Add Backfill API Key to Environment
**Files to modify**: `.env.example`, `docker-compose.yml`, deployment configs

**New Environment Variable**:
- [ ] Add `API_BACKFILL_KEY=your-backfill-api-key-here` to `.env.example`
- [ ] Update deployment configurations with new environment variable

#### 6.4.2 Update Docker Compose Configuration
**Files to modify**: `docker-compose.yml`

**Add Backfill API Key**:
- [ ] Add `API_BACKFILL_KEY` environment variable to office service
- [ ] Ensure environment variable is properly passed through

### 6.5 Testing and Validation

#### 6.5.1 Test Internal Endpoints
**Test Cases**:
- [ ] Valid API Key + Valid User - Should start backfill job
- [ ] Valid API Key + Invalid User - Should return 404 for user not found
- [ ] Invalid API Key + Valid User - Should return 401 unauthorized
- [ ] Missing user_id Parameter - Should return 400 bad request
- [ ] Max Emails Limit - Should respect max_emails parameter

#### 6.5.2 Test Demo Scripts
**Test Cases**:
- [ ] Email Parameter Required - Script should fail without email
- [ ] Max Emails Override - `--max-emails 5` should process only 5 emails
- [ ] Real User Authentication - Should use actual user email, not API key client name
- [ ] Progress Tracking - Should show progress relative to max_emails

#### 6.5.3 Integration Testing
**Test Cases**:
- [ ] End-to-End Flow - Demo script → Internal API → Backfill job → Pub/Sub → Vespa
- [ ] User Isolation - Different users should see only their data
- [ ] Error Handling - Invalid users, API failures, etc.
- [ ] Performance - Respect rate limits and batch sizes

### 6.6 Security Considerations

#### 6.6.1 API Key Permissions
- [ ] Backfill API Key - Limited to backfill operations only
- [ ] No User Data Access - Cannot read emails, only trigger backfill jobs
- [ ] Audit Logging - Log all backfill job requests and completions

#### 6.6.2 User Validation
- [ ] Email Format Validation - Ensure user_id is valid email format
- [ ] User Existence Check - Verify user exists before starting backfill
- [ ] Integration Validation - Check user has valid OAuth integrations

#### 6.6.3 Rate Limiting
- [ ] Per-User Limits - Prevent abuse by limiting jobs per user
- [ ] Global Limits - Prevent system overload with global job limits
- [ ] Cooldown Periods - Require time between backfill jobs

### 6.7 Migration Strategy

#### 6.7.1 Phase 1: Add Internal Endpoints
- [ ] Add new internal endpoints alongside existing ones
- [ ] Keep existing JWT-based endpoints for frontend use
- [ ] Test internal endpoints with demo scripts

#### 6.7.2 Phase 2: Update Demo Scripts
- [ ] Modify demo scripts to use internal endpoints
- [ ] Test with real user emails
- [ ] Verify max_emails parameter works correctly

#### 6.7.3 Phase 3: Deprecate Old Demo Logic
- [ ] Remove hardcoded demo user logic
- [ ] Clean up API key client name usage
- [ ] Update documentation and examples

### 6.8 Success Criteria

#### 6.8.1 Functional Requirements
- [ ] Internal backfill endpoints accept user_id as query parameter
- [ ] Demo scripts require real email addresses as first argument
- [ ] Max emails parameter is respected and passed through to EmailCrawler
- [ ] User isolation works correctly with real user emails
- [ ] API key authentication works for service-to-service communication

#### 6.8.2 Security Requirements
- [ ] Only backfill API keys can access internal endpoints
- [ ] User validation prevents unauthorized access
- [ ] Audit logging captures all backfill operations
- [ ] Rate limiting prevents abuse

#### 6.8.3 Performance Requirements
- [ ] Internal endpoints respond within 100ms
- [ ] Max emails parameter is enforced efficiently
- [ ] Progress tracking updates in real-time
- [ ] Error handling doesn't impact performance

### 6.9 Implementation Timeline

#### Week 1: Internal Endpoints
- [ ] Add internal backfill endpoints to office service
- [ ] Implement backfill API key authentication
- [ ] Add max_emails to BackfillRequest model

#### Week 2: Demo Script Updates
- [ ] Update vespa_backfill.py to use internal endpoints
- [ ] Update vespa_search.py to use internal endpoints
- [ ] Test with real user emails

#### Week 3: Integration and Testing
- [ ] End-to-end testing of backfill flow
- [ ] Performance and security validation
- [ ] Documentation updates

#### Week 4: Cleanup and Migration
- [ ] Remove old demo user logic
- [ ] Clean up API key client name usage
- [ ] Update all documentation and examples

---

## Notes for Implementation

### Key Benefits of This Approach
1. **Service-to-Service Communication** - Backend jobs can trigger backfill without JWT
2. **Real User Authentication** - Uses actual user emails instead of fake IDs
3. **Flexible Email Limits** - Command line can control max_emails per job
4. **Security** - API key-based authentication with proper permissions
5. **Scalability** - Internal endpoints designed for high-throughput backend use

### Common Pitfalls to Avoid
1. **Missing user_id Parameter** - Always validate user_id is present
2. **API Key Permissions** - Ensure backfill API key has correct permissions
3. **User Validation** - Check user exists and has valid integrations
4. **Progress Tracking** - Update progress relative to max_emails, not total emails
5. **Error Handling** - Gracefully handle invalid users and API failures

### Testing Strategy
1. **Unit Tests** - Test internal endpoint logic and validation
2. **Integration Tests** - Test complete backfill flow
3. **Security Tests** - Verify API key permissions and user isolation
4. **Performance Tests** - Ensure endpoints meet performance requirements
5. **Demo Script Tests** - Verify scripts work with real user emails

### Monitoring and Observability
1. **API Key Usage** - Track which API keys are accessing internal endpoints
2. **User Backfill Jobs** - Monitor backfill job creation and completion
3. **Error Rates** - Track failures and identify common issues
4. **Performance Metrics** - Monitor response times and throughput
5. **Security Events** - Log unauthorized access attempts and suspicious activity
