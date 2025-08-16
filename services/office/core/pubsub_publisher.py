#!/usr/bin/env python3
"""
Pub/Sub publisher for backfill data
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import os

try:
    from google.cloud import pubsub_v1
    from google.api_core import exceptions as google_exceptions
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    logging.warning("Google Cloud Pub/Sub not available. Install with: pip install google-cloud-pubsub")

logger = logging.getLogger(__name__)

class PubSubPublisher:
    """Publishes data to Google Cloud Pub/Sub for backfill operations"""
    
    def __init__(self, project_id: str = "briefly-dev", emulator_host: str = "localhost:8085"):
        self.project_id = project_id
        self.emulator_host = emulator_host
        self.publisher = None
        # Fix topic names to match actual Pub/Sub setup
        self.topics = {
            "emails": "email-backfill",  # Short name
            "calendar": "calendar-updates",  # Short name
            "contacts": "contact-updates"  # Short name
        }
        
        if PUBSUB_AVAILABLE:
            self._initialize_publisher()
    
    def _initialize_publisher(self):
        """Initialize the Pub/Sub publisher client"""
        try:
            # Use emulator if specified
            if self.emulator_host:
                os.environ["PUBSUB_EMULATOR_HOST"] = self.emulator_host
                logger.info(f"Using Pub/Sub emulator at {self.emulator_host}")
            
            self.publisher = pubsub_v1.PublisherClient()
            logger.info("Pub/Sub publisher initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub publisher: {e}")
            self.publisher = None
    
    def _sanitize_data_for_json(self, data: Any) -> Any:
        """Sanitize data to ensure it's JSON serializable"""
        if isinstance(data, dict):
            return {k: self._sanitize_data_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data_for_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, 'isoformat'):  # Handle other datetime-like objects
            return data.isoformat()
        else:
            return data

    async def publish_email(self, email_data: Dict[str, Any]) -> bool:
        """Publish a single email to Pub/Sub"""
        if not self.publisher:
            logger.warning("Pub/Sub publisher not available")
            return False
        
        try:
            # Sanitize data to ensure JSON serialization
            sanitized_data = self._sanitize_data_for_json(email_data.copy())
            
            # Add timestamp and message ID
            sanitized_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            sanitized_data["message_id"] = str(uuid.uuid4())
            
            # Convert to JSON
            message_data = json.dumps(sanitized_data).encode("utf-8")
            
            # Publish to emails topic
            future = self.publisher.publish(f"projects/{self.project_id}/topics/{self.topics['emails']}", message_data)
            message_id = future.result()
            
            logger.debug(f"Published email {sanitized_data.get('id')} to Pub/Sub: {message_id}")
            return True
            
        except google_exceptions.NotFound as e:
            # Topic not found - this is a fatal error that should halt the process
            logger.error(f"FATAL: Pub/Sub topic '{self.topics['emails']}' not found. Halting email publishing. Error: {e}")
            # Set publisher to None to prevent further attempts
            self.publisher = None
            raise RuntimeError(f"Pub/Sub topic '{self.topics['emails']}' not found. Please create the topic first.") from e
        except Exception as e:
            logger.error(f"Failed to publish email to Pub/Sub: {e}")
            return False
    
    async def publish_calendar_event(self, calendar_data: Dict[str, Any]) -> bool:
        """Publish a single calendar event to Pub/Sub"""
        if not self.publisher:
            logger.warning("Pub/Sub publisher not available")
            return False
        
        try:
            # Sanitize data to ensure JSON serialization
            sanitized_data = self._sanitize_data_for_json(calendar_data.copy())
            
            # Add timestamp and message ID
            sanitized_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            sanitized_data["message_id"] = str(uuid.uuid4())
            
            # Convert to JSON
            message_data = json.dumps(sanitized_data).encode("utf-8")
            
            # Publish to calendar topic
            future = self.publisher.publish(f"projects/{self.project_id}/topics/{self.topics['calendar']}", message_data)
            message_id = future.result()
            
            logger.debug(f"Published calendar event {sanitized_data.get('id')} to Pub/Sub: {message_id}")
            return True
            
        except google_exceptions.NotFound as e:
            # Topic not found - this is a fatal error that should halt the process
            logger.error(f"FATAL: Pub/Sub topic '{self.topics['calendar']}' not found. Halting calendar publishing. Error: {e}")
            # Set publisher to None to prevent further attempts
            self.publisher = None
            raise RuntimeError(f"Pub/Sub topic '{self.topics['calendar']}' not found. Please create the topic first.") from e
        except Exception as e:
            logger.error(f"Failed to publish calendar event to Pub/Sub: {e}")
            return False
    
    async def publish_contact(self, contact_data: Dict[str, Any]) -> bool:
        """Publish a single contact to Pub/Sub"""
        if not self.publisher:
            logger.warning("Pub/Sub publisher not available")
            return False
        
        try:
            # Sanitize data to ensure JSON serialization
            sanitized_data = self._sanitize_data_for_json(contact_data.copy())
            
            # Add timestamp and message ID
            sanitized_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            sanitized_data["message_id"] = str(uuid.uuid4())
            
            # Convert to JSON
            message_data = json.dumps(sanitized_data).encode("utf-8")
            
            # Publish to contacts topic
            future = self.publisher.publish(f"projects/{self.project_id}/topics/{self.topics['contacts']}", message_data)
            message_id = future.result()
            
            logger.debug(f"Published contact {sanitized_data.get('id')} to Pub/Sub: {message_id}")
            return True
            
        except google_exceptions.NotFound as e:
            # Topic not found - this is a fatal error that should halt the process
            logger.error(f"FATAL: Pub/Sub topic '{self.topics['contacts']}' not found. Halting contact publishing. Error: {e}")
            # Set publisher to None to prevent further attempts
            self.publisher = None
            raise RuntimeError(f"Pub/Sub topic '{self.topics['contacts']}' not found. Please create the topic first.") from e
        except Exception as e:
            logger.error(f"Failed to publish contact to Pub/Sub: {e}")
            return False
    
    async def publish_batch_emails(self, emails: list[Dict[str, Any]]) -> list[bool]:
        """Publish multiple emails in batch"""
        try:
            results = []
            
            for email in emails:
                try:
                    success = await self.publish_email(email)
                    results.append(success)
                except RuntimeError as e:
                    # Fatal error (e.g., topic not found) - halt the batch
                    logger.error(f"Fatal error in batch email publishing: {e}")
                    # Return partial results and re-raise the fatal error
                    return results
                except Exception as e:
                    logger.error(f"Failed to publish email in batch: {e}")
                    # Continue with other emails
                    results.append(False)
                    continue
            
            success_count = sum(results)
            logger.info(f"Published {success_count} out of {len(emails)} emails to topic {self.topics['emails']}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to publish batch emails: {e}")
            raise
    
    async def publish_batch_calendar_events(self, events: list[Dict[str, Any]]) -> list[bool]:
        """Publish multiple calendar events in batch"""
        try:
            results = []
            
            for event in events:
                try:
                    success = await self.publish_calendar_event(event)
                    results.append(success)
                except RuntimeError as e:
                    # Fatal error (e.g., topic not found) - halt the batch
                    logger.error(f"Fatal error in batch calendar publishing: {e}")
                    # Return partial results and re-raise the fatal error
                    return results
                except Exception as e:
                    logger.error(f"Failed to publish calendar event in batch: {e}")
                    # Continue with other events
                    results.append(False)
                    continue
            
            success_count = sum(results)
            logger.info(f"Published {success_count} out of {len(events)} calendar events to topic {self.topics['calendar']}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to publish batch calendar events: {e}")
            raise
    
    async def publish_batch_contacts(self, contacts: list[Dict[str, Any]]) -> list[bool]:
        """Publish multiple contacts in batch"""
        try:
            results = []
            
            for contact in contacts:
                try:
                    success = await self.publish_contact(contact)
                    results.append(success)
                except RuntimeError as e:
                    # Fatal error (e.g., topic not found) - halt the batch
                    logger.error(f"Fatal error in batch contact publishing: {e}")
                    # Return partial results and re-raise the fatal error
                    return results
                except Exception as e:
                    logger.error(f"Failed to publish contact in batch: {e}")
                    # Continue with other contacts
                    results.append(False)
                    continue
            
            success_count = sum(results)
            logger.info(f"Published {len(results)} out of {len(contacts)} contacts to topic {self.topics['contacts']}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to publish batch contacts: {e}")
            raise
    
    def set_topics(self, email_topic: str = None, calendar_topic: str = None, contact_topic: str = None):
        """Set custom topic names"""
        if email_topic:
            self.topics["emails"] = email_topic
        if calendar_topic:
            self.topics["calendar"] = calendar_topic
        if contact_topic:
            self.topics["contacts"] = contact_topic
        
        logger.info(f"Set topics: email={self.topics['emails']}, calendar={self.topics['calendar']}, contact={self.topics['contacts']}")
    
    async def close(self):
        """Close the pubsub client"""
        await self.pubsub_client.close()
        logger.info("PubSub publisher closed")
