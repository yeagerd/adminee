#!/usr/bin/env python3
"""
Pub/Sub Consumer for Vespa Loader Service

This module handles consuming messages from Pub/Sub topics and processing them
for Vespa indexing. It listens to the new data-type focused topics and processes
emails, calendar events, contacts, documents, and todos.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from services.common.config.subscription_config import SubscriptionConfig
from services.common.logging_config import get_logger
from services.vespa_loader.document_factory import process_message
from services.vespa_loader.ingest_service import ingest_document_service
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
    ) -> None:
        self.settings = settings
        self.vespa_client = vespa_client
        self.content_normalizer = content_normalizer
        self.embedding_generator = embedding_generator

        self.subscriber: Optional[Any] = None
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.processed_count = 0
        self.error_count = 0

        # Note: Using process_message function instead of instance methods

        # Configure new data-type focused topics using shared configuration
        self.topics = {}
        for topic_name in SubscriptionConfig.get_service_topics("vespa_loader"):
            config = SubscriptionConfig.get_subscription_config(
                "vespa_loader", topic_name
            )
            self.topics[topic_name] = {
                "subscription_name": config["subscription_name"],
            }

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
                    max_messages=100,
                    max_bytes=1024
                    * 1024,  # 1MB, process up to 100 messages concurrently
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

                # Process message into Vespa document using unified processor
                try:
                    vespa_document = process_message(
                        topic_name, raw_data, message.message_id
                    )

                    logger.debug(
                        f"Processed message data: message_id={message.message_id}, user_id={vespa_document.user_id}, doc_id={vespa_document.id}"
                    )

                    # Process message immediately - no batching needed
                    if self.loop:
                        # Schedule immediate processing in the event loop
                        asyncio.run_coroutine_threadsafe(
                            self._process_message_immediate(vespa_document, message),
                            self.loop,
                        )
                    else:
                        logger.error("No event loop available for message processing")
                        message.nack()
                        self.error_count += 1

                except Exception as parse_error:
                    logger.error(
                        f"Failed to parse message from {topic_name}: {parse_error}"
                    )
                    message.nack()
                    self.error_count += 1

            except Exception as e:
                logger.error(f"Error handling message from {topic_name}: {e}")
                message.nack()
                self.error_count += 1

        return message_callback

    async def _process_message_immediate(
        self, vespa_document: VespaDocumentType, message: Any
    ) -> None:
        """Process a single message immediately"""
        try:
            logger.info(
                f"Processing document {vespa_document.id} (type: {vespa_document.type}) "
                f"from message {message.message_id} for user {vespa_document.user_id}"
            )

            # Document is already processed, just ingest it
            result = await ingest_document_service(
                vespa_document,
                self.vespa_client,
                self.content_normalizer,
                self.embedding_generator,
            )

            logger.info(
                f"Successfully ingested document {vespa_document.id} from message {message.message_id}"
            )

            # Acknowledge the message on success
            message.ack()
            self.processed_count += 1

        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {e}")
            message.nack()
            self.error_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        stats = {
            "running": self.running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
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
