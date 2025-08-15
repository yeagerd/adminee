#!/usr/bin/env python3
"""
PubSub publisher for publishing crawled emails to the message queue
"""

import logging
from typing import Dict, Any, Optional
import json
from datetime import datetime

from services.common.pubsub_client import PubSubClient

logger = logging.getLogger(__name__)

class PubSubPublisher:
    """Publishes email data to PubSub topics"""
    
    def __init__(self, project_id: Optional[str] = None, emulator_host: Optional[str] = None):
        self.pubsub_client = PubSubClient(project_id, emulator_host)
        self.email_topic = "email-backfill"
        self.calendar_topic = "calendar-updates"
        self.contact_topic = "contact-updates"
        
    async def publish_email(self, email_data: Dict[str, Any]) -> str:
        """Publish email data to the email topic"""
        try:
            # Ensure email data has required fields
            if not email_data.get("id") or not email_data.get("user_id"):
                raise ValueError("Email data missing required fields: id, user_id")
            
            # Add timestamp if not present
            if "timestamp" not in email_data:
                email_data["timestamp"] = datetime.utcnow().isoformat()
            
            # Publish to email topic
            message_id = await self.pubsub_client.publish_email_data(email_data, self.email_topic)
            
            logger.debug(f"Published email {email_data.get('id')} to topic {self.email_topic}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish email {email_data.get('id', 'unknown')}: {e}")
            raise
    
    async def publish_calendar_event(self, calendar_data: Dict[str, Any]) -> str:
        """Publish calendar event data to the calendar topic"""
        try:
            # Ensure calendar data has required fields
            if not calendar_data.get("id") or not calendar_data.get("user_id"):
                raise ValueError("Calendar data missing required fields: id, user_id")
            
            # Add timestamp if not present
            if "timestamp" not in calendar_data:
                calendar_data["timestamp"] = datetime.utcnow().isoformat()
            
            # Publish to calendar topic
            message_id = await self.pubsub_client.publish_calendar_data(calendar_data, self.calendar_topic)
            
            logger.debug(f"Published calendar event {calendar_data.get('id')} to topic {self.calendar_topic}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish calendar event {calendar_data.get('id', 'unknown')}: {e}")
            raise
    
    async def publish_contact(self, contact_data: Dict[str, Any]) -> str:
        """Publish contact data to the contact topic"""
        try:
            # Ensure contact data has required fields
            if not contact_data.get("id") or not contact_data.get("user_id"):
                raise ValueError("Contact data missing required fields: id, user_id")
            
            # Add timestamp if not present
            if "timestamp" not in contact_data:
                contact_data["timestamp"] = datetime.utcnow().isoformat()
            
            # Publish to contact topic
            message_id = await self.pubsub_client.publish_contact_data(contact_data, self.contact_topic)
            
            logger.debug(f"Published contact {contact_data.get('id')} to topic {self.contact_topic}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish contact {contact_data.get('id', 'unknown')}: {e}")
            raise
    
    async def publish_batch_emails(self, emails: list[Dict[str, Any]]) -> list[str]:
        """Publish multiple emails in batch"""
        try:
            message_ids = []
            
            for email in emails:
                try:
                    message_id = await self.publish_email(email)
                    message_ids.append(message_id)
                except Exception as e:
                    logger.error(f"Failed to publish email in batch: {e}")
                    # Continue with other emails
                    continue
            
            logger.info(f"Published {len(message_ids)} out of {len(emails)} emails to topic {self.email_topic}")
            return message_ids
            
        except Exception as e:
            logger.error(f"Failed to publish batch emails: {e}")
            raise
    
    async def publish_batch_calendar_events(self, events: list[Dict[str, Any]]) -> list[str]:
        """Publish multiple calendar events in batch"""
        try:
            message_ids = []
            
            for event in events:
                try:
                    message_id = await self.publish_calendar_event(event)
                    message_ids.append(message_id)
                except Exception as e:
                    logger.error(f"Failed to publish calendar event in batch: {e}")
                    # Continue with other events
                    continue
            
            logger.info(f"Published {len(message_ids)} out of {len(events)} calendar events to topic {self.calendar_topic}")
            return message_ids
            
        except Exception as e:
            logger.error(f"Failed to publish batch calendar events: {e}")
            raise
    
    async def publish_batch_contacts(self, contacts: list[Dict[str, Any]]) -> list[str]:
        """Publish multiple contacts in batch"""
        try:
            message_ids = []
            
            for contact in contacts:
                try:
                    message_id = await self.publish_contact(contact)
                    message_ids.append(message_id)
                except Exception as e:
                    logger.error(f"Failed to publish contact in batch: {e}")
                    # Continue with other contacts
                    continue
            
            logger.info(f"Published {len(message_ids)} out of {len(contacts)} contacts to topic {self.contact_topic}")
            return message_ids
            
        except Exception as e:
            logger.error(f"Failed to publish batch contacts: {e}")
            raise
    
    def set_topics(self, email_topic: str = None, calendar_topic: str = None, contact_topic: str = None):
        """Set custom topic names"""
        if email_topic:
            self.email_topic = email_topic
        if calendar_topic:
            self.calendar_topic = calendar_topic
        if contact_topic:
            self.contact_topic = contact_topic
        
        logger.info(f"Set topics: email={self.email_topic}, calendar={self.calendar_topic}, contact={self.contact_topic}")
    
    async def close(self):
        """Close the pubsub client"""
        await self.pubsub_client.close()
        logger.info("PubSub publisher closed")
