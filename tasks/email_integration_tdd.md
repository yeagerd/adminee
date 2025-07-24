# Email Integration System - Test Driven Design & Task List

## System Overview
A multi-provider email integration system that processes Gmail and Microsoft email notifications to extract package tracking numbers and survey response URLs through a unified pubsub architecture.

## Test Driven Design (TDD)

### 1. Gmail Integration Tests

#### Gmail PubSub Receiver
**Test: Should receive Gmail push notifications**
- Given: Gmail sends a push notification to our endpoint
- When: The notification contains a valid history ID
- Then: The message should be published to the gmail-notifications topic
- And: The response should return 200 OK

**Test: Should handle invalid Gmail notifications**
- Given: An invalid or malformed notification is received
- When: The payload lacks required fields (history ID, email address)
- Then: The message should be rejected with appropriate logging
- And: No message should be published to pubsub

#### Gmail Sync Service
**Test: Should fetch emails using history ID**
- Given: A pubsub message with valid history ID and email address
- When: The sync service processes the message
- Then: Gmail API should be called with the correct history ID
- And: New/modified emails should be retrieved
- And: Each email should be published to the email-processing topic

**Test: Should handle Gmail API rate limits**
- Given: Gmail API returns rate limit error
- When: The sync service encounters the error
- Then: The message should be requeued with exponential backoff
- And: Appropriate metrics should be logged

**Test: Should refresh expired tokens**
- Given: Gmail API returns 401 unauthorized
- When: The sync service encounters the error
- Then: Token refresh should be attempted
- And: Original request should be retried with new token

### 2. Microsoft Integration Tests

#### Microsoft Webhook Receiver
**Test: Should receive Microsoft Graph webhook notifications**
- Given: Microsoft sends a webhook notification
- When: The notification contains valid change data
- Then: The message should be published to the microsoft-notifications topic
- And: The webhook validation should pass

**Test: Should validate Microsoft webhook signatures**
- Given: A webhook with invalid signature
- When: The signature validation fails
- Then: The request should be rejected with 401
- And: No message should be published

#### Microsoft Sync Service
**Test: Should fetch emails using change notifications**
- Given: A pubsub message with Microsoft change notification
- When: The sync service processes the message
- Then: Microsoft Graph API should be called to fetch the changed emails
- And: Each email should be published to the email-processing topic

### 3. Email Parser Tests

#### Package Tracking Detection
**Test: Should extract UPS tracking numbers**
- Given: An email containing "1Z999AA1234567890"
- When: The parser processes the email
- Then: The tracking number should be extracted
- And: The carrier should be identified as UPS
- And: A tracking event should be published

**Test: Should extract FedEx tracking numbers**
- Given: An email containing "1234 5678 9012"
- When: The parser processes the email
- Then: The tracking number should be extracted
- And: The carrier should be identified as FedEx

**Test: Should handle multiple tracking numbers**
- Given: An email with both UPS and FedEx tracking numbers
- When: The parser processes the email
- Then: Both tracking numbers should be extracted
- And: Separate events should be published for each

#### Survey URL Detection
**Test: Should extract survey URLs**
- Given: An email containing "https://survey.ourapp.com/response/abc123"
- When: The parser processes the email
- Then: The URL should be extracted and validated
- And: A survey response event should be published

**Test: Should ignore non-survey URLs**
- Given: An email with various URLs but no survey URLs
- When: The parser processes the email
- Then: No survey events should be published
- And: Other URLs should be ignored

### 4. Subscription Management Tests

#### Gmail Subscription Refresh
**Test: Should refresh Gmail watch subscription before expiry**
- Given: A Gmail watch subscription expiring in 24 hours
- When: The refresh service runs
- Then: A new watch request should be sent to Gmail API
- And: The subscription should be updated with new expiry

**Test: Should handle Gmail subscription refresh failures**
- Given: Gmail API returns error during refresh
- When: The refresh fails
- Then: Alert should be sent to monitoring system
- And: Retry should be scheduled

#### Microsoft Subscription Refresh
**Test: Should refresh Microsoft Graph subscription**
- Given: A Microsoft subscription expiring soon
- When: The refresh service runs
- Then: PATCH request should be sent to extend subscription
- And: New expiry time should be stored

### 5. Integration Tests

#### End-to-End Gmail Flow
**Test: Complete Gmail processing pipeline**
- Given: A Gmail push notification is received  
- When: The full pipeline processes the notification
- Then: Email should be fetched from Gmail
- And: Tracking numbers should be extracted
- And: Survey URLs should be identified
- And: Appropriate events should be published

#### End-to-End Microsoft Flow
**Test: Complete Microsoft processing pipeline**
- Given: A Microsoft webhook is received
- When: The full pipeline processes the notification
- Then: Email should be fetched from Graph API
- And: Content should be parsed for tracking and surveys
- And: Events should be published correctly

#### Local Development Test
**Test: Should work with local pubsub emulator**
- Given: Local pubsub emulator is running
- When: Test emails are processed
- Then: All components should work end-to-end
- And: Messages should flow through local topics

---

## Task List for Junior Software Engineer

### Phase 1: Foundation & Gmail Integration (Week 1-2)

#### Task 1.1: Project Setup
- [ ] Set up project structure with appropriate directories
- [ ] Initialize package.json/requirements.txt with dependencies
- [ ] Configure environment variables and secrets management
- [ ] Set up logging framework with structured logging
- [ ] Create Docker containers for local development
- [ ] Set up local pubsub emulator configuration

