"""
Shared PubSub utilities for Briefly services with integrated logging and tracing.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Union

from google.cloud import pubsub_v1  # type: ignore[attr-defined]

from services.common.events import (
    BaseEvent,
    EmailEvent,
    CalendarEvent,
    ContactEvent,
    DocumentEvent,
    TodoEvent,
    # Keep deprecated events for backward compatibility
    CalendarBatchEvent,
    CalendarUpdateEvent,
    ContactBatchEvent,
    ContactUpdateEvent,
    EmailBackfillEvent,
    EmailBatchEvent,
    EmailUpdateEvent,
)
from services.common.logging_config import get_logger
from services.common.telemetry import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class PubSubClient:
    """Shared PubSub client for publishing messages with logging and tracing."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        emulator_host: Optional[str] = None,
        service_name: str = "unknown-service",
    ):
        self.project_id = project_id or os.getenv("PUBSUB_PROJECT_ID", "briefly-dev")
        self.service_name = service_name

        # Set up emulator if specified
        if emulator_host:
            os.environ["PUBSUB_EMULATOR_HOST"] = emulator_host
        elif "PUBSUB_EMULATOR_HOST" not in os.environ:
            # If no emulator host is specified and no emulator is configured,
            # set up the default emulator host to avoid Google credentials issues
            os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
            logger.info(
                "No Pub/Sub emulator host specified, using default: localhost:8085"
            )

        # Initialize publisher client
        try:
            self.publisher = pubsub_v1.PublisherClient()
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub publisher client: {e}")
            logger.info("Pub/Sub functionality will be disabled")
            self.publisher = None

        logger.info(
            "PubSub client initialized",
            extra={
                "project_id": self.project_id,
                "emulator_host": emulator_host,
                "service_name": self.service_name,
            },
        )

    def publish_message(
        self, topic_name: str, data: Union[Dict[str, Any], BaseEvent], **kwargs: Any
    ) -> str:
        """Publish a message to a PubSub topic with tracing and logging."""
        if not self.publisher:
            logger.warning("Pub/Sub publisher not available, message not published")
            return "disabled"

        with tracer.start_as_current_span(f"pubsub.publish.{topic_name}") as span:
            try:
                topic_path = self.publisher.topic_path(self.project_id, topic_name)

                # Handle both dict and BaseEvent types
                if isinstance(data, BaseEvent):
                    # Add tracing context to the event
                    if span.is_recording():
                        span_context = span.get_span_context()
                        data.add_trace_context(
                            trace_id=f"{span_context.trace_id:032x}",
                            span_id=f"{span_context.span_id:016x}",
                        )

                    # Convert event to dict
                    message_data = data.model_dump_json().encode("utf-8")
                    event_type = data.__class__.__name__
                else:
                    # Handle legacy dict format
                    if "timestamp" not in data:
                        data["timestamp"] = datetime.now(timezone.utc).isoformat()
                    message_data = json.dumps(data, default=str).encode("utf-8")
                    event_type = "dict"

                # Add span attributes for tracing
                span.set_attribute("pubsub.topic", topic_name)
                span.set_attribute("pubsub.project_id", str(self.project_id))
                span.set_attribute("pubsub.event_type", event_type)
                span.set_attribute("pubsub.message_size_bytes", len(message_data))

                # Publish message
                future = self.publisher.publish(topic_path, data=message_data, **kwargs)
                message_id = future.result()

                # Log success with structured data
                logger.info(
                    "Message published successfully",
                    extra={
                        "message_id": message_id,
                        "topic_name": topic_name,
                        "event_type": event_type,
                        "message_size_bytes": len(message_data),
                        "trace_id": (
                            span.get_span_context().trace_id
                            if span.is_recording()
                            else None
                        ),
                        "span_id": (
                            span.get_span_context().span_id
                            if span.is_recording()
                            else None
                        ),
                    },
                )

                return message_id

            except Exception as e:
                # Log error with context
                logger.error(
                    "Failed to publish message",
                    extra={
                        "topic_name": topic_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "trace_id": (
                            span.get_span_context().trace_id
                            if span.is_recording()
                            else None
                        ),
                        "span_id": (
                            span.get_span_context().span_id
                            if span.is_recording()
                            else None
                        ),
                    },
                )
                span.record_exception(e)
                raise

    # New event publishing methods for event-driven architecture
    def publish_email_event(
        self, event: EmailEvent, topic_name: str = "emails"
    ) -> str:
        """Publish email event with type safety."""
        logger.info(
            "Publishing email event",
            extra={
                "user_id": event.user_id,
                "email_id": event.email.id,
                "operation": event.operation,
                "batch_id": event.batch_id,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_calendar_event(
        self, event: CalendarEvent, topic_name: str = "calendars"
    ) -> str:
        """Publish calendar event with type safety."""
        logger.info(
            "Publishing calendar event",
            extra={
                "user_id": event.user_id,
                "event_id": event.event.id,
                "operation": event.operation,
                "batch_id": event.batch_id,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_contact_event(
        self, event: ContactEvent, topic_name: str = "contacts"
    ) -> str:
        """Publish contact event with type safety."""
        logger.info(
            "Publishing contact event",
            extra={
                "user_id": event.user_id,
                "contact_id": event.contact.id,
                "operation": event.operation,
                "batch_id": event.batch_id,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_document_event(
        self, event: DocumentEvent, topic_name: str = "word_documents"
    ) -> str:
        """Publish document event with type safety."""
        logger.info(
            "Publishing document event",
            extra={
                "user_id": event.user_id,
                "document_id": event.document.id,
                "operation": event.operation,
                "content_type": event.content_type,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_todo_event(
        self, event: TodoEvent, topic_name: str = "todos"
    ) -> str:
        """Publish todo event with type safety."""
        logger.info(
            "Publishing todo event",
            extra={
                "user_id": event.user_id,
                "todo_id": event.todo.id,
                "operation": event.operation,
                "batch_id": event.batch_id,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    # Deprecated methods for backward compatibility
    def publish_email_backfill(
        self, event: EmailBackfillEvent, topic_name: str = "emails"
    ) -> str:
        """Publish email backfill event with type safety (deprecated - use publish_email_event)."""
        logger.warning(
            "Using deprecated publish_email_backfill method. Use publish_email_event instead.",
            extra={
                "user_id": event.user_id,
                "provider": event.provider,
                "batch_size": event.batch_size,
                "sync_type": event.sync_type,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_email_update(
        self, event: EmailUpdateEvent, topic_name: str = "emails"
    ) -> str:
        """Publish email update event with type safety (deprecated - use publish_email_event)."""
        logger.warning(
            "Using deprecated publish_email_update method. Use publish_email_event instead.",
            extra={
                "user_id": event.user_id,
                "email_id": event.email.id,
                "update_type": event.update_type,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_email_batch(
        self, event: EmailBatchEvent, topic_name: str = "emails"
    ) -> str:
        """Publish email batch event with type safety (deprecated - use publish_email_event)."""
        logger.warning(
            "Using deprecated publish_email_batch method. Use publish_email_event instead.",
            extra={
                "user_id": event.user_id,
                "provider": event.provider,
                "batch_size": len(event.emails),
                "operation": event.operation,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_calendar_update(
        self, event: CalendarUpdateEvent, topic_name: str = "calendars"
    ) -> str:
        """Publish calendar update event with type safety (deprecated - use publish_calendar_event)."""
        logger.warning(
            "Using deprecated publish_calendar_update method. Use publish_calendar_event instead.",
            extra={
                "user_id": event.user_id,
                "event_id": event.event.id,
                "update_type": event.update_type,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_calendar_batch(
        self, event: CalendarBatchEvent, topic_name: str = "calendars"
    ) -> str:
        """Publish calendar batch event with type safety (deprecated - use publish_calendar_event)."""
        logger.warning(
            "Using deprecated publish_calendar_batch method. Use publish_calendar_event instead.",
            extra={
                "user_id": event.user_id,
                "provider": event.provider,
                "batch_size": len(event.events),
                "operation": event.operation,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_contact_update(
        self, event: ContactUpdateEvent, topic_name: str = "contacts"
    ) -> str:
        """Publish contact update event with type safety (deprecated - use publish_contact_event)."""
        logger.warning(
            "Using deprecated publish_contact_update method. Use publish_contact_event instead.",
            extra={
                "user_id": event.user_id,
                "contact_id": event.contact.id,
                "update_type": event.update_type,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    def publish_contact_batch(
        self, event: ContactBatchEvent, topic_name: str = "contacts"
    ) -> str:
        """Publish contact batch event with type safety (deprecated - use publish_contact_event)."""
        logger.warning(
            "Using deprecated publish_contact_batch method. Use publish_contact_event instead.",
            extra={
                "user_id": event.user_id,
                "provider": event.provider,
                "batch_size": len(event.contacts),
                "operation": event.operation,
                "topic_name": topic_name,
            },
        )
        return self.publish_message(topic_name, event)

    # Legacy methods for backward compatibility
    def publish_email_data(
        self, email_data: Dict[str, Any], topic_name: str = "emails"
    ) -> str:
        """Publish email data to the specified topic (legacy method)."""
        logger.warning(
            "Using legacy publish_email_data method. Consider using typed events.",
            extra={"topic_name": topic_name},
        )
        return self.publish_message(topic_name, email_data)

    def publish_calendar_data(
        self, calendar_data: Dict[str, Any], topic_name: str = "calendars"
    ) -> str:
        """Publish calendar data to the specified topic (legacy method)."""
        logger.warning(
            "Using legacy publish_calendar_data method. Consider using typed events.",
            extra={"topic_name": topic_name},
        )
        return self.publish_message(topic_name, calendar_data)

    def publish_contact_data(
        self, contact_data: Dict[str, Any], topic_name: str = "contacts"
    ) -> str:
        """Publish contact data to the specified topic (legacy method)."""
        logger.warning(
            "Using legacy publish_contact_data method. Consider using typed events.",
            extra={"topic_name": topic_name},
        )
        return self.publish_message(topic_name, contact_data)

    def close(self) -> None:
        """Close the publisher client."""
        if self.publisher:
            self.publisher.close()
            logger.info("PubSub publisher client closed")


class PubSubConsumer:
    """Shared PubSub consumer for subscribing to topics with logging and tracing."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        emulator_host: Optional[str] = None,
        service_name: str = "unknown-service",
    ):
        self.project_id = project_id or os.getenv("PUBSUB_PROJECT_ID", "briefly-dev")
        self.service_name = service_name

        # Set up emulator if specified
        if emulator_host:
            os.environ["PUBSUB_EMULATOR_HOST"] = emulator_host
        elif "PUBSUB_EMULATOR_HOST" not in os.environ:
            # If no emulator host is specified and no emulator is configured,
            # set up the default emulator host to avoid Google credentials issues
            os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
            logger.info(
                "No Pub/Sub emulator host specified, using default: localhost:8085"
            )

        # Initialize subscriber client
        try:
            self.subscriber = pubsub_v1.SubscriberClient()
            self.subscriptions: Dict[str, Any] = {}
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub subscriber client: {e}")
            logger.info("Pub/Sub functionality will be disabled")
            self.subscriber = None
            self.subscriptions = {}

        logger.info(
            "PubSub consumer initialized",
            extra={
                "project_id": self.project_id,
                "emulator_host": emulator_host,
                "service_name": self.service_name,
            },
        )

    def subscribe(
        self,
        topic_name: str,
        subscription_name: str,
        callback: Callable[..., Any],
        **kwargs: Any,
    ) -> Any:
        """Subscribe to a topic with the specified callback and tracing."""
        if not self.subscriber:
            logger.warning("Pub/Sub subscriber not available, subscription skipped")
            return None

        with tracer.start_as_current_span(
            f"pubsub.subscribe.{subscription_name}"
        ) as span:
            try:
                subscription_path = self.subscriber.subscription_path(
                    self.project_id, subscription_name
                )

                # Add span attributes
                span.set_attribute("pubsub.topic", topic_name)
                span.set_attribute("pubsub.subscription", subscription_name)
                span.set_attribute("pubsub.project_id", str(self.project_id))

                # Create subscription
                subscription = self.subscriber.subscribe(
                    subscription_path,
                    callback=callback,
                    flow_control=pubsub_v1.types.FlowControl(
                        max_messages=kwargs.get("max_messages", 100),
                        max_bytes=kwargs.get("max_bytes", 1024 * 1024),  # 1MB
                    ),
                )

                self.subscriptions[subscription_name] = subscription

                logger.info(
                    "Successfully subscribed to topic",
                    extra={
                        "topic_name": topic_name,
                        "subscription_name": subscription_name,
                        "subscription_path": subscription_path,
                        "trace_id": (
                            span.get_span_context().trace_id
                            if span.is_recording()
                            else None
                        ),
                        "span_id": (
                            span.get_span_context().span_id
                            if span.is_recording()
                            else None
                        ),
                    },
                )

                return subscription

            except Exception as e:
                logger.error(
                    "Failed to subscribe to topic",
                    extra={
                        "topic_name": topic_name,
                        "subscription_name": subscription_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "trace_id": (
                            span.get_span_context().trace_id
                            if span.is_recording()
                            else None
                        ),
                        "span_id": (
                            span.get_span_context().span_id
                            if span.is_recording()
                            else None
                        ),
                    },
                )
                span.record_exception(e)
                raise

    def unsubscribe(self, subscription_name: str) -> None:
        """Unsubscribe from a topic with logging."""
        if subscription_name in self.subscriptions:
            try:
                self.subscriptions[subscription_name].cancel()
                del self.subscriptions[subscription_name]
                logger.info(
                    "Successfully unsubscribed from subscription",
                    extra={"subscription_name": subscription_name},
                )
            except Exception as e:
                logger.error(
                    "Failed to unsubscribe from subscription",
                    extra={
                        "subscription_name": subscription_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

    def close(self) -> None:
        """Close all subscriptions and the subscriber client."""
        for subscription_name in list(self.subscriptions.keys()):
            self.unsubscribe(subscription_name)

        if self.subscriber:
            self.subscriber.close()
            logger.info("PubSub subscriber client closed")


def create_test_message(data_type: str, **kwargs: Any) -> Dict[str, Any]:
    """Create a test message for testing purposes (legacy function)."""
    logger.warning(
        "Using legacy create_test_message function. Consider using typed events.",
        extra={"data_type": data_type},
    )

    base_message = {
        "id": kwargs.get("id", f"test-{data_type}-{datetime.utcnow().timestamp()}"),
        "user_id": kwargs.get("user_id", "test-user"),
        "provider": kwargs.get("provider", "test"),
        "type": data_type,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if data_type == "email":
        base_message.update(
            {
                "subject": kwargs.get("subject", "Test Email Subject"),
                "body": kwargs.get("body", "This is a test email body"),
                "from": kwargs.get("from", "test@example.com"),
                "to": kwargs.get("to", ["recipient@example.com"]),
                "thread_id": kwargs.get("thread_id", "test-thread-123"),
            }
        )
    elif data_type == "calendar":
        base_message.update(
            {
                "subject": kwargs.get("subject", "Test Calendar Event"),
                "start_time": kwargs.get("start_time", datetime.utcnow().isoformat()),
                "end_time": kwargs.get("end_time", datetime.utcnow().isoformat()),
                "attendees": kwargs.get("attendees", ["attendee@example.com"]),
            }
        )
    elif data_type == "contact":
        base_message.update(
            {
                "display_name": kwargs.get("display_name", "Test Contact"),
                "email_addresses": kwargs.get(
                    "email_addresses", ["contact@example.com"]
                ),
            }
        )

    return base_message
