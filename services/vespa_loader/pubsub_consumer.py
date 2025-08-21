#!/usr/bin/env python3
"""
Pub/Sub Consumer for Vespa Loader Service

This module handles consuming messages from Pub/Sub topics and processing them
for Vespa indexing. It listens to the backfill topics and processes emails,
calendar events, and contacts.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from services.common.events.calendar_events import (
    CalendarBatchEvent,
    CalendarEventData,
    CalendarUpdateEvent,
)
from services.common.events.contact_events import (
    ContactBatchEvent,
    ContactData,
    ContactUpdateEvent,
)
from services.common.events.email_events import EmailBackfillEvent, EmailData
from services.common.logging_config import get_logger
from services.vespa_loader.email_processor import EmailContentProcessor
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
    EmailBackfillEvent,
    CalendarUpdateEvent,
    CalendarBatchEvent,
    ContactUpdateEvent,
    ContactBatchEvent,
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
        if isinstance(self.data, EmailBackfillEvent):
            return "email-backfill"
        elif isinstance(self.data, CalendarUpdateEvent):
            return "calendar-update"
        elif isinstance(self.data, CalendarBatchEvent):
            return "calendar-batch"
        elif isinstance(self.data, ContactUpdateEvent):
            return "contact-update"
        elif isinstance(self.data, ContactBatchEvent):
            return "contact-batch"
        else:
            raise ValueError(f"Unknown event type: {type(self.data)}")

    def is_typed_event(self) -> bool:
        """Check if this message contains a properly typed event"""
        return True  # All events are now typed

    def is_email_event(self) -> bool:
        """Check if this message contains an email-related event"""
        return isinstance(self.data, EmailBackfillEvent)

    def is_calendar_event(self) -> bool:
        """Check if this message contains a calendar-related event"""
        return isinstance(self.data, (CalendarUpdateEvent, CalendarBatchEvent))

    def is_contact_event(self) -> bool:
        """Check if this message contains a contact-related event"""
        return isinstance(self.data, (ContactUpdateEvent, ContactBatchEvent))


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

        # Initialize email content processor
        self.email_processor = EmailContentProcessor()

        # Configure topics and their processors
        self.topics = {
            "email-backfill": {
                "subscription_name": "vespa-loader-email-backfill",
                "processor": self._process_email_message,
                "batch_size": 50,
            },
            "calendar-updates": {
                "subscription_name": "vespa-loader-calendar-updates",
                "processor": self._process_calendar_message,
                "batch_size": 20,
            },
            "contact-updates": {
                "subscription_name": "vespa-loader-contact-updates",
                "processor": self._process_contact_message,
                "batch_size": 100,
            },
        }

        # Batch processing
        self.message_batches: Dict[str, List[TypedMessage]] = {
            topic: [] for topic in self.topics
        }
        self.batch_timers: Dict[str, Optional[asyncio.Task[Any]]] = {}
        self.batch_timeout = 5.0  # seconds

        # Event loop reference for cross-thread communication
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def _parse_event_by_topic(
        self, topic_name: str, raw_data: Dict[str, Any], message_id: str
    ) -> SupportedEventType:
        """Parse raw data into appropriate typed event based on topic name"""
        try:
            if topic_name == "email-backfill":
                email_event: EmailBackfillEvent = EmailBackfillEvent(**raw_data)
                logger.debug(
                    f"Parsed as EmailBackfillEvent: message_id={message_id}, user_id={email_event.user_id}, emails={len(email_event.emails)}"
                )
                return email_event
            elif topic_name == "calendar-updates":
                # Try to determine if it's a single update or batch
                if "events" in raw_data:
                    calendar_batch_event: CalendarBatchEvent = CalendarBatchEvent(
                        **raw_data
                    )
                    logger.debug(
                        f"Parsed as CalendarBatchEvent: message_id={message_id}, user_id={calendar_batch_event.user_id}, events={len(calendar_batch_event.events)}"
                    )
                    return calendar_batch_event
                else:
                    calendar_event: CalendarUpdateEvent = CalendarUpdateEvent(
                        **raw_data
                    )
                    logger.debug(
                        f"Parsed as CalendarUpdateEvent: message_id={message_id}, user_id={calendar_event.user_id}, event_id={calendar_event.event.id}"
                    )
                    return calendar_event
            elif topic_name == "contact-updates":
                # Try to determine if it's a single update or batch
                if "contacts" in raw_data:
                    contact_batch_event: ContactBatchEvent = ContactBatchEvent(
                        **raw_data
                    )
                    logger.debug(
                        f"Parsed as ContactBatchEvent: message_id={message_id}, user_id={contact_batch_event.user_id}, contacts={len(contact_batch_event.contacts)}"
                    )
                    return contact_batch_event
                else:
                    contact_event: ContactUpdateEvent = ContactUpdateEvent(**raw_data)
                    logger.debug(
                        f"Parsed as ContactUpdateEvent: message_id={message_id}, user_id={contact_event.user_id}, contact_id={contact_event.contact.id}"
                    )
                    return contact_event
            else:
                logger.warning(
                    f"Unknown topic {topic_name}, message_id={message_id} - skipping"
                )
                raise ValueError(f"Unsupported topic: {topic_name}")
        except Exception as e:
            logger.error(
                f"Failed to parse event for topic {topic_name}, message_id={message_id}: {e}"
            )
            raise

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
                    typed_data = self._parse_event_by_topic(
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
                if typed_message.is_email_event():
                    email_data = typed_message.data
                    if isinstance(email_data, EmailBackfillEvent):
                        logger.info(
                            f"EmailBackfillEvent contains {len(email_data.emails)} emails"
                        )
                elif typed_message.is_calendar_event():
                    calendar_data = typed_message.data
                    if isinstance(calendar_data, CalendarBatchEvent):
                        logger.info(
                            f"CalendarBatchEvent contains {len(calendar_data.events)} events"
                        )
                elif typed_message.is_contact_event():
                    contact_data = typed_message.data
                    if isinstance(contact_data, ContactBatchEvent):
                        logger.info(
                            f"ContactBatchEvent contains {len(contact_data.contacts)} contacts"
                        )

            result = await processor(typed_message.data)
            logger.info(
                f"Successfully processed message from {topic_name}: {message_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error processing message from {topic_name}: {e}")
            raise

    async def _process_email_message(self, data: EmailBackfillEvent) -> None:
        """Process an email message for Vespa indexing using typed EmailBackfillEvent"""

        logger.info(
            f"Processing EmailBackfillEvent with {len(data.emails)} emails for user {data.user_id}"
        )

        for i, email in enumerate(data.emails):
            try:
                # Log email processing with key details in one line
                logger.info(
                    f"Processing email {i+1}/{len(data.emails)}: ID={email.id}, "
                    f"Subject='{email.subject or 'No subject'}', Provider={email.provider}"
                )

                # Validate email data quality and log warnings for missing/empty fields
                self._validate_email_data_quality(email, data.user_id, i)

                # Create typed document object
                document = VespaDocumentType(
                    id=email.id,
                    user_id=data.user_id,  # Use the user_id from the event
                    type="email",
                    provider=email.provider,
                    subject=email.subject or "",
                    body=email.body or "",
                    from_address=email.from_address or "",
                    to_addresses=email.to_addresses or [],
                    thread_id=email.thread_id,
                    folder="",  # Not available in current model
                    created_at=email.received_date,
                    updated_at=email.sent_date,
                    metadata={
                        "is_read": email.is_read,
                        "is_starred": email.is_starred,
                        "has_attachments": email.has_attachments,
                        "labels": email.labels,
                        "size_bytes": email.size_bytes,
                        "mime_type": email.mime_type,
                        "headers": email.headers or {},
                    },
                    content_chunks=[],
                    quoted_content="",
                    thread_summary={},
                    search_text="",
                )

                await self._ingest_document(document)
            except Exception as e:
                logger.error(f"Failed to process email {i+1} from batch: {e}")
                # Continue processing other emails in the batch
                continue

    async def _process_calendar_message(
        self, data: Union[CalendarUpdateEvent, CalendarBatchEvent]
    ) -> None:
        """Process a calendar message for Vespa indexing using typed events"""

        if isinstance(data, CalendarUpdateEvent):
            logger.info(f"Processing CalendarUpdateEvent for user {data.user_id}")
            # Create typed document object
            document = VespaDocumentType(
                id=data.event.id,
                user_id=data.user_id,
                type="calendar",
                provider=data.event.provider,
                subject=data.event.title,
                body=data.event.description or "",
                from_address=data.event.organizer,
                to_addresses=data.event.attendees,
                thread_id="",
                folder=data.event.calendar_id,
                created_at=data.event.start_time,
                updated_at=data.event.end_time,
                metadata={
                    "event_type": "calendar",
                    "all_day": data.event.all_day,
                    "location": data.event.location,
                    "status": data.event.status,
                    "visibility": data.event.visibility,
                    "recurrence": data.event.recurrence,
                    "reminders": data.event.reminders,
                    "attachments": data.event.attachments,
                    "color_id": data.event.color_id,
                    "html_link": data.event.html_link,
                },
            )
            await self._ingest_document(document)

        elif isinstance(data, CalendarBatchEvent):
            logger.info(
                f"Processing CalendarBatchEvent with {len(data.events)} events for user {data.user_id}"
            )

            for i, event in enumerate(data.events):
                try:
                    # Log calendar event processing with key details in one line
                    logger.info(
                        f"Processing calendar event {i+1}/{len(data.events)}: "
                        f"ID={event.id}, Title='{event.title or 'No title'}', "
                        f"Provider={event.provider}"
                    )

                    document = VespaDocumentType(
                        id=event.id,
                        user_id=data.user_id,
                        type="calendar",
                        provider=event.provider,
                        subject=event.title,
                        body=event.description or "",
                        from_address=event.organizer,
                        to_addresses=event.attendees,
                        thread_id="",
                        folder=event.calendar_id,
                        created_at=event.start_time,
                        updated_at=event.end_time,
                        metadata={
                            "event_type": "calendar",
                            "all_day": event.all_day,
                            "location": event.location,
                            "status": event.status,
                            "visibility": event.visibility,
                            "recurrence": event.recurrence,
                            "reminders": event.reminders,
                            "attachments": event.attachments,
                            "color_id": event.color_id,
                            "html_link": event.html_link,
                        },
                    )

                    await self._ingest_document(document)
                except Exception as e:
                    logger.error(
                        f"Failed to process calendar event {i+1} from batch: {e}"
                    )
                    continue

    async def _process_contact_message(
        self, data: Union[ContactUpdateEvent, ContactBatchEvent]
    ) -> None:
        """Process a contact message for Vespa indexing using typed events"""

        if isinstance(data, ContactUpdateEvent):
            logger.info(f"Processing ContactUpdateEvent for user {data.user_id}")
            # Create typed document object
            document = VespaDocumentType(
                id=data.contact.id,
                user_id=data.user_id,
                type="contact",
                provider=data.contact.provider,
                subject=data.contact.display_name,
                body=data.contact.notes or "",
                from_address="",
                to_addresses=data.contact.email_addresses,
                thread_id="",
                folder="",
                created_at=None,
                updated_at=data.contact.last_modified,
                metadata={
                    "contact_type": "contact",
                    "given_name": data.contact.given_name,
                    "family_name": data.contact.family_name,
                    "phone_numbers": data.contact.phone_numbers,
                    "addresses": data.contact.addresses,
                    "organizations": data.contact.organizations,
                    "birthdays": (
                        [bd.isoformat() for bd in data.contact.birthdays]
                        if data.contact.birthdays
                        else []
                    ),
                    "photos": data.contact.photos,
                    "groups": data.contact.groups,
                    "tags": data.contact.tags,
                },
            )
            await self._ingest_document(document)

        elif isinstance(data, ContactBatchEvent):
            logger.info(
                f"Processing ContactBatchEvent with {len(data.contacts)} contacts for user {data.user_id}"
            )

            for i, contact in enumerate(data.contacts):
                try:
                    # Log contact processing with key details in one line
                    logger.info(
                        f"Processing contact {i+1}/{len(data.contacts)}: "
                        f"ID={contact.id}, Name='{(contact.given_name or '') + ' ' + (contact.family_name or '')}'.strip(), "
                        f"Provider={contact.provider}"
                    )

                    document = VespaDocumentType(
                        id=contact.id,
                        user_id=data.user_id,
                        type="contact",
                        provider=contact.provider,
                        subject=contact.display_name,
                        body=contact.notes or "",
                        from_address="",
                        to_addresses=contact.email_addresses,
                        thread_id="",
                        folder="",
                        created_at=None,
                        updated_at=contact.last_modified,
                        metadata={
                            "contact_type": "contact",
                            "given_name": contact.given_name,
                            "family_name": contact.family_name,
                            "phone_numbers": contact.phone_numbers,
                            "addresses": contact.addresses,
                            "organizations": contact.organizations,
                            "birthdays": (
                                [bd.isoformat() for bd in contact.birthdays]
                                if contact.birthdays
                                else []
                            ),
                            "photos": contact.photos,
                            "groups": contact.groups,
                            "tags": contact.tags,
                        },
                    )

                    await self._ingest_document(document)
                except Exception as e:
                    logger.error(f"Failed to process contact {i+1} from batch: {e}")
                    continue

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

    def _validate_email_data_quality(
        self, email: EmailData, user_id: str, email_index: int
    ) -> None:
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
                f"Email data quality issues detected for user {user_id}, email {email_index + 1}: "
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
