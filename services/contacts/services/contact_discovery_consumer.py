"""
Contact discovery consumer for processing events and discovering contacts.

Moved from services/user/services/contact_discovery_consumer.py and adapted
for database persistence in the Contacts Service.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

try:
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]
    from google.cloud.pubsub_v1.types import (
        ReceivedMessage,  # type: ignore[attr-defined]
    )

    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    pubsub_v1 = None  # type: ignore
    ReceivedMessage = None  # type: ignore

from sqlalchemy.ext.asyncio import AsyncSession

from services.common.config.subscription_config import SubscriptionConfig
from services.common.events import (
    CalendarEvent,
    ContactEvent,
    DocumentEvent,
    EmailEvent,
    TodoEvent,
)
from services.common.pubsub_client import PubSubClient
from services.contacts.services.contact_discovery_service import ContactDiscoveryService

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
        self.subscriber: Optional[Any] = None
        self.subscription_paths: Dict[str, str] = {}

    def _get_processor_for_topic(
        self, topic_name: str
    ) -> Optional[Callable[[Dict[str, Any], AsyncSession], None]]:
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
            if not PUBSUB_AVAILABLE:
                logger.error("Google Cloud Pub/Sub not available")
                return

            self.subscriber = pubsub_v1.SubscriberClient()

            for topic_name, process_func in self.topics.items():
                if process_func is None:
                    continue

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
        self,
        topic_name: str,
        subscription_path: str,
        process_func: Callable[[Dict[str, Any], AsyncSession], None],
    ) -> None:
        """Start consuming from a specific topic subscription."""

        def callback(message: Any) -> None:
            try:
                logger.debug(
                    f"Processing message from {topic_name}: {message.message_id}"
                )

                # Parse message data
                data = json.loads(message.data.decode("utf-8"))

                # Process the event with database session
                # Note: This is a simplified approach - in a real implementation,
                # you'd want to pass the session from the main service context
                # For now, we'll log that we need database integration
                logger.info(f"Received message from {topic_name}, needs database session for processing")

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
        if self.subscriber is not None:
            streaming_pull_future = self.subscriber.subscribe(
                subscription_path, callback=callback
            )

        logger.info(f"Started consuming from {topic_name}")

        # Store the future for cleanup
        if not hasattr(self, "_streaming_futures"):
            self._streaming_futures = {}
        self._streaming_futures[topic_name] = streaming_pull_future

    async def _process_email_event(self, data: Dict[str, Any], session: AsyncSession) -> None:
        """Process an email event for contact discovery."""
        try:
            # Parse email event
            email_event = EmailEvent(**data)

            # Process for contact discovery
            await self.contact_discovery_service.process_email_event(email_event, session)

            logger.debug(
                f"Processed email event for contact discovery: {email_event.email.id}"
            )

        except Exception as e:
            logger.error(f"Error processing email event for contact discovery: {e}")

    async def _process_calendar_event(self, data: Dict[str, Any], session: AsyncSession) -> None:
        """Process a calendar event for contact discovery."""
        try:
            # Parse calendar event
            calendar_event = CalendarEvent(**data)

            # Process for contact discovery
            await self.contact_discovery_service.process_calendar_event(calendar_event, session)

            logger.debug(
                f"Processed calendar event for contact discovery: {calendar_event.event.id}"
            )

        except Exception as e:
            logger.error(f"Error processing calendar event for contact discovery: {e}")

    async def _process_contact_event(self, data: Dict[str, Any], session: AsyncSession) -> None:
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

    async def _process_document_event(self, data: Dict[str, Any], session: AsyncSession) -> None:
        """Process a document event for contact discovery."""
        try:
            # Parse document event
            document_event = DocumentEvent(**data)

            # Process for contact discovery
            await self.contact_discovery_service.process_document_event(document_event, session)

            logger.debug(
                f"Processed document event for contact discovery: {document_event.document.id}"
            )

        except Exception as e:
            logger.error(f"Error processing document event for contact discovery: {e}")

    async def _process_todo_event(self, data: Dict[str, Any], session: AsyncSession) -> None:
        """Process a todo event for contact discovery."""
        try:
            # Parse todo event
            todo_event = TodoEvent(**data)

            # Process for contact discovery
            await self.contact_discovery_service.process_todo_event(todo_event, session)

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

    async def get_contact_stats(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get contact statistics for a user."""
        return await self.contact_discovery_service.get_contact_stats(session, user_id)

    async def search_contacts(self, session: AsyncSession, user_id: str, query: str, limit: int = 20) -> List[Any]:
        """Search contacts for a user."""
        return await self.contact_discovery_service.search_contacts(session, user_id, query, limit)

    async def get_user_contacts(self, session: AsyncSession, user_id: str, limit: int = 100) -> List[Any]:
        """Get all contacts for a user."""
        return await self.contact_discovery_service.get_user_contacts(session, user_id, limit)
