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

from services.common.logging_config import get_logger
from services.vespa_loader.settings import Settings
from services.vespa_loader.email_processor import EmailContentProcessor

logger = get_logger(__name__)

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

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
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
        self.message_batches: Dict[str, List[Dict[str, Any]]] = {
            topic: [] for topic in self.topics
        }
        self.batch_timers: Dict[str, Optional[asyncio.Task[Any]]] = {}
        self.batch_timeout = 5.0  # seconds

        # Event loop reference for cross-thread communication
        self.loop: Optional[asyncio.AbstractEventLoop] = None

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

    async def _create_subscription_if_not_exists(self, topic_name: str, config: Dict[str, Any]) -> None:
        """Create a subscription if it doesn't exist using Python Pub/Sub client"""
        try:
            import asyncio
            
            subscription_name = config['subscription_name']
            topic_path = f"projects/{self.settings.pubsub_project_id}/topics/{topic_name}"
            subscription_path = f"projects/{self.settings.pubsub_project_id}/subscriptions/{subscription_name}"
            
            # Check if subscription already exists by trying to get it
            try:
                # Use the subscriber client to check if subscription exists
                if self.subscriber:
                    subscription = self.subscriber.get_subscription(request={"subscription": subscription_path})
                    if subscription:
                        logger.info(f"Subscription {subscription_name} already exists for topic {topic_name}")
                        return
            except Exception:
                # Subscription doesn't exist, create it
                pass
            
            # Create the subscription using the subscriber client
            try:
                # The subscriber client can create subscriptions
                if self.subscriber:
                    subscription = self.subscriber.create_subscription(
                        request={
                            "name": subscription_path,
                            "topic": topic_path
                        }
                    )
                    logger.info(f"Successfully created subscription {subscription_name} for topic {topic_name}")
                
            except Exception as e:
                logger.warning(f"Failed to create subscription {subscription_name} using subscriber client: {e}")
                
        except Exception as e:
            logger.warning(f"Could not create subscription {config['subscription_name']} for topic {topic_name}: {e}")
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
                logger.debug(f"Received message from {topic_name}: {message.message_id}")
                logger.debug(f"Message data length: {len(message.data)} bytes")
                
                # Parse message data
                data = json.loads(message.data.decode("utf-8"))
                logger.debug(f"Parsed message data: {data.get('id', 'unknown')} for user {data.get('user_id', 'unknown')}")

                # Add to batch
                self.message_batches[topic_name].append(
                    {"message": message, "data": data, "timestamp": time.time()}
                )
                logger.debug(f"Added message to batch for {topic_name}. Batch size: {len(self.message_batches[topic_name])}")

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
                    if topic_name not in self.batch_timers or not timer or (timer is not None and timer.done()):
                        logger.debug(f"Starting timer for partial batch in {topic_name}")
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
        logger.info(f"Message IDs: {[item['data'].get('id', 'unknown') for item in batch]}")

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
        for i, (item, result) in enumerate(zip(batch, results)):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to process message {i} from {topic_name}: {result}"
                )
                item["message"].nack()
                self.error_count += 1
            else:
                item["message"].ack()
                self.processed_count += 1

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
            message_id = item['data'].get('id', 'unknown')
            user_id = item['data'].get('user_id', 'unknown')
            
            logger.info(
                f"Calling processor for message from {topic_name}: {message_id} for user {user_id}"
            )
            result = await processor(item["data"])
            logger.info(
                f"Successfully processed message from {topic_name}: {message_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error processing message from {topic_name}: {e}")
            raise

    async def _process_email_message(self, data: Dict[str, Any]) -> None:
        """Process an email message for Vespa indexing"""
        message_id = data.get('id', 'unknown')
        user_id = data.get('user_id', 'unknown')
        
        logger.info(
            f"Processing email message: {message_id} for user {user_id}"
        )
        logger.info(f"Email subject: {data.get('subject', 'no subject')}")
        logger.info(f"Email provider: {data.get('provider', 'unknown')}")

        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)

    async def _process_calendar_message(self, data: Dict[str, Any]) -> None:
        """Process a calendar message for Vespa indexing"""
        message_id = data.get('id', 'unknown')
        user_id = data.get('user_id', 'unknown')
        
        logger.info(
            f"Processing calendar message: {message_id} for user {user_id}"
        )

        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)

    async def _process_contact_message(self, data: Dict[str, Any]) -> None:
        """Process a contact message for Vespa indexing"""
        message_id = data.get('id', 'unknown')
        user_id = data.get('user_id', 'unknown')
        
        logger.info(
            f"Processing contact message: {message_id} for user {user_id}"
        )

        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)

    async def _call_ingest_endpoint(self, data: Dict[str, Any]) -> None:
        """Call the Vespa loader ingest endpoint"""
        try:
            import httpx

            message_id = data.get('id')
            user_id = data.get('user_id')
            
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
            logger.info(f"Making HTTP POST to ingest endpoint for document {message_id}")

            # Call the ingest endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:9001/ingest", json=document_data, timeout=30.0
                )

                logger.info(
                    f"Received response for document {message_id}: {response.status_code}"
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Successfully indexed document {message_id}: {result}"
                    )
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
                    "path": sub.get("path", "unknown")
                } for topic, sub in self.subscriptions.items()
            }
        }
        logger.info(f"Consumer stats: {stats}")
        return stats
