# Event-Driven Architecture Deployment Guide

This guide provides deployment instructions and configuration details for the new event-driven Office data architecture.

## Overview

The new architecture introduces data-type focused topics, comprehensive idempotency, and centralized subscription management. This guide covers the deployment steps, configuration, and monitoring setup.

## Prerequisites

- Google Cloud Platform project with Pub/Sub API enabled
- Redis instance (Cloud Memorystore or self-hosted)
- Vespa cluster for document indexing
- Access to Briefly services codebase

## Topic Setup

### 1. Create New Topics

Use the updated setup script to create the new data-type focused topics:

```bash
cd services/demos
python setup_pubsub.py
```

This will create the following topics:
- `emails` (replaces `email-backfill`)
- `calendars` (replaces `calendar-updates`)
- `contacts` (replaces `contact-updates`)
- `word_documents` (new)
- `sheet_documents` (new)
- `presentation_documents` (new)
- `todos` (new)

### 2. Topic Configuration

Each topic is configured with:
- **Message retention**: 7 days (default)
- **Message ordering**: Disabled (for parallel processing)
- **Schema validation**: Enabled (using Pydantic models)

## Subscription Setup

### 1. Service Subscriptions

The system uses a centralized subscription configuration in `services/common/config/subscription_config.py`. Each service subscribes only to the topics it needs:

#### Vespa Loader
- Subscribes to all data types for comprehensive indexing
- Subscription names: `vespa-loader-{topic_name}`
- Batch size: 50 messages
- Ack deadline: 120 seconds

#### Contact Discovery Service
- Subscribes to events that can contain contact information
- Topics: `emails`, `calendars`, `word_documents`, `sheet_documents`, `presentation_documents`
- Subscription names: `contact-discovery-{topic_name}`
- Batch size: 100 messages
- Ack deadline: 60 seconds

#### Meetings Service
- Subscribes to calendar events only
- Topic: `calendars`
- Subscription name: `meetings-calendars`
- Batch size: 25 messages
- Ack deadline: 60 seconds

#### Shipments Service
- Subscribes to email events only
- Topic: `emails`
- Subscription name: `shipments-emails`
- Batch size: 50 messages
- Ack deadline: 60 seconds

### 2. Subscription Creation

Subscriptions are created automatically when services start up, using the configuration from `SubscriptionConfig`. The system validates that all required subscriptions exist and creates them if missing.

## Redis Configuration

### 1. Redis Instance Setup

Ensure Redis is accessible to all services with the following configuration:

```bash
# Redis connection string format
REDIS_URL=redis://{host}:{port}/{database}

# Required Redis modules
# - No special modules required for basic functionality
# - Redis 6.0+ recommended for better performance
```

### 2. Redis Key Patterns

The system uses the following Redis key patterns:

```python
# Office data references
office:{user_id}:{doc_type}:{doc_id}

# Idempotency keys
idempotency:{hashed_key}

# Batch references
batch:{batch_id}:{correlation_id}

# Document fragments
fragment:{parent_doc_id}:{fragment_id}
```

### 3. TTL Settings

```python
TTL_SETTINGS = {
    "office": 86400 * 7,      # 7 days
    "idempotency": 86400,     # 24 hours
    "batch": 86400 * 3,       # 3 days
    "fragment": 86400 * 30,   # 30 days
}
```

## Service Deployment

### 1. Office Service

The Office service is responsible for:
- Provider integrations (Microsoft Graph, Google APIs)
- Data normalization and event publishing
- Batch sync orchestration
- Streaming webhook handling

**Environment Variables:**
```bash
# Pub/Sub
PUBSUB_PROJECT_ID={your-project-id}
PUBSUB_EMULATOR_HOST={host:port}  # For local development

# Redis
REDIS_URL={redis-connection-string}

# Provider credentials
MICROSOFT_CLIENT_ID={client-id}
MICROSOFT_CLIENT_SECRET={client-secret}
GOOGLE_CLIENT_ID={client-id}
GOOGLE_CLIENT_SECRET={client-secret}
```

**Deployment:**
```bash
cd services/office
docker build -t office-service .
docker run -p 8000:8000 office-service
```

### 2. Vespa Loader

The Vespa loader consumes all event types and indexes them in Vespa:

**Environment Variables:**
```bash
# Pub/Sub
PUBSUB_PROJECT_ID={your-project-id}
PUBSUB_EMULATOR_HOST={host:port}

# Vespa
VESPA_ENDPOINT={vespa-endpoint}
VESPA_CERT_PATH={path-to-cert}

# Redis
REDIS_URL={redis-connection-string}
```

**Deployment:**
```bash
cd services/vespa_loader
docker build -t vespa-loader .
docker run vespa-loader
```

### 3. Contact Discovery Service

The contact discovery service processes events to maintain email contact lists:

**Environment Variables:**
```bash
# Pub/Sub
PUBSUB_PROJECT_ID={your-project-id}
PUBSUB_EMULATOR_HOST={host:port}

# Redis
REDIS_URL={redis-connection-string}
```

**Deployment:**
```bash
cd services/user
docker build -t user-service .
docker run -p 8001:8001 user-service
```

## Monitoring and Observability

### 1. Pub/Sub Metrics

