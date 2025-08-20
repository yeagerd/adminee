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
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from services.common.events import (
    BaseEvent,
    CalendarBatchEvent,
    CalendarUpdateEvent,
    ContactBatchEvent,
    ContactUpdateEvent,
    EmailBackfillEvent,
    EmailBatchEvent,
    EmailUpdateEvent,
)
from services.common.logging_config import get_logger
from services.common.pubsub_client import PubSubConsumer as CommonPubSubConsumer
from services.vespa_loader.email_processor import EmailContentProcessor
from services.vespa_loader.settings import Settings

logger = get_logger(__name__)


class PubSubConsumer:
    """Consumes messages from Pub/Sub topics for Vespa indexing using common pubsub_client"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # Initialize common pubsub consumer
        self.pubsub_consumer: Optional[CommonPubSubConsumer] = CommonPubSubConsumer(
            project_id=settings.pubsub_project_id,
            emulator_host=settings.pubsub_emulator_host,
            service_name="vespa-loader-service",
        )

        self.subscriptions: Dict[str, Any] = {}
        self.running = False
        self.processed_count = 0
        self.error_count = 0

        # Initialize email content processor
        self.email_processor = EmailContentProcessor()

        # Configure topics and their processors
        self.topics = {
            "email-backfill": {
                "subscription_name": "vespa-loader-email-backfill",
                "processor": self._process_email_backfill_event,
                "batch_size": 50,
            },
            "calendar-updates": {
                "subscription_name": "vespa-loader-calendar-updates",
                "processor": self._process_calendar_update_event,
                "batch_size": 20,
            },
            "contact-updates": {
                "subscription_name": "vespa-loader-contact-updates",
                "processor": self._process_contact_update_event,
                "batch_size": 100,
            },
        }

        # Batch processing
        self.message_batches: Dict[str, List[Any]] = {
            topic: [] for topic in self.topics
        }
        # Store original message objects for conditional ack/nack
        self.message_objects: Dict[str, List[Any]] = {
            topic: [] for topic in self.topics
        }
        self.batch_timers: Dict[str, Optional[asyncio.Task[Any]]] = {}
        self.batch_timeout = 5.0  # seconds

        # Event loop reference for cross-thread communication
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> bool:
        """Start the Pub/Sub consumer"""
        if not self.pubsub_consumer:
            logger.error("Pub/Sub consumer not initialized - cannot start consumer")
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
        if self.pubsub_consumer:
            self.pubsub_consumer.close()
            self.pubsub_consumer = None

        logger.info("Pub/Sub consumer stopped")

    async def _ensure_subscriptions(self) -> None:
        """Ensure all required subscriptions exist"""
        if not self.pubsub_consumer:
            logger.error("PubSubConsumer not initialized")
            return

        logger.info("Ensuring subscriptions exist...")
        for topic_name, config in self.topics.items():
            try:
                subscription_name = config["subscription_name"]
                topic_path = (
                    f"projects/{self.settings.pubsub_project_id}/topics/{topic_name}"
                )
                subscription_path = f"projects/{self.settings.pubsub_project_id}/subscriptions/{subscription_name}"

                logger.info(f"Subscription path for {topic_name}: {subscription_path}")
                logger.info(f"Subscription name: {subscription_name}")

                # Try to create the subscription using the common pubsub client
                await self._create_subscription_if_not_exists(topic_name, config)

            except Exception as e:
                logger.error(f"Error setting up subscription for {topic_name}: {e}")

    async def _create_subscription_if_not_exists(
        self, topic_name: str, config: Dict[str, Any]
    ) -> None:
        """Create a subscription if it doesn't exist"""
        try:
            subscription_name = config["subscription_name"]
            topic_path = (
                f"projects/{self.settings.pubsub_project_id}/topics/{topic_name}"
            )
            subscription_path = f"projects/{self.settings.pubsub_project_id}/subscriptions/{subscription_name}"

            # For now, we'll assume subscriptions exist or are created externally
            # In a production environment, you'd want to check and create them here
            logger.info(
                f"Subscription {subscription_name} configured for topic {topic_name}"
            )

        except Exception as e:
            logger.warning(
                f"Could not verify subscription {config['subscription_name']} for topic {topic_name}: {e}"
            )

    async def _start_topic_consumer(
        self, topic_name: str, config: Dict[str, Any]
    ) -> None:
        """Start consuming from a specific topic using the common pubsub client"""
        if not self.pubsub_consumer:
            logger.error("PubSubConsumer not initialized")
            return

        try:
            subscription_name = config["subscription_name"]

            # Use the common pubsub client to subscribe
            subscription = self.pubsub_consumer.subscribe(
                topic_name=topic_name,
                subscription_name=subscription_name,
                callback=self._create_message_callback(topic_name, config),
                max_messages=config["batch_size"],
                max_bytes=1024 * 1024,  # 1MB
            )

            self.subscriptions[topic_name] = subscription
            logger.info(
                f"Started consuming from topic {topic_name} with subscription {subscription_name}"
            )

        except Exception as e:
            logger.error(f"Failed to start consumer for topic {topic_name}: {e}")
            raise

    def _create_message_callback(
        self, topic_name: str, config: Dict[str, Any]
    ) -> Callable[[Any], None]:
        """Create a callback function for processing messages from a topic"""
        processor = config["processor"]

        def callback(message: Any) -> None:
            """Callback function for processing messages"""
            try:
                # Extract message data
                if hasattr(message, "data"):
                    data = json.loads(message.data.decode("utf-8"))
                else:
                    data = message

                # Add message to batch
                self.message_batches[topic_name].append(data)
                # Store original message object
                self.message_objects[topic_name].append(message)

                # Process batch if it's full or if timer expires
                if len(self.message_batches[topic_name]) >= config["batch_size"]:
                    asyncio.create_task(self._process_batch(topic_name, config))
                else:
                    # Start or reset batch timer
                    self._start_batch_timer(topic_name, config)

                # Message acknowledgment is deferred until after batch processing
                # to allow for conditional ack/nack based on processing results

            except Exception as e:
                logger.error(f"Error in message callback for topic {topic_name}: {e}")
                # Nack the message to retry if there's an error in the callback
                if hasattr(message, "nack"):
                    message.nack()
                # Don't add to batch if callback processing fails

        return callback

    def _start_batch_timer(self, topic_name: str, config: Dict[str, Any]) -> None:
        """Start or reset the batch timer for a topic"""
        # Cancel existing timer if it exists
        if (
            topic_name in self.batch_timers
            and self.batch_timers[topic_name] is not None
        ):
            existing_timer = self.batch_timers[topic_name]
            if existing_timer is not None:
                existing_timer.cancel()

        # Create new timer
        async def timer_callback() -> None:
            await asyncio.sleep(self.batch_timeout)
            if topic_name in self.message_batches and self.message_batches[topic_name]:
                asyncio.create_task(self._process_batch(topic_name, config))

        self.batch_timers[topic_name] = asyncio.create_task(timer_callback())

    async def _process_email_backfill_event(self, event: EmailBackfillEvent) -> None:
        """Process an email backfill event for Vespa indexing"""
        logger.info(
            "Processing email backfill event",
            extra={
                "event_id": event.metadata.event_id,
                "user_id": event.user_id,
                "provider": event.provider,
                "batch_size": event.batch_size,
                "sync_type": event.sync_type,
            },
        )

        # Process each email in the batch
        for email_data in event.emails:
            try:
                # Convert EmailData to the format expected by the email processor
                email_dict = {
                    "id": email_data.id,
                    "user_id": event.user_id,
                    "subject": email_data.subject,
                    "body": email_data.body,
                    "from": email_data.from_address,
                    "to": email_data.to_addresses,
                    "cc": email_data.cc_addresses,
                    "bcc": email_data.bcc_addresses,
                    "received_date": email_data.received_date.isoformat(),
                    "sent_date": (
                        email_data.sent_date.isoformat()
                        if email_data.sent_date
                        else None
                    ),
                    "labels": email_data.labels,
                    "is_read": email_data.is_read,
                    "is_starred": email_data.is_starred,
                    "has_attachments": email_data.has_attachments,
                    "provider": email_data.provider,
                    "provider_message_id": email_data.provider_message_id,
                }

                # Process the email for Vespa indexing
                await self._call_ingest_endpoint(email_dict)

            except Exception as e:
                logger.error(
                    f"Failed to process email {email_data.id}",
                    extra={
                        "email_id": email_data.id,
                        "user_id": event.user_id,
                        "error": str(e),
                    },
                )
                self.error_count += 1

        self.processed_count += len(event.emails)

    async def _process_calendar_update_event(self, event: CalendarUpdateEvent) -> None:
        """Process a calendar update event for Vespa indexing"""
        logger.info(
            "Processing calendar update event",
            extra={
                "event_id": event.metadata.event_id,
                "user_id": event.user_id,
                "calendar_event_id": event.event.id,
                "update_type": event.update_type,
            },
        )

        # Convert CalendarEventData to the format expected by the ingest endpoint
        calendar_dict = {
            "id": event.event.id,
            "user_id": event.user_id,
            "title": event.event.title,
            "description": event.event.description,
            "start_time": event.event.start_time.isoformat(),
            "end_time": event.event.end_time.isoformat(),
            "all_day": event.event.all_day,
            "location": event.event.location,
            "organizer": event.event.organizer,
            "attendees": event.event.attendees,
            "status": event.event.status,
            "visibility": event.event.visibility,
            "provider": event.event.provider,
            "provider_event_id": event.event.provider_event_id,
            "calendar_id": event.event.calendar_id,
        }

        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(calendar_dict)
        self.processed_count += 1

    async def _process_contact_update_event(self, event: ContactUpdateEvent) -> None:
        """Process a contact update event for Vespa indexing"""
        logger.info(
            "Processing contact update event",
            extra={
                "event_id": event.metadata.event_id,
                "user_id": event.user_id,
                "contact_id": event.contact.id,
                "update_type": event.update_type,
            },
        )

        # Convert ContactData to the format expected by the ingest endpoint
        contact_dict = {
            "id": event.contact.id,
            "user_id": event.user_id,
            "display_name": event.contact.display_name,
            "given_name": event.contact.given_name,
            "family_name": event.contact.family_name,
            "email_addresses": event.contact.email_addresses,
            "phone_numbers": event.contact.phone_numbers,
            "addresses": event.contact.addresses,
            "organizations": event.contact.organizations,
            "birthdays": (
                [b.isoformat() for b in event.contact.birthdays]
                if event.contact.birthdays
                else []
            ),
            "notes": event.contact.notes,
            "provider": event.contact.provider,
            "provider_contact_id": event.contact.provider_contact_id,
        }

        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(contact_dict)
        self.processed_count += 1

    async def _process_batch(self, topic_name: str, config: Dict[str, Any]) -> None:
        """Process a batch of messages"""
        if not self.message_batches[topic_name]:
            logger.info(f"No messages to process for {topic_name}")
            return

        batch = self.message_batches[topic_name]
        message_objects = self.message_objects[topic_name]

        # Clear the batches
        self.message_batches[topic_name] = []
        self.message_objects[topic_name] = []

        logger.info(f"Processing batch of {len(batch)} messages from {topic_name}")
        logger.info(f"Message IDs: {[item.get('id', 'unknown') for item in batch]}")

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
        for i, (item, result, message_obj) in enumerate(
            zip(batch, results, message_objects)
        ):
            try:
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to process message {i} from {topic_name}: {result}"
                    )
                    # Nack the message to retry
                    if hasattr(message_obj, "nack"):
                        message_obj.nack()
                        logger.info(f"Nacked message {i} from {topic_name} for retry")
                    else:
                        logger.warning(
                            f"Message object does not support nack for {topic_name}"
                        )
                    self.error_count += 1
                else:
                    # Acknowledge successful processing
                    if hasattr(message_obj, "ack"):
                        message_obj.ack()
                        logger.info(f"Acknowledged message {i} from {topic_name}")
                    else:
                        logger.warning(
                            f"Message object does not support ack for {topic_name}"
                        )
                    self.processed_count += 1
            except Exception as e:
                logger.error(
                    f"Error handling message acknowledgment for {topic_name}: {e}"
                )
                # If we can't ack/nack, increment error count
                self.error_count += 1

        logger.info(
            f"Completed processing batch from {topic_name}: {len(batch)} messages"
        )

    async def _process_single_message(
        self, topic_name: str, item: Dict[str, Any], config: Dict[str, Any]
    ) -> Any:
        """Process a single message"""
        try:
            # Call the appropriate processor
            processor = config["processor"]
            message_id = item.get("id", "unknown")
            user_id = item.get("user_id", "unknown")

            logger.info(
                f"Calling processor for message from {topic_name}: {message_id} for user {user_id}"
            )

            # Deserialize the raw message data into the appropriate event type
            event_object = await self._deserialize_message(item, topic_name)
            if event_object is None:
                logger.error(
                    f"Failed to deserialize message from {topic_name}: {message_id}"
                )
                raise ValueError(f"Invalid message format for topic {topic_name}")

            # Call the processor with the properly typed event object
            result = await processor(event_object)
            logger.info(
                f"Successfully processed message from {topic_name}: {message_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error processing message from {topic_name}: {e}")
            raise

    async def _deserialize_message(
        self, raw_data: Dict[str, Any], topic_name: str
    ) -> Optional[BaseEvent]:
        """
        Deserialize raw message data into the appropriate typed event object.

        Args:
            raw_data: Raw message data from Pub/Sub
            topic_name: Name of the topic for determining event type

        Returns:
            Properly typed event object or None if deserialization fails
        """
        try:
            # The raw_data should already contain the event structure
            # We just need to validate and create the appropriate event object

            # Determine event type based on topic name and data structure
            if "email" in topic_name.lower():
                if "backfill" in topic_name.lower():
                    # Validate required fields for EmailBackfillEvent
                    required_fields = ["user_id", "provider", "emails", "batch_size"]
                    if not all(field in raw_data for field in required_fields):
                        logger.error(
                            f"Missing required fields for EmailBackfillEvent: {required_fields}"
                        )
                        return None

                    # Create the event object
                    return EmailBackfillEvent(**raw_data)
                else:
                    # Validate required fields for EmailUpdateEvent
                    required_fields = ["user_id", "email", "update_type"]
                    if not all(field in raw_data for field in required_fields):
                        logger.error(
                            f"Missing required fields for EmailUpdateEvent: {required_fields}"
                        )
                        return None

                    return EmailUpdateEvent(**raw_data)

            elif "calendar" in topic_name.lower():
                # Validate required fields for CalendarUpdateEvent
                required_fields = ["user_id", "event", "update_type"]
                if not all(field in raw_data for field in required_fields):
                    logger.error(
                        f"Missing required fields for CalendarUpdateEvent: {required_fields}"
                    )
                    return None

                return CalendarUpdateEvent(**raw_data)

            elif "contact" in topic_name.lower():
                # Validate required fields for ContactUpdateEvent
                required_fields = ["user_id", "contact", "update_type"]
                if not all(field in raw_data for field in required_fields):
                    logger.error(
                        f"Missing required fields for ContactUpdateEvent: {required_fields}"
                    )
                    return None

                return ContactUpdateEvent(**raw_data)
            else:
                logger.warning(
                    f"Unknown topic type: {topic_name}, cannot deserialize message"
                )
                return None

        except Exception as e:
            logger.error(
                f"Failed to deserialize message for topic {topic_name}: {e}",
                extra={
                    "raw_data_keys": list(raw_data.keys()) if raw_data else [],
                    "topic_name": topic_name,
                },
            )
            return None

    async def _call_ingest_endpoint(self, data: Dict[str, Any]) -> None:
        """Call the Vespa loader ingest endpoint"""
        try:
            import httpx

            message_id = data.get("id")
            user_id = data.get("user_id")

            logger.info(
                f"Starting ingest for document {message_id} from user {user_id}"
            )

            # Determine the source type from the data
            source_type = data.get("type", "email")  # Default to email

            # Process email data using the email processor if it's an email
            if source_type == "email":
                processed_data = self.email_processor.process_email(data)
                document_data = {
                    "id": processed_data.get("id"),
                    "user_id": processed_data.get("user_id"),
                    "type": source_type,
                    "provider": processed_data.get("provider"),
                    "subject": processed_data.get("subject", ""),
                    "body": processed_data.get("body", ""),
                    "from": processed_data.get("from", ""),
                    "to": processed_data.get("to", []),
                    "thread_id": processed_data.get("thread_id", ""),
                    "folder": processed_data.get("folder", ""),
                    "created_at": processed_data.get("created_at"),
                    "updated_at": processed_data.get("updated_at"),
                    "metadata": processed_data.get("metadata", {}),
                    # Add processed content fields
                    "content_chunks": processed_data.get("content_chunks", []),
                    "quoted_content": processed_data.get("quoted_content", ""),
                    "thread_summary": processed_data.get("thread_summary", {}),
                    "search_text": processed_data.get("search_text", ""),
                }
            else:
                # For non-email documents, use basic mapping
                document_data = {
                    "id": data.get("id"),
                    "user_id": data.get("user_id"),
                    "type": source_type,
                    "provider": data.get("provider"),
                    "subject": data.get("subject", ""),
                    "body": data.get("body", ""),
                    "from": data.get("from", ""),
                    "to": data.get("to", []),
                    "thread_id": data.get("thread_id", ""),
                    "folder": data.get("folder", ""),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "metadata": data.get("metadata", {}),
                }

            logger.info(f"Document data prepared: {document_data}")
            logger.info(
                f"Making HTTP POST to ingest endpoint for document {message_id}"
            )

            # Call the ingest endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.settings.ingest_endpoint, json=document_data, timeout=30.0
                )

                logger.info(
                    f"Received response for document {message_id}: {response.status_code}"
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Successfully indexed document {message_id}: {result}")
                    return result
                else:
                    logger.error(
                        f"Failed to index document {message_id}: {response.status_code} - {response.text}"
                    )
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(
                f"Error calling ingest endpoint for document {data.get('id')}: {e}"
            )
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
