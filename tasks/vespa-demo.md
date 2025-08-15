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
- [ ] Install Vespa locally (use their Docker container or create a Dockerfile)
- [ ] Create Vespa application package with streaming search configuration
- [ ] Define document schema supporting email/calendar/files/contacts data model, normalized by the office-service
- [ ] Configure per-user partitioning strategy (user_id-based routing)
- [ ] Test basic email ingestion
- [ ] Verify user isolation with sample emails

**Files to create/modify**:
- `vespa/schemas/briefly_document.sd` - Main document schema
- `vespa/services.xml` - Vespa service configuration
- `vespa/hosts.xml` - Host configuration for local setup
- `scripts/start-vespa-local.sh` - Vespa startup script

### 1.2 Create Office Router Service
**Goal**: Central routing service for office (eg. email) data distribution
- [ ] Create new service: `services/office_router/`
- [ ] Set up FastAPI service with pubsub consumer
- [ ] Implement routing logic to multiple downstream services
- [ ] Add configuration for routing rules and service endpoints
- [ ] Include error handling and retry logic
- [ ] Add health checks and monitoring endpoints

**Files to create**:
- `services/office_router/main.py` - Main FastAPI application
- `services/office_router/router.py` - Core routing logic
- `services/office_router/models.py` - Data models
- `services/office_router/settings.py` - Configuration
- `services/office_router/pubsub_consumer.py` - Pubsub integration

### 1.3 Set Up Pubsub Infrastructure
**Goal**: Message queue for backfill job → router communication
- [ ] Set up local Google Cloud Pubsub emulator
- [ ] Create topics: `email-backfill`, `email-updates`
- [ ] Create subscriptions for email router
- [ ] Test pubsub connectivity and message flow


**Files to create/modify**:
- `scripts/start-pubsub-emulator.sh` - Pubsub emulator startup
- `scripts/setup-pubsub-topics.sh` - Topic/subscription creation
- `services/common/pubsub_client.py` - Shared pubsub utilities

---

## Phase 2: Data Ingestion Pipeline

### 2.1 Create Vespa Loader Service
**Goal**: Service to consume email data and index into Vespa
- [ ] Create new service: `services/vespa_loader/`
- [ ] Implement Vespa document mapper from office service format
- [ ] Add content normalization (HTML→Markdown for emails)
- [ ] Implement embedding generation for search_text field
- [ ] Create batch indexing capabilities
- [ ] Add document deduplication and update handling

**Files to create**:
- `services/vespa_loader/main.py` - Main service
- `services/vespa_loader/vespa_client.py` - Vespa HTTP API client
- `services/vespa_loader/content_normalizer.py` - Content processing
- `services/vespa_loader/embeddings.py` - Vector embedding generation
- `services/vespa_loader/mapper.py` - Office→Vespa data mapping

### 2.2 Enhance Office Service for Backfill
**Goal**: Add backfill capabilities to office service
- [ ] Add new endpoint: `POST /api/backfill/start` for triggering backfill jobs
- [ ] Implement pagination for large email datasets
- [ ] Add configurable batch sizes and rate limiting
- [ ] Include progress tracking and resumption capability
- [ ] Add filtering options (date ranges, folders, etc.)
- [ ] Integrate with pubsub for publishing crawled emails

**Files to modify**:
- `services/office/api/backfill.py` - New backfill endpoints
- `services/office/core/email_crawler.py` - Email crawling logic
- `services/office/core/pubsub_publisher.py` - Message publishing

### 2.3 Create Backfill Job Controller
**Goal**: Orchestration service for managing backfill jobs
- [ ] Create backfill management in `services/demos/` 
- [ ] Add job status tracking and progress reporting
- [ ] Implement user-specific backfill isolation
- [ ] Add job cancellation and cleanup capabilities
- [ ] Include error recovery and restart mechanisms
- [ ] Add demo data seeding scripts

**Files to create**:
- `services/demos/backfill_manager.py` - Job orchestration
- `services/demos/README_backfill.md` - Usage documentation
- `scripts/seed-demo-data.py` - Demo data generation

---

## Phase 3: Search Integration

### 3.1 Create Vespa Query Service
**Goal**: Query interface for hybrid search capabilities
- [ ] Create query service: `services/vespa_query/`
- [ ] Implement hybrid search (BM25 + vector similarity)
- [ ] Add user isolation filtering to all queries
- [ ] Support faceting by source_type, provider, date ranges
- [ ] Implement result ranking and relevance tuning
- [ ] Add query analytics and performance monitoring

**Files to create**:
- `services/vespa_query/main.py` - Query service
- `services/vespa_query/search_engine.py` - Core search logic
- `services/vespa_query/query_builder.py` - YQL query construction
- `services/vespa_query/result_processor.py` - Result formatting

### 3.2 Enhance Chat Service for Vespa Integration
**Goal**: Integrate Vespa search into chat workflows
- [ ] Add Vespa search tools to existing agents
- [ ] Create user-data search tool using Vespa instead of office service
- [ ] Implement semantic search capabilities for chat queries
- [ ] Add mixed result presentation (emails + calendar + files + contacts + ...)
- [ ] Include relevance scoring and snippet generation
- [ ] Maintain fallback to office service to read a specific email, eg.

**Files to modify**:
- `services/chat/agents/llm_tools.py` - Add Vespa search tools
- `services/chat/agents/email_agent.py` - Integrate Vespa search
- `services/chat/service_client.py` - Add Vespa query client

---

## Phase 4: Demo Implementation

### 4.1 Create Vespa Demo Scripts
**Goal**: End-to-end demo showcasing Vespa capabilities
- [ ] Create comprehensive demo: `services/demos/vespa_full.py`
- [ ] Implement data seeding for Microsoft and Google test accounts
- [ ] Add demo queries showcasing hybrid search capabilities
- [ ] Include performance benchmarking and comparison tools
- [ ] Add data quality validation and verification
- [ ] Create cleanup and teardown procedures

**Files to create**:
- `services/demos/vespa_full.py` - Main demo script
- `services/demos/README_vespa_demo.md` - Demo documentation
- `services/demos/demo_queries.py` - Predefined demo queries
- `scripts/vespa-demo-setup.sh` - Automated demo setup

### 4.2 Create Chatbot Demo Enhancement
**Goal**: Enhanced chat experience using Vespa data
- [ ] Create specialized demo: `services/demos/vespa_chat.py`
- [ ] Implement semantic search queries through chat interface
- [ ] Add mixed result types in chat responses
- [ ] Include relevance explanations and source attribution
- [ ] Support follow-up questions and refinement
- [ ] Add comparison mode (office service vs Vespa results)

**Files to create**:
- `services/demos/vespa_chat.py` - Vespa-powered chat demo
- `services/demos/README_vespa_chat.md` - Chat demo documentation

---

## Phase 5: Integration and Testing

### 5.1 End-to-End Integration Testing
**Goal**: Verify complete data flow from office service to Vespa to chat
- [ ] Create integration test suite
- [ ] Test backfill job → pubsub → router → Vespa loader flow
- [ ] Verify data consistency and deduplication
- [ ] Test user isolation and security
- [ ] Validate search relevance and performance
- [ ] Test error handling and recovery scenarios

**Files to create**:
- `tests/integration/test_vespa_flow.py` - E2E tests
- `tests/integration/test_data_consistency.py` - Data validation tests

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
