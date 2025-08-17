#!/usr/bin/env python3
"""
Pub/Sub Consumer for Vespa Loader Service

This module handles consuming messages from Pub/Sub topics and processing them
for Vespa indexing. It listens to the backfill topics and processes emails,
calendar events, and contacts.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timezone
import time

from services.common.logging_config import get_logger
from services.vespa_loader.settings import Settings

logger = get_logger(__name__)

try:
    from google.cloud import pubsub_v1
    from google.cloud.pubsub_v1.types import ReceivedMessage
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    logger.warning("Google Cloud Pub/Sub not available. Install with: pip install google-cloud-pubsub")

class PubSubConsumer:
    """Consumes messages from Pub/Sub topics for Vespa indexing"""
    
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.subscriber: Optional[pubsub_v1.SubscriberClient] = None
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
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
        self.message_batches: Dict[str, List[Dict[str, Any]]] = {topic: [] for topic in self.topics}
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
        self.running = False
        
        # Cancel all subscriptions
        for topic_name, subscription in self.subscriptions.items():
            try:
                if subscription and hasattr(subscription, 'cancel'):
                    subscription.cancel()
                    logger.info(f"Cancelled subscription for topic: {topic_name}")
            except Exception as e:
                logger.error(f"Error cancelling subscription for topic {topic_name}: {e}")
        
        # Close subscriber client
        if self.subscriber:
            self.subscriber.close()
            self.subscriber = None
        
        logger.info("Pub/Sub consumer stopped")
    
    async def _ensure_subscriptions(self) -> None:
        """Ensure all required subscriptions exist"""
        if not self.subscriber:
            return
            
        for topic_name, config in self.topics.items():
            try:
                subscription_path = self.subscriber.subscription_path(
                    self.settings.pubsub_project_id,
                    config["subscription_name"]
                )
                
                # Check if subscription exists (this is a simplified check)
                # In production, you might want to create subscriptions if they don't exist
                logger.info(f"Subscription path for {topic_name}: {subscription_path}")
                
            except Exception as e:
                logger.error(f"Error setting up subscription for {topic_name}: {e}")
    
    async def _start_topic_consumer(self, topic_name: str, config: Dict[str, Any]) -> None:
        """Start consuming from a specific topic using async callbacks"""
        if not self.subscriber:
            return
            
        try:
            subscription_path = self.subscriber.subscription_path(
                self.settings.pubsub_project_id,
                config["subscription_name"]
            )
            
            # Use the subscribe method with callbacks instead of polling
            subscription = self.subscriber.subscribe(
                subscription_path,
                callback=self._create_message_callback(topic_name, config),
                flow_control=pubsub_v1.types.FlowControl(
                    max_messages=config["batch_size"],
                    max_bytes=1024 * 1024  # 1MB
                )
            )
            
            self.subscriptions[topic_name] = {
                "subscription": subscription,
                "active": True,
                "path": subscription_path
            }
            
            logger.info(f"Started async subscription for topic: {topic_name}")
            
        except Exception as e:
            logger.error(f"Error starting topic consumer for {topic_name}: {e}")
            self.subscriptions[topic_name] = {"active": False}
    
    def _create_message_callback(self, topic_name: str, config: Dict[str, Any]) -> Callable[[Any], None]:
        """Create a callback function for processing messages from a specific topic"""
        def message_callback(message: Any) -> None:
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
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self._process_batch(topic_name, config),
                            self.loop
                        )
                else:
                    # Start timer for partial batch
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self._schedule_batch_processing(topic_name, config),
                            self.loop
                        )
                        
            except Exception as e:
                logger.error(f"Error handling message from {topic_name}: {e}")
                message.nack()
                self.error_count += 1
        
        return message_callback
    
    async def _schedule_batch_processing(self, topic_name: str, config: Dict[str, Any]) -> None:
        """Schedule batch processing for a topic"""
        # Cancel existing timer if any
        if topic_name in self.batch_timers and self.batch_timers[topic_name]:
            self.batch_timers[topic_name].cancel()
        
        # Create new timer
        self.batch_timers[topic_name] = asyncio.create_task(
            self._delayed_batch_processing(topic_name, config)
        )
    
    async def _delayed_batch_processing(self, topic_name: str, config: Dict[str, Any]) -> None:
        """Process batch after timeout delay"""
        await asyncio.sleep(self.batch_timeout)
        
        if self.message_batches[topic_name]:
            await self._process_batch(topic_name, config)
    
    async def _process_batch(self, topic_name: str, config: Dict[str, Any]) -> None:
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
    
    async def _process_single_message(self, topic_name: str, item: Dict[str, Any], config: Dict[str, Any]) -> Any:
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
    
    async def _process_email_message(self, data: Dict[str, Any]) -> None:
        """Process an email message for Vespa indexing"""
        logger.info(f"Processing email message: {data.get('id', 'unknown')} for user {data.get('user_id', 'unknown')}")
        
        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)
    
    async def _process_calendar_message(self, data: Dict[str, Any]) -> None:
        """Process a calendar message for Vespa indexing"""
        logger.info(f"Processing calendar message: {data.get('id', 'unknown')} for user {data.get('user_id', 'unknown')}")
        
        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)
    
    async def _process_contact_message(self, data: Dict[str, Any]) -> None:
        """Process a contact message for Vespa indexing"""
        logger.info(f"Processing contact message: {data.get('id', 'unknown')} for user {data.get('user_id', 'unknown')}")
        
        # Call the ingest endpoint to index the document
        await self._call_ingest_endpoint(data)
    
    async def _call_ingest_endpoint(self, data: Dict[str, Any]) -> None:
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
