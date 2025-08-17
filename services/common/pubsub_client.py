#!/usr/bin/env python3
"""
Shared PubSub utilities for Briefly services
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


class PubSubClient:
    """Shared PubSub client for publishing messages"""

    def __init__(
        self, project_id: Optional[str] = None, emulator_host: Optional[str] = None
    ):
        self.project_id = project_id or os.getenv("PUBSUB_PROJECT_ID", "briefly-dev")

        # Set up emulator if specified
        if emulator_host:
            os.environ["PUBSUB_EMULATOR_HOST"] = emulator_host

        # Initialize publisher client
        self.publisher = pubsub_v1.PublisherClient()

    def publish_message(self, topic_name: str, data: Dict[str, Any], **kwargs) -> str:
        """Publish a message to a PubSub topic"""
        try:
            topic_path = self.publisher.topic_path(self.project_id, topic_name)

            # Convert data to JSON string
            message_data = json.dumps(data, default=str).encode("utf-8")

            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = datetime.utcnow().isoformat()

            # Publish message
            future = self.publisher.publish(topic_path, data=message_data, **kwargs)

            message_id = future.result()
            logger.info(f"Published message {message_id} to topic {topic_name}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to publish message to topic {topic_name}: {e}")
            raise

    def publish_email_data(
        self, email_data: Dict[str, Any], topic_name: str = "email-backfill"
    ) -> str:
        """Publish email data to the specified topic"""
        return self.publish_message(topic_name, email_data)

    def publish_calendar_data(
        self, calendar_data: Dict[str, Any], topic_name: str = "calendar-updates"
    ) -> str:
        """Publish calendar data to the specified topic"""
        return self.publish_message(topic_name, calendar_data)

    def publish_contact_data(
        self, contact_data: Dict[str, Any], topic_name: str = "contact-updates"
    ) -> str:
        """Publish contact data to the specified topic"""
        return self.publish_message(topic_name, contact_data)

    def close(self):
        """Close the publisher client"""
        if self.publisher:
            self.publisher.close()


class PubSubConsumer:
    """Shared PubSub consumer for subscribing to topics"""

    def __init__(
        self, project_id: Optional[str] = None, emulator_host: Optional[str] = None
    ):
        self.project_id = project_id or os.getenv("PUBSUB_PROJECT_ID", "briefly-dev")

        # Set up emulator if specified
        if emulator_host:
            os.environ["PUBSUB_EMULATOR_HOST"] = emulator_host

        # Initialize subscriber client
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscriptions = {}

    def subscribe(
        self, topic_name: str, subscription_name: str, callback: Callable, **kwargs
    ):
        """Subscribe to a topic with the specified callback"""
        try:
            subscription_path = self.subscriber.subscription_path(
                self.project_id, subscription_name
            )

            # Create subscription
            subscription = self.subscriber.subscribe(
                subscription_path,
                callback=callback,
                flow_control=pubsub_v1.types.FlowControl(
                    max_messages=kwargs.get("max_messages", 100),
                    max_bytes=kwargs.get("max_bytes", 1024 * 1024),  # 1MB
                    allow_exceeded_limits=False,
                ),
            )

            self.subscriptions[subscription_name] = subscription
            logger.info(
                f"Subscribed to {topic_name} with subscription {subscription_name}"
            )
            return subscription

        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic_name}: {e}")
            raise

    def unsubscribe(self, subscription_name: str):
        """Unsubscribe from a topic"""
        if subscription_name in self.subscriptions:
            try:
                self.subscriptions[subscription_name].cancel()
                del self.subscriptions[subscription_name]
                logger.info(f"Unsubscribed from {subscription_name}")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from {subscription_name}: {e}")

    def close(self):
        """Close all subscriptions and the subscriber client"""
        for subscription_name in list(self.subscriptions.keys()):
            self.unsubscribe(subscription_name)

        if self.subscriber:
            self.subscriber.close()


def create_test_message(data_type: str, **kwargs) -> Dict[str, Any]:
    """Create a test message for testing purposes"""
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
