#!/usr/bin/env python3
"""
Pub/Sub Consumer for Vespa Loader Service

This module handles consuming messages from Pub/Sub topics and processing them
for Vespa indexing. It listens to the backfill topics and processes emails,
calendar events, and contacts.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
import time

try:
    from google.cloud import pubsub_v1
    from google.cloud.pubsub_v1.types import ReceivedMessage
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    logging.warning("Google Cloud Pub/Sub not available. Install with: pip install google-cloud-pubsub")

from services.common.logging_config import get_logger
from services.vespa_loader.settings import Settings

logger = get_logger(__name__)

class PubSubConsumer:
    """Consumes messages from Pub/Sub topics for Vespa indexing"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.subscriber = None
        self.subscriptions = {}
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        
        # Topic configurations
        self.topics = {
            "email-backfill": {
                "subscription_name": "vespa-loader-email-backfill",
                "processor": self._process_email_message,
                "batch_size": 50
            },
            "calendar-updates": {
                "subscription_name": "vespa-loader-calendar-updates", 
                "processor": self._process_calendar_message,
                "batch_size": 20
            },
            "contact-updates": {
                "subscription_name": "vespa-loader-contact-updates",
                "processor": self._process_contact_message,
                "batch_size": 100
            }
        }
        
        # Batch processing
        self.message_batches = {topic: [] for topic in self.topics}
        self.batch_timers = {}
        self.batch_timeout = 5.0  # seconds
        
        # Event loop reference for cross-thread communication
        self.loop = None
        
    async def start(self):
        """Start the Pub/Sub consumer"""
        if not PUBSUB_AVAILABLE:
            logger.error("Pub/Sub not available - cannot start consumer")
            return False
            
        try:
            # Initialize subscriber client with emulator configuration
            if hasattr(self.settings, 'pubsub_emulator_host'):
                # Use local emulator
                import os
                os.environ["PUBSUB_EMULATOR_HOST"] = self.settings.pubsub_emulator_host
                logger.info(f"Using Pub/Sub emulator at {self.settings.pubsub_emulator_host}")
            
            self.subscriber = pubsub_v1.SubscriberClient()
            
            # Store event loop reference for cross-thread communication
            self.loop = asyncio.get_running_loop()
            
            # Create subscriptions if they don't exist
            await self._ensure_subscriptions()
            
            # Start consuming from each topic
            for topic_name, config in self.topics.items():
                await self._start_topic_consumer(topic_name, config)
            
            self.running = True
            logger.info("Pub/Sub consumer started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Pub/Sub consumer: {e}")
            return False
    
    async def stop(self):
        """Stop the Pub/Sub consumer"""
        self.running = False
        
        # Cancel all batch timers
        for timer in self.batch_timers.values():
            if timer and not timer.done():
                timer.cancel()
        
        # Close subscriber
        if self.subscriber:
            self.subscriber.close()
            self.subscriber = None
            
        logger.info("Pub/Sub consumer stopped")
    
    async def _ensure_subscriptions(self):
        """Ensure all required subscriptions exist"""
        project_id = self.settings.pubsub_project_id if hasattr(self.settings, 'pubsub_project_id') else "briefly-dev"
        
        for topic_name, config in self.topics.items():
            subscription_path = self.subscriber.subscription_path(
                project_id, 
                config["subscription_name"]
            )
            
            try:
                # Try to create subscription (will fail if it already exists)
                topic_path = self.subscriber.topic_path(project_id, topic_name)
                self.subscriber.create_subscription(
                    name=subscription_path,
                    topic=topic_path
                )
                logger.info(f"Created subscription: {config['subscription_name']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Subscription already exists: {config['subscription_name']}")
                else:
                    logger.warning(f"Could not create subscription {config['subscription_name']}: {e}")
                    # For emulator, we might need to handle this differently
                    logger.info(f"Continuing with existing subscription setup...")
    
    async def _start_topic_consumer(self, topic_name: str, config: Dict[str, Any]):
        """Start consuming from a specific topic using polling approach"""
        project_id = self.settings.pubsub_project_id if hasattr(self.settings, 'pubsub_project_id') else "briefly-dev"
        subscription_path = self.subscriber.subscription_path(
            project_id, 
            config["subscription_name"]
        )
        
        # Store subscription info for polling
        self.subscriptions[topic_name] = {
            "subscription_path": subscription_path,
            "config": config,
            "active": True
        }
        
        # Start polling task
        asyncio.create_task(self._poll_subscription(topic_name, subscription_path, config))
        logger.info(f"Started polling from topic: {topic_name}")
    
    async def _poll_subscription(self, topic_name: str, subscription_path: str, config: Dict[str, Any]):
        """Poll a subscription for messages"""
        while self.running and self.subscriptions.get(topic_name, {}).get("active", False):
            try:
                # Pull messages from subscription
                response = self.subscriber.pull(
                    request=pubsub_v1.PullRequest(
                        subscription=subscription_path,
                        max_messages=config["batch_size"],
                        return_immediately=True
                    )
                )
                
                if response.received_messages:
                    logger.info(f"Received {len(response.received_messages)} messages from {topic_name}")
                    
                    # Process messages
                    for message in response.received_messages:
                        await self._handle_message(topic_name, message, config)
                        
                        # Acknowledge the message
                        self.subscriber.acknowledge(
                            request=pubsub_v1.AcknowledgeRequest(
                                subscription=subscription_path,
                                ack_ids=[message.ack_id]
                            )
                        )
                        
                        self.processed_count += 1
                        
                # Wait before next poll
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error polling subscription {topic_name}: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    def _handle_message_sync(self, topic_name: str, message: ReceivedMessage, config: Dict[str, Any]):
        """Handle a single message from Pub/Sub synchronously (called from callback)"""
        try:
            # Parse message data
            data = json.loads(message.data.decode("utf-8"))
            
            # Add to batch
            self.message_batches[topic_name].append({
                "message": message,
                "data": data,
                "timestamp": time.time()
            })
            
            # Process batch if it's full or start timer for partial batch
            if len(self.message_batches[topic_name]) >= config["batch_size"]:
                # Schedule async processing
                asyncio.run_coroutine_threadsafe(
                    self._process_batch(topic_name, config),
                    self.loop
                )
            else:
                # Start timer for partial batch
                asyncio.run_coroutine_threadsafe(
                    self._schedule_batch_processing(topic_name, config),
                    self.loop
                )
                
        except Exception as e:
            logger.error(f"Error handling message from {topic_name}: {e}")
            message.nack()
            self.error_count += 1

    async def _handle_message(self, topic_name: str, message: ReceivedMessage, config: Dict[str, Any]):
        """Handle a single message from Pub/Sub (async version for compatibility)"""
        try:
            # Parse message data
            data = json.loads(message.data.decode("utf-8"))
            
            # Add to batch
            self.message_batches[topic_name].append({
                "message": message,
                "data": data,
                "timestamp": time.time()
            })
            
            # Process batch if it's full or start timer for partial batch
            if len(self.message_batches[topic_name]) >= config["batch_size"]:
                await self._process_batch(topic_name, config)
            else:
                # Start timer for partial batch
                await self._schedule_batch_processing(topic_name, config)
                
        except Exception as e:
            logger.error(f"Error handling message from {topic_name}: {e}")
            message.nack()
            self.error_count += 1
    
    async def _schedule_batch_processing(self, topic_name: str, config: Dict[str, Any]):
        """Schedule batch processing for a topic"""
        # Cancel existing timer if any
        if topic_name in self.batch_timers and self.batch_timers[topic_name]:
            self.batch_timers[topic_name].cancel()
        
        # Create new timer
        self.batch_timers[topic_name] = asyncio.create_task(
            self._delayed_batch_processing(topic_name, config)
        )
    
    async def _delayed_batch_processing(self, topic_name: str, config: Dict[str, Any]):
        """Process batch after timeout delay"""
        await asyncio.sleep(self.batch_timeout)
        
        if self.message_batches[topic_name]:
            await self._process_batch(topic_name, config)
    
    async def _process_batch(self, topic_name: str, config: Dict[str, Any]):
        """Process a batch of messages"""
        if not self.message_batches[topic_name]:
            return
            
        batch = self.message_batches[topic_name]
        self.message_batches[topic_name] = []
        
        logger.info(f"Processing batch of {len(batch)} messages from {topic_name}")
        
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
                logger.error(f"Failed to process message {i} from {topic_name}: {result}")
                item["message"].nack()
                self.error_count += 1
            else:
                item["message"].ack()
                self.processed_count += 1
        
        logger.info(f"Completed processing batch from {topic_name}: {len(batch)} messages")
    
    async def _process_single_message(self, topic_name: str, item: Dict[str, Any], config: Dict[str, Any]):
        """Process a single message"""
        try:
            # Call the appropriate processor
            processor = config["processor"]
            logger.info(f"Calling processor for message from {topic_name}: {item['data'].get('id', 'unknown')}")
            result = await processor(item["data"])
            logger.info(f"Successfully processed message from {topic_name}: {item['data'].get('id', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing message from {topic_name}: {e}")
            raise
    
    async def _process_email_message(self, data: Dict[str, Any]):
        """Process an email message for Vespa indexing"""
        logger.info(f"Processing email message: {data.get('id', 'unknown')} for user {data.get('user_id', 'unknown')}")
        
        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)
    
    async def _process_calendar_message(self, data: Dict[str, Any]):
        """Process a calendar message for Vespa indexing"""
        logger.info(f"Processing calendar message: {data.get('id', 'unknown')} for user {data.get('user_id', 'unknown')}")
        
        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)
    
    async def _process_contact_message(self, data: Dict[str, Any]):
        """Process a contact message for Vespa indexing"""
        logger.info(f"Processing contact message: {data.get('id', 'unknown')} for user {data.get('user_id', 'unknown')}")
        
        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)
    
    async def _call_ingest_endpoint(self, data: Dict[str, Any]):
        """Call the Vespa loader ingest endpoint"""
        try:
            import httpx
            
            logger.info(f"Starting ingest for document {data.get('id')} from user {data.get('user_id')}")
            
            # Determine the source type from the data
            source_type = data.get('type', 'email')  # Default to email
            
            # Map the data to the expected format for the ingest endpoint
            document_data = {
                "id": data.get('id'),
                "user_id": data.get('user_id'),
                "source_type": source_type,
                "provider": data.get('provider'),
                "subject": data.get('subject', ''),
                "body": data.get('body', ''),
                "from": data.get('from', ''),
                "to": data.get('to', []),
                "thread_id": data.get('thread_id', ''),
                "folder": data.get('folder', ''),
                "created_at": data.get('created_at'),
                "updated_at": data.get('updated_at'),
                "metadata": data.get('metadata', {}),
                "timestamp": data.get('timestamp')
            }
            
            logger.info(f"Document data prepared: {document_data}")
            
            # Call the ingest endpoint
            async with httpx.AsyncClient() as client:
                logger.info(f"Making HTTP POST to ingest endpoint for document {data.get('id')}")
                response = await client.post(
                    "http://localhost:9001/ingest",
                    json=document_data,
                    timeout=30.0
                )
                
                logger.info(f"Received response for document {data.get('id')}: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Successfully indexed document {data.get('id')}: {result}")
                    return result
                else:
                    logger.error(f"Failed to index document {data.get('id')}: {response.status_code} - {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error calling ingest endpoint for document {data.get('id')}: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        return {
            "running": self.running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "active_batches": {topic: len(batch) for topic, batch in self.message_batches.items()},
            "subscriptions": list(self.subscriptions.keys())
        }
