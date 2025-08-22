#!/usr/bin/env python3
"""
Pub/Sub Consumer for Vespa Loader Service

This module handles consuming messages from Pub/Sub topics and processing them
for Vespa indexing. It listens to the new data-type focused topics and processes
emails, calendar events, contacts, documents, and todos.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from services.common.config.subscription_config import SubscriptionConfig
from services.common.events.calendar_events import (  # Keep deprecated events for backward compatibility
    CalendarBatchEvent,
    CalendarEvent,
    CalendarEventData,
    CalendarUpdateEvent,
)
from services.common.events.contact_events import (  # Keep deprecated events for backward compatibility
    ContactBatchEvent,
    ContactData,
    ContactEvent,
    ContactUpdateEvent,
)
from services.common.events.document_events import DocumentData, DocumentEvent
from services.common.events.email_events import EmailData, EmailEvent
from services.common.events.todo_events import TodoData, TodoEvent
from services.common.logging_config import get_logger
from services.vespa_loader.document_factory import VespaDocumentFactory, parse_event_by_topic
from services.vespa_loader.settings import Settings
from services.vespa_loader.types import VespaDocumentType

# PubSub types
try:
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]
    from google.cloud.pubsub_v1.types import (
        ReceivedMessage,  # type: ignore[attr-defined]
    )

    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    ReceivedMessage = Any  # type: ignore


logger = get_logger(__name__)

# Import the shared ingest service function
from services.vespa_loader.ingest_service import ingest_document_service

# Define union type for all supported event types
SupportedEventType = Union[
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
]


# Typed message structure
class TypedMessage:
    """A properly typed message container that handles all event types"""

    def __init__(self, message: Any, data: SupportedEventType):
        self.message = message
        self.data = data
        self.timestamp = time.time()

    @property
    def message_id(self) -> str:
        return self.message.message_id

    @property
    def user_id(self) -> str:
        """Extract user_id from any supported event type"""
        return self.data.user_id

    @property
    def event_type(self) -> str:
        """Get the event type name"""
        if isinstance(self.data, EmailEvent):
            return "email"
        elif isinstance(self.data, CalendarEvent):
            return "calendar"
        elif isinstance(self.data, ContactEvent):
            return "contact"
        elif isinstance(self.data, DocumentEvent):
            return "document"
        elif isinstance(self.data, TodoEvent):
            return "todo"
        # Keep deprecated event types for backward compatibility
        elif isinstance(self.data, CalendarBatchEvent):
            return "calendar-batch"
        elif isinstance(self.data, CalendarUpdateEvent):
            return "calendar-update"
        elif isinstance(self.data, ContactBatchEvent):
            return "contact-batch"
        elif isinstance(self.data, ContactUpdateEvent):
            return "contact-update"
        else:
            raise ValueError(f"Unknown event type: {type(self.data)}")

    def is_typed_event(self) -> bool:
        """Check if this message contains a properly typed event"""
        return True  # All events are now typed

    def is_email_event(self) -> bool:
        """Check if this message contains an email-related event"""
        return isinstance(self.data, EmailEvent)

    def is_calendar_event(self) -> bool:
        """Check if this message contains a calendar-related event"""
        return isinstance(
            self.data, (CalendarEvent, CalendarBatchEvent, CalendarUpdateEvent)
        )

    def is_contact_event(self) -> bool:
        """Check if this message contains a contact-related event"""
        return isinstance(
            self.data, (ContactEvent, ContactBatchEvent, ContactUpdateEvent)
        )

    def is_document_event(self) -> bool:
        """Check if this message contains a document-related event"""
        return isinstance(self.data, DocumentEvent)

    def is_todo_event(self) -> bool:
        """Check if this message contains a todo-related event"""
        return isinstance(self.data, TodoEvent)


try:
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]
    from google.cloud.pubsub_v1.types import (
        ReceivedMessage,  # type: ignore[attr-defined]
    )

    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    logger.warning(
        "Google Cloud Pub/Sub not available. Install with: pip install google-cloud-pubsub"
    )


class PubSubConsumer:
    """Consumes messages from Pub/Sub topics for Vespa indexing"""

    def __init__(
        self,
        settings: Settings,
        vespa_client: Any = None,
        content_normalizer: Any = None,
        embedding_generator: Any = None,
        document_mapper: Any = None,
    ) -> None:
        self.settings = settings
        self.vespa_client = vespa_client
        self.content_normalizer = content_normalizer
        self.embedding_generator = embedding_generator
        self.document_mapper = document_mapper

        self.subscriber: Optional[Any] = None
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.processed_count = 0
        self.error_count = 0

        # Initialize email content processor and document factory
        self.document_factory = VespaDocumentFactory()

        # Configure new data-type focused topics using shared configuration
        self.topics = {}
        for topic_name in SubscriptionConfig.get_service_topics("vespa_loader"):
            config = SubscriptionConfig.get_subscription_config(
                "vespa_loader", topic_name
            )
            self.topics[topic_name] = {
                "subscription_name": config["subscription_name"],
                "processor": self._get_processor_for_topic(topic_name),
                "batch_size": config["batch_size"],
            }

        # Batch processing
        self.message_batches: Dict[str, List[TypedMessage]] = {
            topic: [] for topic in self.topics
        }
        self.batch_timers: Dict[str, Optional[asyncio.Task[Any]]] = {}
        self.batch_timeout = 5.0  # seconds

        # Event loop reference for cross-thread communication
        self.loop: Optional[asyncio.AbstractEventLoop] = None

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
            "word_fragments",
            "sheet_documents",
            "sheet_fragments",
            "presentation_documents",
            "presentation_fragments",
            "task_documents",
        ]:
            return self._process_document_event
        elif topic_name == "todos":
            return self._process_todo_event
        else:
            # Default to document processing for unknown topics
            return self._process_document_event

    async def start(self) -> bool:
        """Start the Pub/Sub consumer"""
        if not PUBSUB_AVAILABLE:
            logger.error("Pub/Sub not available - cannot start consumer")
            return False

        try:
            logger.info("Starting Pub/Sub consumer...")
            logger.info(f"Project ID: {self.settings.pubsub_project_id}")
            logger.info(f"Emulator host: {self.settings.pubsub_emulator_host}")
            logger.info(f"Topics configured: {list(self.topics.keys())}")

            # Initialize subscriber client with emulator configuration
            if hasattr(self.settings, "pubsub_emulator_host"):
                # Use local emulator
                import os

                os.environ["PUBSUB_EMULATOR_HOST"] = self.settings.pubsub_emulator_host
                logger.info(
                    f"Using Pub/Sub emulator at {self.settings.pubsub_emulator_host}"
                )

            self.subscriber = pubsub_v1.SubscriberClient()
            logger.info("Pub/Sub subscriber client initialized")

            # Store event loop reference for cross-thread communication
            self.loop = asyncio.get_running_loop()
            logger.info("Event loop reference stored")

            # Create subscriptions if they don't exist
            await self._ensure_subscriptions()

            # Start consuming from each topic using async callbacks
            for topic_name, config in self.topics.items():
                await self._start_topic_consumer(topic_name, config)

            self.running = True
            logger.info("Pub/Sub consumer started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start Pub/Sub consumer: {e}")
            return False

    async def stop(self) -> None:
        """Stop the Pub/Sub consumer"""
        logger.info("Stopping Pub/Sub consumer...")
        self.running = False

        # Cancel all subscriptions
        for topic_name, subscription in self.subscriptions.items():
            try:
                if subscription and hasattr(subscription, "cancel"):
                    subscription.cancel()
                    logger.info(f"Cancelled subscription for topic: {topic_name}")
            except Exception as e:
                logger.error(
                    f"Error cancelling subscription for topic {topic_name}: {e}"
                )

        # Close subscriber client
        if self.subscriber:
            self.subscriber.close()
            self.subscriber = None

        logger.info("Pub/Sub consumer stopped")

    async def _ensure_subscriptions(self) -> None:
        """Ensure all required subscriptions exist"""
        if not self.subscriber:
            logger.error("Subscriber not initialized")
            return

        logger.info("Ensuring subscriptions exist...")
        for topic_name, config in self.topics.items():
            try:
                subscription_path = self.subscriber.subscription_path(
                    self.settings.pubsub_project_id, config["subscription_name"]
                )

                # Check if subscription exists and create if it doesn't
                logger.info(f"Subscription path for {topic_name}: {subscription_path}")
                logger.info(f"Subscription name: {config['subscription_name']}")

                # Try to create the subscription using REST API
                await self._create_subscription_if_not_exists(topic_name, config)

            except Exception as e:
                logger.error(f"Error setting up subscription for {topic_name}: {e}")

    async def _create_subscription_if_not_exists(
        self, topic_name: str, config: Dict[str, Any]
    ) -> None:
        """Create a subscription if it doesn't exist using Python Pub/Sub client"""
        try:
            import asyncio

            subscription_name = config["subscription_name"]
            topic_path = (
                f"projects/{self.settings.pubsub_project_id}/topics/{topic_name}"
            )
            subscription_path = f"projects/{self.settings.pubsub_project_id}/subscriptions/{subscription_name}"

            # Check if subscription already exists by trying to get it
            try:
                # Use the subscriber client to check if subscription exists
                if self.subscriber:
                    subscription = self.subscriber.get_subscription(
                        request={"subscription": subscription_path}
                    )
                    if subscription:
                        logger.info(
                            f"Subscription {subscription_name} already exists for topic {topic_name}"
                        )
                        return
            except Exception:
                # Subscription doesn't exist, create it
                pass

            # Create the subscription using the subscriber client
            try:
                # The subscriber client can create subscriptions
                if self.subscriber:
                    subscription = self.subscriber.create_subscription(
                        request={"name": subscription_path, "topic": topic_path}
                    )
                    logger.info(
                        f"Successfully created subscription {subscription_name} for topic {topic_name}"
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to create subscription {subscription_name} using subscriber client: {e}"
                )

        except Exception as e:
            logger.warning(
                f"Could not create subscription {config['subscription_name']} for topic {topic_name}: {e}"
            )
            # Don't fail startup if subscription creation fails

    async def _start_topic_consumer(
        self, topic_name: str, config: Dict[str, Any]
    ) -> None:
        """Start consuming from a specific topic using async callbacks"""
        if not self.subscriber:
            logger.error("Subscriber not initialized")
            return

        try:
            subscription_path = self.subscriber.subscription_path(
                self.settings.pubsub_project_id, config["subscription_name"]
            )

            logger.info(f"Starting consumer for topic: {topic_name}")
            logger.info(f"Subscription path: {subscription_path}")
            logger.info(f"Batch size: {config['batch_size']}")

            # Use the subscribe method with callbacks instead of polling
            subscription = self.subscriber.subscribe(
                subscription_path,
                callback=self._create_message_callback(topic_name, config),
                flow_control=pubsub_v1.types.FlowControl(
                    max_messages=config["batch_size"], max_bytes=1024 * 1024  # 1MB
                ),
            )

            self.subscriptions[topic_name] = {
                "subscription": subscription,
                "active": True,
                "path": subscription_path,
            }

            logger.info(f"Started async subscription for topic: {topic_name}")

        except Exception as e:
            logger.error(f"Error starting topic consumer for {topic_name}: {e}")
            self.subscriptions[topic_name] = {"active": False}

    def _create_message_callback(
        self, topic_name: str, config: Dict[str, Any]
    ) -> Callable[[Any], None]:
        """Create a callback function for processing messages from a specific topic"""

        def message_callback(message: Any) -> None:
            try:
                logger.debug(
                    f"Received message from {topic_name}: {message.message_id}"
                )
                logger.debug(f"Message data length: {len(message.data)} bytes")

                # Parse message data
                raw_data = json.loads(message.data.decode("utf-8"))

                # Parse as appropriate typed event based on topic
                try:
                    typed_data = parse_event_by_topic(
                        topic_name, raw_data, message.message_id
                    )

                    logger.debug(
                        f"Parsed message data: message_id={message.message_id}, user_id={typed_data.user_id}"
                    )

                    # Create typed message and add to batch
                    typed_message = TypedMessage(message, typed_data)
                    self.message_batches[topic_name].append(typed_message)
                except Exception as parse_error:
                    logger.error(
                        f"Failed to parse message from {topic_name}: {parse_error}"
                    )
                    message.nack()
                    self.error_count += 1
                    return
                logger.debug(
                    f"Added message to batch for {topic_name}. Batch size: {len(self.message_batches[topic_name])}"
                )

                # Process batch if it's full
                if len(self.message_batches[topic_name]) >= config["batch_size"]:
                    logger.info(f"Batch full for {topic_name}, processing immediately")
                    # Schedule async processing
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self._process_batch(topic_name, config), self.loop
                        )
                else:
                    # Only start timer if one doesn't already exist
                    timer = self.batch_timers.get(topic_name)
                    if (
                        topic_name not in self.batch_timers
                        or not timer
                        or (timer is not None and timer.done())
                    ):
                        logger.debug(
                            f"Starting timer for partial batch in {topic_name}"
                        )
                        # Start timer for partial batch
                        if self.loop:
                            asyncio.run_coroutine_threadsafe(
                                self._schedule_batch_processing(topic_name, config),
                                self.loop,
                            )

            except Exception as e:
                logger.error(f"Error handling message from {topic_name}: {e}")
                message.nack()
                self.error_count += 1

        return message_callback

    async def _schedule_batch_processing(
        self, topic_name: str, config: Dict[str, Any]
    ) -> None:
        """Schedule batch processing for a topic"""
        # Only create timer if one doesn't exist or is done
        if topic_name in self.batch_timers and self.batch_timers[topic_name]:
            timer = self.batch_timers[topic_name]
            if timer is not None and not timer.done():
                logger.info(f"Timer already exists for {topic_name}, skipping")
                return

        # Create new timer
        logger.info(f"Creating timer for {topic_name} with {self.batch_timeout}s delay")
        self.batch_timers[topic_name] = asyncio.create_task(
            self._delayed_batch_processing(topic_name, config)
        )

    async def _delayed_batch_processing(
        self, topic_name: str, config: Dict[str, Any]
    ) -> None:
        """Process batch after timeout delay"""
        logger.info(f"Timer expired for {topic_name}, processing batch")
        await asyncio.sleep(self.batch_timeout)

        if self.message_batches[topic_name]:
            await self._process_batch(topic_name, config)
        else:
            logger.info(f"No messages in batch for {topic_name} after timer")

    async def _process_batch(self, topic_name: str, config: Dict[str, Any]) -> None:
        """Process a batch of messages"""
        if not self.message_batches[topic_name]:
            logger.info(f"No messages to process for {topic_name}")
            return

        batch = self.message_batches[topic_name]
        self.message_batches[topic_name] = []

        logger.info(f"Processing batch of {len(batch)} messages from {topic_name}")
        logger.info(f"Message IDs: {[item.message_id for item in batch]}")

        # Process messages in parallel
        tasks = []
        for item in batch:
            task = asyncio.create_task(
                self._process_single_message(topic_name, item, config)
            )
            tasks.append(task)

        # Wait for all processing to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Acknowledge or nack messages based on results
        for i, (typed_message, result) in enumerate(zip(batch, results)):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to process message {i} from {topic_name}: {result}"
                )
                typed_message.message.nack()
                self.error_count += 1
            else:
                typed_message.message.ack()
                self.processed_count += 1

        logger.info(
            f"Completed processing batch from {topic_name}: {len(batch)} messages"
        )

    async def _process_single_message(
        self, topic_name: str, typed_message: TypedMessage, config: Dict[str, Any]
    ) -> Any:
        """Process a single message with proper typing"""
        try:
            # Call the appropriate processor
            processor = config["processor"]
            message_id = typed_message.message_id
            user_id = typed_message.user_id

            logger.info(
                f"Calling processor for message from {topic_name}: {message_id} for user {user_id}"
            )

            # Log additional info for typed events
            if typed_message.is_typed_event():
                logger.info(
                    f"Processing {typed_message.event_type} event for user {user_id}"
                )

            result = await processor(typed_message.data)
            logger.info(
                f"Successfully processed message from {topic_name}: {message_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error processing message from {topic_name}: {e}")
            raise

    async def _process_email_event(self, data: EmailEvent) -> None:
        """Process an email event for Vespa indexing using typed EmailEvent"""
        logger.info(
            f"Processing EmailEvent for user {data.user_id}, email {data.email.id}, operation {data.operation}"
        )

        try:
            # Create Vespa document using factory
            document = self.document_factory.create_email_document(data)

            # Validate email data quality and log warnings for missing/empty fields
            self._validate_email_data_quality(data.email, data.user_id)

            await self._ingest_document(document)
        except Exception as e:
            logger.error(f"Failed to process email event: {e}")
            raise

    async def _process_calendar_event(self, data: CalendarEvent) -> None:
        """Process a calendar event for Vespa indexing using typed CalendarEvent"""
        logger.info(
            f"Processing CalendarEvent for user {data.user_id}, event {data.event.id}, operation {data.operation}"
        )

        try:
            # Create Vespa document using factory
            document = self.document_factory.create_calendar_document(data)
            await self._ingest_document(document)
        except Exception as e:
            logger.error(f"Failed to process calendar event: {e}")
            raise

    async def _process_contact_event(self, data: ContactEvent) -> None:
        """Process a contact event for Vespa indexing using typed ContactEvent"""
        logger.info(
            f"Processing ContactEvent for user {data.user_id}, contact {data.contact.id}, operation {data.operation}"
        )

        try:
            # Create Vespa document using factory
            document = self.document_factory.create_contact_document(data)
            await self._ingest_document(document)
        except Exception as e:
            logger.error(f"Failed to process contact event: {e}")
            raise

    async def _process_document_event(self, data: DocumentEvent) -> None:
        """Process a document event for Vespa indexing using typed DocumentEvent"""
        logger.info(
            f"Processing DocumentEvent for user {data.user_id}, document {data.document.id}, operation {data.operation}, content_type {data.content_type}"
        )

        try:
            # Create Vespa document using factory
            document = self.document_factory.create_document_document(data)
            await self._ingest_document(document)
        except Exception as e:
            logger.error(f"Failed to process document event: {e}")
            raise

    async def _process_todo_event(self, data: TodoEvent) -> None:
        """Process a todo event for Vespa indexing using typed TodoEvent"""
        logger.info(
            f"Processing TodoEvent for user {data.user_id}, todo {data.todo.id}, operation {data.operation}"
        )

        try:
            # Create Vespa document using factory
            document = self.document_factory.create_todo_document(data)
            await self._ingest_document(document)
        except Exception as e:
            logger.error(f"Failed to process todo event: {e}")
            raise

    async def _ingest_document(self, document: VespaDocumentType) -> Dict[str, Any]:
        """Ingest a document into Vespa

        Returns:
            Dict containing the ingestion result
        """
        try:
            # Log document ingestion start with key details in one line
            logger.info(
                f"Starting ingest for document {document.id} "
                f"(type: {document.type}, user: {document.user_id})"
            )

            # Call the ingest service directly
            result = await ingest_document_service(
                document.to_dict(),
                self.vespa_client,
                self.content_normalizer,
                self.embedding_generator,
                self.document_mapper,
            )

            # Run post-processing tasks directly since we're not in a FastAPI context
            try:
                await self._post_process_document(document.id, document.user_id)
            except Exception as post_process_error:
                logger.warning(
                    f"Post-processing failed for document {document.id}: {post_process_error}"
                )
                # Continue even if post-processing fails

            logger.info(f"Successfully indexed document {document.id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Error ingesting document {document.id}: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        stats = {
            "running": self.running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "active_batches": {
                topic: len(batch) for topic, batch in self.message_batches.items()
            },
            "subscriptions": list(self.subscriptions.keys()),
            "subscription_details": {
                topic: {
                    "active": sub.get("active", False),
                    "path": sub.get("path", "unknown"),
                }
                for topic, sub in self.subscriptions.items()
            },
        }
        logger.info(f"Consumer stats: {stats}")
        return stats

    async def _post_process_document(self, document_id: str, user_id: str) -> None:
        """Post-process a document after ingestion

        This method runs the same post-processing logic that would normally
        run as a background task in the HTTP endpoint.
        """
        try:
            # Add any post-processing logic here
            # For example: update search indices, trigger notifications, etc.
            # This mirrors the logic in main.py:_post_process_document
            pass
        except Exception as e:
            logger.error(f"Error in post-processing document {document_id}: {e}")

    def _validate_email_data_quality(self, email: EmailData, user_id: str) -> None:
        """Validate email data quality and log warnings for missing/empty fields"""

        # Check for empty or missing critical fields
        quality_issues = []

        if not email.from_address or email.from_address.strip() == "":
            quality_issues.append("empty_from_address")

        if not email.to_addresses or len(email.to_addresses) == 0:
            quality_issues.append("empty_to_addresses")
        elif all(not addr or addr.strip() == "" for addr in email.to_addresses):
            quality_issues.append("all_empty_to_addresses")

        if not email.subject or email.subject.strip() == "":
            quality_issues.append("empty_subject")

        if not email.body or email.body.strip() == "":
            quality_issues.append("empty_body")

        if not email.thread_id or email.thread_id.strip() == "":
            quality_issues.append("empty_thread_id")

        # Log quality issues with distributed trace information
        if quality_issues:
            # Extract trace_id from metadata if available
            trace_id = "unknown"
            if (
                hasattr(email, "metadata")
                and email.metadata
                and "trace_id" in email.metadata
            ):
                trace_id = email.metadata["trace_id"]

            # Log the main warning message with trace_id
            logger.warning(
                f"Email data quality issues detected for user {user_id}: "
                f"ID={email.id}, provider={email.provider}, trace_id={trace_id}, issues={quality_issues}"
            )

            # Log the raw email data for debugging
            logger.debug(
                f"Raw email data with quality issues: "
                f"from_address='{email.from_address}', "
                f"to_addresses={email.to_addresses}, "
                f"subject='{email.subject}', "
                f"body_length={len(email.body) if email.body else 0}, "
                f"thread_id='{email.thread_id}', "
                f"trace_id={trace_id}"
            )
