"""
Contact discovery consumer for processing events and discovering contacts.
"""

import json
import logging
from typing import Any, Dict, Optional

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import ReceivedMessage

from services.common.config.subscription_config import SubscriptionConfig
from services.common.events import (
    CalendarEvent,
    ContactEvent,
    DocumentEvent,
    EmailEvent,
    TodoEvent,
)
from services.common.pubsub_client import PubSubClient
from services.user.services.contact_discovery_service import ContactDiscoveryService

logger = logging.getLogger(__name__)


class ContactDiscoveryConsumer:
    """Consumer for discovering contacts from various events."""

    def __init__(self, pubsub_client: PubSubClient):
        self.pubsub_client = pubsub_client
        self.contact_discovery_service = ContactDiscoveryService(pubsub_client)

        # Topics to subscribe to for contact discovery using shared configuration
        self.topics = {}
        for topic_name in SubscriptionConfig.get_service_topics("contact_discovery"):
            self.topics[topic_name] = self._get_processor_for_topic(topic_name)

        # Subscriber client
        self.subscriber = None
        self.subscription_paths = {}

    def _get_processor_for_topic(self, topic_name: str):
        """Get the appropriate processor method for a topic."""
        if topic_name == "emails":
            return self._process_email_event
        elif topic_name == "calendars":
            return self._process_calendar_event
        elif topic_name == "contacts":
            return self._process_contact_event
        elif topic_name in [
            "word_documents",
            "sheet_documents",
            "presentation_documents",
        ]:
            return self._process_document_event
        elif topic_name == "todos":
            return self._process_todo_event
        else:
            # Default to document processing for unknown topics
            return self._process_document_event

    def start_consuming(
        self, project_id: str, subscription_prefix: str = "contact-discovery"
    ) -> None:
        """Start consuming events from all subscribed topics."""
        try:
            self.subscriber = pubsub_v1.SubscriberClient()

            for topic_name, process_func in self.topics.items():
                config = SubscriptionConfig.get_subscription_config(
                    "contact_discovery", topic_name
                )
                subscription_name = config["subscription_name"]
                subscription_path = self.subscriber.subscription_path(
                    project_id, subscription_name
                )

                # Create subscription if it doesn't exist
                try:
                    self.subscriber.get_subscription(
                        request={"subscription": subscription_path}
                    )
                    logger.info(f"Subscription {subscription_name} already exists")
                except Exception:
                    # Create new subscription
                    topic_path = self.subscriber.topic_path(project_id, topic_name)
                    self.subscriber.create_subscription(
                        request={
                            "name": subscription_path,
                            "topic": topic_path,
                            "ack_deadline_seconds": config["ack_deadline_seconds"],
                            "retain_acked_messages": config["retain_acked_messages"],
                        }
                    )
                    logger.info(
                        f"Created subscription {subscription_name} for topic {topic_name}"
                    )

                self.subscription_paths[topic_name] = subscription_path

                # Start consuming from this subscription
                self._consume_topic(topic_name, subscription_path, process_func)

            logger.info("Contact discovery consumer started successfully")

        except Exception as e:
            logger.error(f"Error starting contact discovery consumer: {e}")
            raise

    def _consume_topic(
        self, topic_name: str, subscription_path: str, process_func: callable
    ) -> None:
        """Start consuming from a specific topic subscription."""

        def callback(message: ReceivedMessage) -> None:
            try:
                logger.debug(
                    f"Processing message from {topic_name}: {message.message_id}"
                )

                # Parse message data
                data = json.loads(message.data.decode("utf-8"))

                # Process the event
                process_func(data)

                # Acknowledge the message
                message.ack()
                logger.debug(
                    f"Successfully processed message {message.message_id} from {topic_name}"
                )

            except Exception as e:
                logger.error(
                    f"Error processing message {message.message_id} from {topic_name}: {e}"
                )
                # Nack the message to retry later
                message.nack()

        # Start streaming pull
        streaming_pull_future = self.subscriber.subscribe(
            subscription_path, callback=callback
        )

        logger.info(f"Started consuming from {topic_name}")

        # Store the future for cleanup
        if not hasattr(self, "_streaming_futures"):
            self._streaming_futures = {}
        self._streaming_futures[topic_name] = streaming_pull_future

    def _process_email_event(self, data: Dict[str, Any]) -> None:
        """Process an email event for contact discovery."""
        try:
            # Parse email event
            email_event = EmailEvent(**data)

            # Process for contact discovery
            self.contact_discovery_service.process_email_event(email_event)

            logger.debug(
                f"Processed email event for contact discovery: {email_event.email.message_id}"
            )

        except Exception as e:
            logger.error(f"Error processing email event for contact discovery: {e}")

    def _process_calendar_event(self, data: Dict[str, Any]) -> None:
        """Process a calendar event for contact discovery."""
        try:
            # Parse calendar event
            calendar_event = CalendarEvent(**data)

            # Process for contact discovery
            self.contact_discovery_service.process_calendar_event(calendar_event)

            logger.debug(
                f"Processed calendar event for contact discovery: {calendar_event.event.id}"
            )

        except Exception as e:
            logger.error(f"Error processing calendar event for contact discovery: {e}")

    def _process_contact_event(self, data: Dict[str, Any]) -> None:
        """Process a contact event for contact discovery."""
        try:
            # Parse contact event
            contact_event = ContactEvent(**data)

            # For contact events, we might want to update existing contact information
            # or merge contact data from different sources
            logger.debug(
                f"Processed contact event for contact discovery: {contact_event.contact.id}"
            )

        except Exception as e:
            logger.error(f"Error processing contact event for contact discovery: {e}")

    def _process_document_event(self, data: Dict[str, Any]) -> None:
        """Process a document event for contact discovery."""
        try:
            # Parse document event
            document_event = DocumentEvent(**data)

            # Process for contact discovery
            self.contact_discovery_service.process_document_event(document_event)

            logger.debug(
                f"Processed document event for contact discovery: {document_event.document.id}"
            )

        except Exception as e:
            logger.error(f"Error processing document event for contact discovery: {e}")

    def _process_todo_event(self, data: Dict[str, Any]) -> None:
        """Process a todo event for contact discovery."""
        try:
            # Parse todo event
            todo_event = TodoEvent(**data)

            # Process for contact discovery
            self.contact_discovery_service.process_todo_event(todo_event)

            logger.debug(
                f"Processed todo event for contact discovery: {todo_event.todo.id}"
            )

        except Exception as e:
            logger.error(f"Error processing todo event for contact discovery: {e}")

    def stop_consuming(self) -> None:
        """Stop consuming events."""
        try:
            if hasattr(self, "_streaming_futures"):
                for topic_name, future in self._streaming_futures.items():
                    future.cancel()
                    logger.info(f"Stopped consuming from {topic_name}")

            if self.subscriber:
                self.subscriber.close()
                logger.info("Contact discovery consumer stopped")

        except Exception as e:
            logger.error(f"Error stopping contact discovery consumer: {e}")

    def get_contact_stats(self, user_id: str) -> Dict[str, Any]:
        """Get contact statistics for a user."""
        return self.contact_discovery_service.get_contact_stats(user_id)

    def search_contacts(self, user_id: str, query: str, limit: int = 20):
        """Search contacts for a user."""
        return self.contact_discovery_service.search_contacts(user_id, query, limit)

    def get_user_contacts(self, user_id: str, limit: int = 100):
        """Get all contacts for a user."""
        return self.contact_discovery_service.get_user_contacts(user_id, limit)
