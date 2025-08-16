#!/usr/bin/env python3
"""
Demo data seeding script for backfill functionality testing
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
import string

from services.common.pubsub_client import PubSubClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DemoDataSeeder:
    """Seeds demo data for testing backfill functionality"""
    
    def __init__(self, project_id: str = "briefly-dev", emulator_host: str = "localhost:8085"):
        self.pubsub_client = PubSubClient(project_id, emulator_host)
        self.email_topic = "email-backfill"
        self.calendar_topic = "calendar-updates"
        self.contact_topic = "contact-updates"
        
    async def seed_demo_emails(self, user_id: str, count: int = 100) -> List[str]:
        """Seed demo email data"""
        logger.info(f"Seeding {count} demo emails for user {user_id}")
        
        emails = []
        message_ids = []
        
        # Generate demo emails
        for i in range(count):
            email = self._generate_demo_email(user_id, i)
            emails.append(email)
            
            try:
                # Publish to pubsub
                message_id = await self.pubsub_client.publish_email_data(email, self.email_topic)
                message_ids.append(message_id)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Published {i + 1}/{count} demo emails")
                    
            except RuntimeError as e:
                # Fatal error (e.g., topic not found) - halt the process
                logger.error(f"Fatal error publishing demo email {i}: {e}")
                logger.error("Halting demo email seeding due to fatal Pub/Sub error")
                break
            except Exception as e:
                logger.error(f"Failed to publish demo email {i}: {e}")
        
        logger.info(f"Successfully seeded {len(message_ids)} demo emails")
        return message_ids
    
    async def seed_demo_calendar_events(self, user_id: str, count: int = 50) -> List[str]:
        """Seed demo calendar event data"""
        logger.info(f"Seeding {count} demo calendar events for user {user_id}")
        
        events = []
        message_ids = []
        
        # Generate demo calendar events
        for i in range(count):
            event = self._generate_demo_calendar_event(user_id, i)
            events.append(event)
            
            try:
                # Publish to pubsub
                message_id = await self.pubsub_client.publish_calendar_data(event, self.calendar_topic)
                message_ids.append(message_id)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Published {i + 1}/{count} demo calendar events")
                    
            except RuntimeError as e:
                # Fatal error (e.g., topic not found) - halt the process
                logger.error(f"Fatal error publishing demo calendar event {i}: {e}")
                logger.error("Halting demo calendar seeding due to fatal Pub/Sub error")
                break
            except Exception as e:
                logger.error(f"Failed to publish demo calendar event {i}: {e}")
        
        logger.info(f"Successfully seeded {len(message_ids)} demo calendar events")
        return message_ids
    
    async def seed_demo_contacts(self, user_id: str, count: int = 25) -> List[str]:
        """Seed demo contact data"""
        logger.info(f"Seeding {count} demo contacts for user {user_id}")
        
        contacts = []
        message_ids = []
        
        # Generate demo contacts
        for i in range(count):
            contact = self._generate_demo_contact(user_id, i)
            contacts.append(contact)
            
            try:
                # Publish to pubsub
                message_id = await self.pubsub_client.publish_contact_data(contact, self.contact_topic)
                message_ids.append(message_id)
                
                if (i + 1) % 5 == 0:
                    logger.info(f"Published {i + 1}/{count} demo contacts")
                    
            except RuntimeError as e:
                # Fatal error (e.g., topic not found) - halt the process
                logger.error(f"Fatal error publishing demo contact {i}: {e}")
                logger.error("Halting demo contact seeding due to fatal Pub/Sub error")
                break
            except Exception as e:
                logger.error(f"Failed to publish demo contact {i}: {e}")
        
        logger.info(f"Successfully seeded {len(message_ids)} demo contacts")
        return message_ids
    
    async def seed_all_demo_data(self, user_id: str, email_count: int = 100, 
                                calendar_count: int = 50, contact_count: int = 25) -> Dict[str, Any]:
        """Seed all types of demo data"""
        logger.info(f"Starting comprehensive demo data seeding for user {user_id}")
        
        start_time = datetime.utcnow()
        
        # Seed emails
        email_message_ids = await self.seed_demo_emails(user_id, email_count)
        
        # Seed calendar events
        calendar_message_ids = await self.seed_demo_calendar_events(user_id, calendar_count)
        
        # Seed contacts
        contact_message_ids = await self.seed_demo_contacts(user_id, contact_count)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        summary = {
            "user_id": user_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "emails_seeded": len(email_message_ids),
            "calendar_events_seeded": len(calendar_message_ids),
            "contacts_seeded": len(contact_message_ids),
            "total_messages": len(email_message_ids) + len(calendar_message_ids) + len(contact_message_ids),
            "email_message_ids": email_message_ids[:10],  # First 10 for reference
            "calendar_message_ids": calendar_message_ids[:10],
            "contact_message_ids": contact_message_ids[:10]
        }
        
        logger.info(f"Demo data seeding completed in {duration:.2f} seconds")
        logger.info(f"Summary: {summary['total_messages']} total messages published")
        
        return summary
    
    def _generate_demo_email(self, user_id: str, index: int) -> Dict[str, Any]:
        """Generate a demo email"""
        # Sample email subjects and content
        subjects = [
            "Weekly Team Meeting",
            "Project Update - Q4 Goals",
            "Client Presentation Feedback",
            "Budget Review Meeting",
            "New Product Launch",
            "Customer Support Tickets",
            "Sales Pipeline Update",
            "Marketing Campaign Results",
            "Technical Architecture Review",
            "HR Policy Updates"
        ]
        
        senders = [
            "alice@company.com",
            "bob@company.com",
            "charlie@company.com",
            "diana@company.com",
            "eve@company.com"
        ]
        
        recipients = [
            "team@company.com",
            "managers@company.com",
            "developers@company.com",
            "sales@company.com"
        ]
        
        folders = ["inbox", "sent", "drafts", "archive"]
        
        # Generate email data
        email = {
            "id": f"demo_email_{user_id}_{index}_{random.randint(1000, 9999)}",
            "user_id": user_id,
            "provider": random.choice(["microsoft", "google"]),
            "type": "email",
            "subject": random.choice(subjects),
            "body": f"This is demo email content for testing purposes. Email #{index} contains sample data to test the backfill functionality.",
            "from": random.choice(senders),
            "to": [random.choice(recipients)],
            "cc": [],
            "bcc": [],
            "thread_id": f"thread_{index // 5}",  # Group emails into threads
            "folder": random.choice(folders),
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            "attachments": [],
            "metadata": {
                "has_attachments": False,
                "is_read": random.choice([True, False]),
                "importance": random.choice(["low", "normal", "high"]),
                "demo_data": True
            }
        }
        
        return email
    
    def _generate_demo_calendar_event(self, user_id: str, index: int) -> Dict[str, Any]:
        """Generate a demo calendar event"""
        # Sample event types
        event_types = [
            "Team Meeting",
            "Client Call",
            "Project Review",
            "Training Session",
            "All Hands",
            "1:1 Meeting",
            "Product Demo",
            "Strategy Session"
        ]
        
        attendees = [
            "alice@company.com",
            "bob@company.com",
            "charlie@company.com",
            "diana@company.com"
        ]
        
        locations = [
            "Conference Room A",
            "Conference Room B",
            "Zoom Meeting",
            "Office Kitchen",
            "Remote"
        ]
        
        # Generate event data
        start_time = datetime.utcnow() + timedelta(days=random.randint(1, 30), hours=random.randint(9, 17))
        end_time = start_time + timedelta(hours=random.randint(1, 3))
        
        event = {
            "id": f"demo_calendar_{user_id}_{index}_{random.randint(1000, 9999)}",
            "user_id": user_id,
            "provider": random.choice(["microsoft", "google"]),
            "type": "calendar",
            "subject": random.choice(event_types),
            "body": f"This is a demo calendar event for testing purposes. Event #{index} contains sample data.",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "attendees": random.sample(attendees, random.randint(1, 3)),
            "location": random.choice(locations),
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            "metadata": {
                "is_all_day": False,
                "is_recurring": random.choice([True, False]),
                "attendee_count": random.randint(1, 4),
                "demo_data": True
            }
        }
        
        return event
    
    def _generate_demo_contact(self, user_id: str, index: int) -> Dict[str, Any]:
        """Generate a demo contact"""
        # Sample names and companies
        first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
        companies = ["Tech Corp", "Innovation Inc", "Global Solutions", "Startup Co", "Enterprise Ltd"]
        job_titles = ["Software Engineer", "Product Manager", "Sales Director", "Marketing Manager", "CEO"]
        
        # Generate contact data
        contact = {
            "id": f"demo_contact_{user_id}_{index}_{random.randint(1000, 9999)}",
            "user_id": user_id,
            "provider": random.choice(["microsoft", "google"]),
            "type": "contact",
            "display_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "email_addresses": [f"{random.choice(first_names).lower()}.{random.choice(last_names).lower()}@{random.choice(companies).lower().replace(' ', '')}.com"],
            "phone_numbers": [f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"],
            "company": random.choice(companies),
            "job_title": random.choice(job_titles),
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            "metadata": {
                "email_count": 1,
                "phone_count": 1,
                "has_company": True,
                "has_job_title": True,
                "demo_data": True
            }
        }
        
        return contact
    
    async def close(self):
        """Close the pubsub client"""
        await self.pubsub_client.close()

async def main():
    """Main function for demo data seeding"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed demo data for backfill testing")
    parser.add_argument("--user-id", required=True, help="User ID for demo data")
    parser.add_argument("--emails", type=int, default=100, help="Number of demo emails to seed")
    parser.add_argument("--calendar", type=int, default=50, help="Number of demo calendar events to seed")
    parser.add_argument("--contacts", type=int, default=25, help="Number of demo contacts to seed")
    parser.add_argument("--project-id", default="briefly-dev", help="PubSub project ID")
    parser.add_argument("--emulator-host", default="localhost:8085", help="PubSub emulator host")
    
    args = parser.parse_args()
    
    # Create seeder
    seeder = DemoDataSeeder(args.project_id, args.emulator_host)
    
    try:
        # Seed demo data
        summary = await seeder.seed_all_demo_data(
            args.user_id,
            args.emails,
            args.calendar,
            args.contacts
        )
        
        # Print summary
        print("\n" + "="*50)
        print("DEMO DATA SEEDING SUMMARY")
        print("="*50)
        print(f"User ID: {summary['user_id']}")
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"Emails: {summary['emails_seeded']}")
        print(f"Calendar Events: {summary['calendar_events_seeded']}")
        print(f"Contacts: {summary['contacts_seeded']}")
        print(f"Total Messages: {summary['total_messages']}")
        print("="*50)
        
        # Save summary to file
        output_file = f"demo_data_summary_{args.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\nSummary saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Demo data seeding failed: {e}")
        raise
    finally:
        await seeder.close()

if __name__ == "__main__":
    asyncio.run(main())
