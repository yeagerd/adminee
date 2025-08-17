# Data Router Service Design Document

## Overview
The Data Router Service is a centralized message processing and routing service that consumes messages from Google Cloud Pub/Sub topics and routes them to appropriate downstream services. It serves as the central nervous system for data processing, handling email processing, shipment tracking, meeting poll responses, and real-time client communication.

## Architecture Goals
- **Centralized Message Routing**: Single point of entry for all data processing
- **Real-time Communication**: WebSocket/SSE support for frontend updates
- **Scalable Processing**: Independent scaling of different processors
- **Fault Tolerance**: Retry logic, dead letter queues, and error handling
- **Observability**: Comprehensive logging, metrics, and monitoring

## Current State Analysis
- **Vespa Loader Service**: Currently handles Pub/Sub consumption and Vespa indexing
- **Office Router Service**: Has basic Pub/Sub consumer functionality
- **Pub/Sub Topics**: `email-backfill`, `calendar-updates`, `contact-updates`
- **Existing Processors**: Email parsing, meeting poll responses, shipment tracking

## Proposed Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Office        │    │   Email Sync    │    │   Other         │
│   Service       │    │   Service       │    │   Services      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      Pub/Sub Topics      │
                    │  • email-backfill        │
                    │  • calendar-updates      │
                    │  • contact-updates       │
                    │  • shipment-updates      │
                    │  • meeting-responses     │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     Data Router          │
                    │   (Core Service)         │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
│   Vespa Indexer   │  │   Email          │  │   Calendar       │
│   (Vespa Loader)  │  │   Processor      │  │   Processor      │
└───────────────────┘  └───────────────────┘  └───────────────────┘
          │                       │                       │
          │              ┌────────▼────────┐              │
          │              │   Meeting Poll  │              │
          │              │   Response      │              │
          │              │   Processor     │              │
          │              └────────▼────────┘              │
          │                       │                       │
          │              ┌────────▼────────┐              │
          │              │   Shipment      │              │
          │              │   Tracker       │              │
          │              └────────▼────────┘              │
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   WebSocket/SSE          │
                    │   Manager                 │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   Frontend Clients       │
                    │   (Real-time Updates)    │
                    └───────────────────────────┘
```

## Core Components

### 1. Message Router
- **Purpose**: Routes incoming Pub/Sub messages to appropriate processors
- **Features**: Message validation, content-based routing, priority queuing
- **Input**: Pub/Sub messages from various topics
- **Output**: Dispatched messages to specialized processors

### 2. WebSocket/SSE Manager
- **Purpose**: Manages real-time connections with frontend clients
- **Features**: Connection pooling, message broadcasting, client authentication
- **Input**: Updates from various processors
- **Output**: Real-time updates to connected clients

### 3. Processor Orchestrator
- **Purpose**: Coordinates processing across different specialized services
- **Features**: Workflow management, error handling, retry logic
- **Input**: Routed messages from message router
- **Output**: Processed results and client notifications

## Message Flow

### Email Processing Flow
1. **Email arrives** → Published to `email-backfill` topic
2. **Data Router** receives message and routes to Email Processor
3. **Email Processor** parses content and extracts relevant data
4. **Shipment Detection** → If shipment email, route to Shipment Tracker
5. **Meeting Poll Detection** → If poll response, route to Meeting Processor
6. **Vespa Indexing** → Route to Vespa Indexer for search indexing
7. **Client Updates** → Send real-time updates via WebSocket/SSE

### Shipment Tracking Flow
1. **Shipment email detected** → Route to Shipment Tracker
2. **Tracking number extraction** → Parse and validate tracking info
3. **Carrier detection** → Identify shipping carrier
4. **Status updates** → Fetch current shipment status
5. **Client notification** → Send real-time updates to frontend
6. **Data persistence** → Store tracking events and status

### Meeting Poll Response Flow
1. **Poll response email** → Route to Meeting Poll Processor
2. **Response parsing** → Extract slot preferences and comments
3. **Participant validation** → Verify sender is valid participant
4. **Response processing** → Update poll results and participant status
5. **Client notification** → Send real-time updates to meeting organizers
6. **Data persistence** → Store responses in meetings database

## Pub/Sub Topic Structure

### Existing Topics
- `email-backfill` - Raw email data for processing
- `calendar-updates` - Calendar event updates
- `contact-updates` - Contact information updates

### New Topics
- `shipment-updates` - Shipment status and tracking updates
- `meeting-responses` - Meeting poll response processing
- `client-notifications` - Real-time client updates

## WebSocket/SSE Design

### Connection Management
- **Authentication**: JWT token validation for secure connections
- **Connection Pooling**: Efficient management of multiple client connections
- **Room-based Broadcasting**: Organize clients by user, organization, or context

### Message Types
- **Shipment Updates**: Real-time tracking status changes
- **Meeting Responses**: Poll response notifications
- **Email Processing**: Status updates for email operations
- **System Events**: Service health and maintenance notifications

### Client Subscription Model
- **User-specific**: Personal updates and notifications
- **Organization-wide**: Shared updates across team members
- **Context-specific**: Meeting-specific or shipment-specific updates

## Data Models

### Message Envelope
```python
class MessageEnvelope(BaseModel):
    message_id: str
    timestamp: datetime
    source_topic: str
    message_type: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    priority: int = 0
    retry_count: int = 0
