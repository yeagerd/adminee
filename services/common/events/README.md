# Events Module

This directory contains Pydantic models for all PubSub events used across Briefly services. These models ensure type safety and consistency when publishing and consuming messages.

## Overview

The events module provides:
- **Type-safe event schemas** for all PubSub messages
- **Distributed tracing integration** with OpenTelemetry
- **Request context tracking** for debugging and monitoring
- **Standardized metadata** across all events

## Event Types

### Email Events
- `EmailBackfillEvent` - For email backfill operations
- `EmailUpdateEvent` - For individual email updates
- `EmailBatchEvent` - For batch email operations

### Calendar Events
- `CalendarUpdateEvent` - For individual calendar event updates
- `CalendarBatchEvent` - For batch calendar operations

### Contact Events
- `ContactUpdateEvent` - For individual contact updates
- `ContactBatchEvent` - For batch contact operations

## Usage

### Publishing Events

```python
from services.common.pubsub_client import PubSubClient
from services.common.events import EmailBackfillEvent, EmailData

# Create email data
email_data = EmailData(
    id="email_123",
    thread_id="thread_456",
    subject="Test Email",
    body="Email content",
    from_address="sender@example.com",
    to_addresses=["recipient@example.com"],
    # ... other fields
)

# Create backfill event
event = EmailBackfillEvent(
    user_id="user_789",
    provider="gmail",
    emails=[email_data],
    batch_size=1,
    sync_type="backfill",
    metadata=EmailBackfillEvent.__fields__['metadata'].type_(
        source_service="office-service",
        source_version="1.0.0",
        correlation_id="backfill_job_123",
    )
)

# Publish using pubsub_client
pubsub_client = PubSubClient(service_name="office-service")
message_id = pubsub_client.publish_email_backfill(event)
```

### Consuming Events

```python
from services.common.pubsub_client import PubSubConsumer
from services.common.events import EmailBackfillEvent

def process_email_backfill(event: EmailBackfillEvent):
    """Process email backfill event"""
    print(f"Processing {len(event.emails)} emails for user {event.user_id}")
    # Process emails...

# Subscribe to topic
consumer = PubSubConsumer(service_name="vespa-loader-service")
consumer.subscribe(
    topic_name="email-backfill",
    subscription_name="vespa-loader-email-backfill",
    callback=process_email_backfill
)
```

## Distributed Tracing

All events automatically include distributed tracing context when published through the `PubSubClient`:

```python
# Tracing context is automatically added
event.metadata.trace_id  # OpenTelemetry trace ID
event.metadata.span_id   # OpenTelemetry span ID
event.metadata.request_id # Request ID that triggered the event
```

## Metadata Fields

All events include standard metadata:

- `event_id` - Unique event identifier
- `timestamp` - Event creation time
- `source_service` - Service that published the event
- `source_version` - Version of the source service
- `trace_id` - OpenTelemetry trace ID
- `span_id` - OpenTelemetry span ID
- `request_id` - Request ID that triggered the event
- `user_id` - User ID associated with the event
- `correlation_id` - Correlation ID for related events
- `tags` - Additional context tags

## Adding New Event Types

To add a new event type:

1. Create a new file in the appropriate category (e.g., `new_feature_events.py`)
2. Define the data model extending `BaseModel`
3. Define the event model extending `BaseEvent`
4. Add the new event to `__init__.py`
5. Update this README

Example:

```python
# new_feature_events.py
from .base_events import BaseEvent

class NewFeatureData(BaseModel):
    feature_id: str
    feature_name: str
    # ... other fields

class NewFeatureEvent(BaseEvent):
    feature: NewFeatureData
    action: str
    # ... other fields
```

## Testing

Run the test file to verify the events structure:

```bash
cd services/common/events
python test_events.py
```

## Migration from Legacy Format

If you're currently using the legacy dict-based PubSub messages, you can migrate gradually:

1. **Phase 1**: Use typed events for new functionality
2. **Phase 2**: Update existing publishers to use typed events
3. **Phase 3**: Update consumers to expect typed events
4. **Phase 4**: Remove legacy support

The `PubSubClient` maintains backward compatibility with legacy methods while encouraging the use of typed events.