#### Task 1.2: Gmail PubSub Receiver
- [ ] Create HTTP endpoint to receive Gmail push notifications
- [ ] Implement request validation (verify push notification format)
- [ ] Add authentication/authorization for Gmail webhooks
- [ ] Implement pubsub publisher to gmail-notifications topic
- [ ] Add error handling and appropriate HTTP status codes
- [ ] Write unit tests for notification receiver
- [ ] Add integration test with mock Gmail notifications

#### Task 1.3: Gmail Sync Service
- [ ] Create pubsub subscriber for gmail-notifications topic
- [ ] Implement Gmail API client with proper authentication
- [ ] Add logic to fetch emails using history ID
- [ ] Implement incremental sync (only fetch new/changed emails)
- [ ] Add retry logic with exponential backoff
- [ ] Implement token refresh mechanism
- [ ] Write unit tests for sync service
- [ ] Add integration tests with Gmail API (using test account)

### Phase 2: Email Parser & Microsoft Integration (Week 3-4)

#### Task 2.1: Email Parser Service
- [ ] Create pubsub subscriber for email-processing topic
- [ ] Implement regex patterns for tracking number detection:
  - [ ] UPS: `1Z[0-9A-Z]{16}`
  - [ ] FedEx: `\d{4}\s?\d{4}\s?\d{4}` and `\d{12}`
  - [ ] USPS: `\d{20,22}`
- [ ] Implement URL extraction and validation for survey links
- [ ] Create event publishers for tracking and survey events
- [ ] Add email content sanitization and security measures
- [ ] Write comprehensive unit tests for all regex patterns
- [ ] Add integration tests with sample email data

#### Task 2.2: Microsoft Webhook Receiver
- [ ] Create HTTP endpoint for Microsoft Graph webhooks
- [ ] Implement webhook signature validation
- [ ] Add Microsoft-specific authentication handling
- [ ] Implement pubsub publisher to microsoft-notifications topic
- [ ] Add proper error handling and logging
- [ ] Write unit tests for webhook receiver
- [ ] Add integration tests with mock Microsoft notifications

#### Task 2.3: Microsoft Sync Service
- [ ] Create pubsub subscriber for microsoft-notifications topic
- [ ] Implement Microsoft Graph API client
- [ ] Add logic to fetch emails using change notifications
- [ ] Implement OAuth token management for Microsoft
- [ ] Add retry logic and error handling
- [ ] Write unit tests for Microsoft sync
- [ ] Add integration tests with Graph API

### Phase 3: Subscription Management (Week 5)

#### Task 3.1: Gmail Subscription Management
- [ ] Create scheduled job for subscription refresh
- [ ] Implement Gmail watch API integration
- [ ] Add subscription status monitoring
- [ ] Implement automatic re-subscription on failure
- [ ] Add alerting for subscription issues
- [ ] Write unit tests for subscription management
- [ ] Add integration tests with Gmail watch API

#### Task 3.2: Microsoft Subscription Management
- [ ] Create scheduled job for Microsoft subscription refresh
- [ ] Implement Graph API subscription management
- [ ] Add subscription lifecycle management
- [ ] Implement failure recovery mechanisms
- [ ] Add monitoring and alerting
- [ ] Write unit tests for subscription refresh
- [ ] Add integration tests with Graph API subscriptions

### Phase 4: Testing & Documentation (Week 6)

#### Task 4.1: Integration Testing
- [ ] Set up local pubsub emulator for development
- [ ] Create end-to-end test suite
- [ ] Implement test data generators for emails
- [ ] Add performance tests for high-volume scenarios
- [ ] Create load tests for webhook endpoints
- [ ] Add chaos engineering tests (network failures, API errors)
- [ ] Document test scenarios and expected outcomes

#### Task 4.2: Local Development Setup
- [ ] Create docker-compose for local development
- [ ] Set up local pubsub emulator integration
- [ ] Create mock services for external APIs
- [ ] Add development scripts and utilities
- [ ] Create sample data for testing
- [ ] Document local setup process

#### Task 4.3: Documentation & Deployment
- [ ] Write API documentation for all endpoints
- [ ] Create deployment guides and runbooks
- [ ] Document monitoring and alerting setup
- [ ] Create troubleshooting guides
- [ ] Add architecture diagrams
- [ ] Document security considerations and best practices

### Phase 5: Monitoring & Production Readiness (Week 7)

#### Task 5.1: Observability
- [ ] Add comprehensive metrics collection
- [ ] Implement distributed tracing
- [ ] Set up health check endpoints
- [ ] Add performance monitoring
- [ ] Create dashboards for system monitoring
- [ ] Set up alerting rules and notifications

#### Task 5.2: Security & Compliance
- [ ] Implement proper secret management
- [ ] Add input validation and sanitization
- [ ] Implement rate limiting on endpoints
- [ ] Add audit logging for sensitive operations
- [ ] Review and implement security best practices
- [ ] Add compliance documentation

## Success Criteria

### Technical Metrics
- [ ] 99.9% uptime for webhook endpoints
- [ ] < 30 second end-to-end processing time
- [ ] > 95% accuracy for tracking number extraction
- [ ] Zero data loss in pubsub messaging
- [ ] Successful token refresh with < 1% failure rate

### Quality Metrics
- [ ] > 90% code coverage across all services
- [ ] All integration tests passing
- [ ] Performance tests meeting SLA requirements
- [ ] Security scan with zero high-severity issues
- [ ] Complete documentation for all components

## Dependencies & Prerequisites

### External Services
- Gmail API access and push notification setup
- Microsoft Graph API permissions and webhook configuration
- Pubsub service (Google Cloud Pub/Sub or equivalent)
- Secret management service
- Monitoring and alerting infrastructure

### Development Tools
- Local pubsub emulator
- Docker for containerization
- Testing frameworks (Jest, pytest, etc.)
- API testing tools (Postman, curl)
- Code coverage tools