Monitor the following Pub/Sub metrics:
- **Message count**: Messages published/consumed per topic
- **Subscription lag**: Number of unacknowledged messages
- **Error rate**: Failed message deliveries
- **Throughput**: Messages per second

### 2. Redis Metrics

Monitor Redis performance:
- **Memory usage**: Total memory consumed
- **Connection count**: Active connections
- **Command latency**: Response times for key operations
- **Key expiration**: TTL-based cleanup effectiveness

### 3. Service Metrics

Each service exposes metrics for:
- **Event processing rate**: Events processed per second
- **Processing latency**: Time to process events
- **Error rates**: Failed event processing
- **Idempotency effectiveness**: Duplicate event detection

### 4. Logging

All services use structured logging with:
- **Trace IDs**: Distributed tracing across services
- **Correlation IDs**: Batch job tracking
- **User IDs**: User-scoped operation tracking
- **Event metadata**: Full event context for debugging

## Migration from Old Architecture

### 1. Topic Migration

The system includes a migration script to handle the transition:

```bash
cd services/demos
python migrate_pubsub_topics.py
```

This script:
- Creates new topics
- Migrates existing subscriptions
- Updates service configurations
- Provides rollback instructions

### 2. Service Updates

Update each service to use the new event models and topic names:

1. **Update imports**: Use new event models from `services.common.events.*`
2. **Update topic names**: Use new data-type focused topic names
3. **Update event handling**: Handle new event fields (`operation`, `batch_id`, `last_updated`, `sync_timestamp`)
4. **Enable idempotency**: Use `IdempotencyService` for event processing

### 3. Rollback Plan

If issues arise during migration:
1. Stop new services
2. Revert to old topic names
3. Restart old services
4. Investigate and fix issues
5. Re-attempt migration

## Testing

### 1. Local Testing

Use the Pub/Sub emulator for local development:

```bash
# Start emulator
gcloud beta emulators pubsub start --project=test-project

# Set environment
export PUBSUB_EMULATOR_HOST=localhost:8085
export PUBSUB_PROJECT_ID=test-project

# Run tests
cd services/common/tests
python -m pytest test_event_driven_architecture_integration.py -v
```

### 2. Integration Testing

The system includes comprehensive integration tests covering:
- End-to-end event flow
- Consumer scaling and isolation
- Error handling and retry mechanisms
- Unified search functionality
- Contact discovery flow
- Document chunking and fragment search
- Parent-child navigation
- Timestamp validation and data freshness

### 3. Performance Testing

Test the system under load:
- **Event publishing rate**: Maximum events per second
- **Consumer processing rate**: Maximum events processed per second
- **Redis performance**: Key operations under load
- **Vespa indexing rate**: Document indexing performance

## Troubleshooting

### Common Issues

1. **Subscription not found**
   - Check `SubscriptionConfig` configuration
   - Verify topic names match configuration
   - Ensure service has proper permissions

2. **Redis connection failures**
   - Verify `REDIS_URL` environment variable
   - Check network connectivity
   - Verify Redis instance is running

3. **Event processing failures**
   - Check event schema validation
   - Verify idempotency key generation
   - Check consumer error logs

4. **High subscription lag**
   - Increase consumer instances
   - Check consumer processing performance
   - Verify ack deadlines are appropriate

### Debug Commands

```bash
# Check Pub/Sub topics
gcloud pubsub topics list

# Check subscriptions
gcloud pubsub subscriptions list

# Monitor subscription lag
gcloud pubsub subscriptions describe {subscription-name}

# Check Redis keys
redis-cli -h {host} -p {port} KEYS "idempotency:*"

# View service logs
docker logs {service-container}
```

## Security Considerations

### 1. Access Control

- Use service accounts with minimal required permissions
- Implement network policies to restrict service-to-service communication
- Use encrypted connections for Redis and Pub/Sub

### 2. Data Privacy

- Events contain only necessary data for processing
- Large payloads are stored in Redis with appropriate TTL
- User data is isolated by `user_id` in all operations

### 3. Audit Logging

- All event processing is logged with full context
- Idempotency keys provide audit trail for duplicate detection
- Correlation IDs enable batch operation tracking

## Performance Tuning

### 1. Consumer Scaling

- Scale consumers based on topic message rates
- Use appropriate batch sizes for each service
- Monitor ack deadlines and adjust based on processing time

### 2. Redis Optimization

- Use Redis clustering for high availability
- Implement connection pooling
- Monitor memory usage and adjust TTL settings

### 3. Event Processing

- Use async processing where possible
- Implement backpressure controls
- Monitor processing latency and adjust batch sizes

## Support and Maintenance

### 1. Regular Maintenance

- Monitor Redis key expiration and cleanup
- Review Pub/Sub subscription health
- Update service configurations as needed

### 2. Updates and Upgrades

- Test new versions in staging environment
- Use blue-green deployment for zero-downtime updates
- Maintain backward compatibility during transitions

### 3. Documentation Updates

- Keep this guide updated with configuration changes
- Document new features and capabilities
- Maintain troubleshooting guides

## Conclusion

This deployment guide covers the essential aspects of deploying and maintaining the new event-driven architecture. The system provides a robust, scalable foundation for Office data processing with comprehensive idempotency, selective consumption, and unified search capabilities.

For additional support or questions, refer to the main architecture documentation and the comprehensive test suite that validates all functionality.
