#!/usr/bin/env python3
"""
PubSub consumer for the office router service
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import json
from datetime import datetime
import time
import os

from google.cloud import pubsub_v1
from google.api_core import retry

from .router import OfficeRouter
from .settings import Settings

logger = logging.getLogger(__name__)

class PubSubConsumer:
    """Consumes messages from PubSub and routes them through the office router"""
    
    def __init__(self, settings: Settings, router: OfficeRouter):
        self.settings = settings
        self.router = router
        self.subscriber: Optional[pubsub_v1.SubscriberClient] = None
        self.subscriptions: Dict[str, Any] = {}
        self.is_running = False
        self.message_count = 0
        self.error_count = 0
        
    async def start(self):
        """Start the PubSub consumer"""
        try:
            # Set up PubSub emulator environment
            os.environ["PUBSUB_EMULATOR_HOST"] = self.settings.pubsub_emulator_host
            
            # Initialize subscriber client
            self.subscriber = pubsub_v1.SubscriberClient()
            
            # Start consuming from email subscription
            await self._start_email_subscription()
            
            # Start consuming from calendar subscription
            await self._start_calendar_subscription()
            
            self.is_running = True
            logger.info("PubSub consumer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start PubSub consumer: {e}")
            raise
    
    async def stop(self):
        """Stop the PubSub consumer"""
        self.is_running = False
        
        # Cancel all subscriptions
        for subscription_name, subscription in self.subscriptions.items():
            try:
                subscription.cancel()
                logger.info(f"Cancelled subscription: {subscription_name}")
            except Exception as e:
                logger.error(f"Error cancelling subscription {subscription_name}: {e}")
        
        # Close subscriber client
        if self.subscriber:
            self.subscriber.close()
            self.subscriber = None
        
        logger.info("PubSub consumer stopped")
    
    async def _start_email_subscription(self):
        """Start consuming from email subscription"""
        subscription_path = self.subscriber.subscription_path(
            self.settings.pubsub_project_id,
            self.settings.pubsub_email_subscription
        )
        
        subscription = self.subscriber.subscribe(
            subscription_path,
            callback=self._email_message_callback,
            flow_control=pubsub_v1.types.FlowControl(
                max_messages=100,
                max_bytes=1024 * 1024,  # 1MB
                allow_exceeded_limits=False
            )
        )
        
        self.subscriptions["email"] = subscription
        logger.info(f"Started email subscription: {subscription_path}")
    
    async def _start_calendar_subscription(self):
        """Start consuming from calendar subscription"""
        subscription_path = self.subscriber.subscription_path(
            self.settings.pubsub_project_id,
            self.settings.pubsub_calendar_subscription
        )
        
        subscription = self.subscriber.subscribe(
            subscription_path,
            callback=self._calendar_message_callback,
            flow_control=pubsub_v1.types.FlowControl(
                max_messages=50,
                max_bytes=512 * 1024,  # 512KB
                allow_exceeded_limits=False
            )
        )
        
        self.subscriptions["calendar"] = subscription
        logger.info(f"Started calendar subscription: {subscription_path}")
    
    def _email_message_callback(self, message):
        """Callback for processing email messages"""
        try:
            self.message_count += 1
            
            # Parse message data
            data = json.loads(message.data.decode("utf-8"))
            logger.info(f"Processing email message {self.message_count}: {data.get('id', 'unknown')}")
            
            # Route email through the router
            asyncio.create_task(self._process_email_message(data))
            
            # Acknowledge the message
            message.ack()
            logger.debug(f"Acknowledged email message {self.message_count}")
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error processing email message {self.message_count}: {e}")
            # Nack the message to retry
            message.nack()
    
    def _calendar_message_callback(self, message):
        """Callback for processing calendar messages"""
        try:
            self.message_count += 1
            
            # Parse message data
            data = json.loads(message.data.decode("utf-8"))
            logger.info(f"Processing calendar message {self.message_count}: {data.get('id', 'unknown')}")
            
            # Route calendar event through the router
            asyncio.create_task(self._process_calendar_message(data))
            
            # Acknowledge the message
            message.ack()
            logger.debug(f"Acknowledged calendar message {self.message_count}")
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error processing calendar message {self.message_count}: {e}")
            # Nack the message to retry
    
    async def _process_email_message(self, data: Dict[str, Any]):
        """Process email message asynchronously"""
        try:
            # Add retry logic for routing
            for attempt in range(self.settings.max_retries):
                try:
                    result = await self.router.route_email(data)
                    logger.info(f"Successfully routed email {data.get('id', 'unknown')} on attempt {attempt + 1}")
                    return result
                except Exception as e:
                    if attempt == self.settings.max_retries - 1:
                        logger.error(f"Failed to route email {data.get('id', 'unknown')} after {self.settings.max_retries} attempts: {e}")
                        raise
                    else:
                        logger.warning(f"Attempt {attempt + 1} failed for email {data.get('id', 'unknown')}: {e}")
                        await asyncio.sleep(self.settings.retry_delay_seconds * (2 ** attempt))  # Exponential backoff
                        
        except Exception as e:
            logger.error(f"Failed to process email message: {e}")
            raise
    
    async def _process_calendar_message(self, data: Dict[str, Any]):
        """Process calendar message asynchronously"""
        try:
            # Add retry logic for routing
            for attempt in range(self.settings.max_retries):
                try:
                    result = await self.router.route_calendar(data)
                    logger.info(f"Successfully routed calendar event {data.get('id', 'unknown')} on attempt {attempt + 1}")
                    return result
                except Exception as e:
                    if attempt == self.settings.max_retries - 1:
                        logger.error(f"Failed to route calendar event {data.get('id', 'unknown')} after {self.settings.max_retries} attempts: {e}")
                        raise
                    else:
                        logger.warning(f"Attempt {attempt + 1} failed for calendar event {data.get('id', 'unknown')}: {e}")
                        await asyncio.sleep(self.settings.retry_delay_seconds * (2 ** attempt))  # Exponential backoff
                        
        except Exception as e:
            logger.error(f"Failed to process calendar message: {e}")
            raise
    
    def get_running_status(self) -> bool:
        """Check if the consumer is running"""
        return self.is_running
    
    def get_subscription_status(self) -> Dict[str, Any]:
        """Get status of all subscriptions"""
        return {
            "email": {
                "active": "email" in self.subscriptions and self.subscriptions["email"] is not None,
                "subscription_path": f"projects/{self.settings.pubsub_project_id}/subscriptions/{self.settings.pubsub_email_subscription}"
            },
            "calendar": {
                "active": "calendar" in self.subscriptions and self.subscriptions["calendar"] is not None,
                "subscription_path": f"projects/{self.settings.pubsub_project_id}/subscriptions/{self.settings.pubsub_calendar_subscription}"
            },
            "stats": {
                "total_messages": self.message_count,
                "total_errors": self.error_count,
                "success_rate": ((self.message_count - self.error_count) / max(self.message_count, 1)) * 100
            }
        }