```

### Processing Result
```python
class ProcessingResult(BaseModel):
    success: bool
    processor_name: str
    result_data: Dict[str, Any]
    error_message: Optional[str]
    processing_time: float
    timestamp: datetime
```

### Client Notification
```python
class ClientNotification(BaseModel):
    notification_id: str
    user_id: str
    notification_type: str
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    read: bool = False
```

## Error Handling & Resilience

### Retry Logic
- **Exponential Backoff**: Progressive delay between retry attempts
- **Max Retries**: Configurable retry limits per message type
- **Dead Letter Queue**: Failed messages sent to DLQ for manual review

### Circuit Breaker
- **Service Health Monitoring**: Track processor health and availability
- **Automatic Fallback**: Route messages to alternative processors when needed
- **Graceful Degradation**: Continue processing other message types during failures

### Monitoring & Alerting
- **Message Processing Metrics**: Throughput, latency, error rates
- **Service Health Checks**: Processor availability and performance
- **Alert Thresholds**: Automatic notifications for critical issues

## Security Considerations

### Authentication & Authorization
- **API Key Validation**: Verify service-to-service communication
- **JWT Token Validation**: Secure WebSocket/SSE connections
- **Role-based Access**: Different permissions for different client types

### Data Privacy
- **Message Encryption**: Encrypt sensitive data in transit
- **Access Logging**: Audit trail for all data access
- **Data Retention**: Configurable retention policies for processed messages

## Performance & Scalability

### Horizontal Scaling
- **Stateless Design**: Multiple instances can run simultaneously
- **Load Balancing**: Distribute message processing across instances
- **Auto-scaling**: Automatic scaling based on message queue depth

### Caching Strategy
- **Redis Integration**: Cache frequently accessed data
- **Connection Pooling**: Efficient database and external service connections
- **Message Batching**: Process messages in batches for efficiency

### Resource Management
- **Memory Optimization**: Efficient message processing and garbage collection
- **Connection Limits**: Prevent resource exhaustion from too many connections
- **Rate Limiting**: Control processing speed to prevent overwhelming downstream services

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Transform vespa_loader service to data_router
- [ ] Implement message routing framework
- [ ] Set up basic Pub/Sub consumer
- [ ] Create processor interface and base classes

### Phase 2: Processor Implementation (Week 3-4)
- [ ] Implement Email Processor
- [ ] Implement Shipment Tracker
- [ ] Implement Meeting Poll Response Processor
- [ ] Implement Vespa Indexer (extracted from current vespa_loader)

### Phase 3: Real-time Communication (Week 5-6)
- [ ] Implement WebSocket/SSE Manager
- [ ] Add client connection management
- [ ] Implement real-time notification system
- [ ] Add authentication and security

### Phase 4: Integration & Testing (Week 7-8)
- [ ] Integrate with existing services
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation and deployment

## Technology Stack

### Backend
- **FastAPI**: High-performance web framework
- **Google Cloud Pub/Sub**: Message queuing and delivery
- **WebSockets**: Real-time bidirectional communication
- **Redis**: Caching and connection management
- **PostgreSQL**: Data persistence (via existing services)

### Frontend Integration
- **WebSocket Client**: Real-time updates in React components
- **SSE Fallback**: Server-sent events for browsers without WebSocket support
- **Connection Management**: Automatic reconnection and error handling

### Monitoring & Observability
- **OpenTelemetry**: Distributed tracing and metrics
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and alerting
- **Structured Logging**: JSON-formatted logs for analysis

## Success Metrics

### Performance Metrics
- **Message Processing Latency**: < 100ms for 95% of messages
- **Throughput**: > 1000 messages/second per instance
- **Error Rate**: < 1% message processing failures
- **Client Connection Stability**: > 99.9% uptime

### Business Metrics
- **Real-time Update Delivery**: < 500ms from event to client notification
- **Shipment Tracking Accuracy**: > 95% successful tracking updates
- **Meeting Response Processing**: < 1 second from email to database update
- **User Engagement**: Increased real-time feature usage

## Risk Assessment

### Technical Risks
- **Message Processing Bottlenecks**: Mitigated by horizontal scaling
- **WebSocket Connection Limits**: Mitigated by connection pooling and load balancing
- **Data Consistency**: Mitigated by transaction management and retry logic

### Operational Risks
- **Service Dependencies**: Mitigated by circuit breakers and fallback mechanisms
- **Data Loss**: Mitigated by persistent message queues and dead letter queues
- **Performance Degradation**: Mitigated by monitoring and auto-scaling

## Conclusion

The Data Router Service provides a robust, scalable foundation for centralized message processing and real-time communication. By consolidating message routing, processing orchestration, and client communication into a single service, we achieve better performance, reliability, and maintainability while enabling new real-time features for the frontend.

The phased implementation approach minimizes risk and allows for iterative validation of the architecture. The service will serve as the central nervous system for data processing across the Briefly platform, enabling new features and improving existing functionality.
