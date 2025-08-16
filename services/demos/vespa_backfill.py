#!/usr/bin/env python3
"""
Vespa Backfill Demo - Real Office Data Integration

This demo creates demo data and sends it directly to the Vespa loader service
via HTTP ingest, bypassing the Pub/Sub complexity for now.
"""

import asyncio
import logging
import argparse
import sys
import os
import json
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import httpx

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.common.logging_config import get_logger

logger = get_logger(__name__)

class VespaBackfillDemo:
    """Demo for real office data backfill into Vespa"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Demo configuration
        self.demo_users = config.get("demo_users", ["demo_user_1", "demo_user_2"])
        self.email_count = config.get("email_count", 50)
        self.calendar_count = config.get("calendar_count", 25)
        self.contact_count = config.get("contact_count", 10)
        self.vespa_loader_url = config.get("vespa_loader_url", "http://localhost:9001")
        
    async def run_backfill_demo(self) -> Dict[str, Any]:
        """Run the complete backfill demo"""
        logger.info("Starting Vespa backfill demo with direct HTTP ingest...")
        
        start_time = datetime.now(timezone.utc)
        results = {
            "status": "running",
            "start_time": start_time.isoformat(),
            "users_processed": 0,
            "total_data_ingested": 0,
            "successful_ingests": 0,
            "failed_ingests": 0,
            "ingest_details": []
        }
        
        try:
            # Process each demo user
            for user_id in self.demo_users:
                logger.info(f"Creating demo data for user: {user_id}")
                
                try:
                    # Generate and ingest demo data
                    ingest_result = await self._ingest_user_data(user_id)
                    
                    results["successful_ingests"] += 1
                    results["total_data_ingested"] += ingest_result.get("total_documents", 0)
                    results["ingest_details"].append({
                        "user_id": user_id,
                        "status": "success",
                        "emails_ingested": ingest_result.get("emails_ingested", 0),
                        "calendar_events_ingested": ingest_result.get("calendar_events_ingested", 0),
                        "contacts_ingested": ingest_result.get("contacts_ingested", 0),
                        "total_documents": ingest_result.get("total_documents", 0),
                        "duration_seconds": ingest_result.get("duration_seconds", 0)
                    })
                    
                    logger.info(f"Successfully ingested data for {user_id}: {ingest_result.get('total_documents', 0)} documents")
                    
                except Exception as e:
                    logger.error(f"Failed to ingest data for {user_id}: {e}")
                    results["failed_ingests"] += 1
                    results["ingest_details"].append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": str(e)
                    })
                
                results["users_processed"] += 1
            
            # Wait a bit for data to be processed by Vespa
            logger.info("Waiting for Vespa to process ingested data...")
            await asyncio.sleep(5)
            
            results["status"] = "completed"
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
            
        except Exception as e:
            logger.error(f"Backfill demo failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return results
    
    async def _ingest_user_data(self, user_id: str) -> Dict[str, Any]:
        """Generate and ingest demo data for a specific user"""
        start_time = datetime.now(timezone.utc)
        
        # Generate demo data
        emails = self._generate_demo_emails(user_id, self.email_count)
        calendar_events = self._generate_demo_calendar_events(user_id, self.calendar_count)
        contacts = self._generate_demo_contacts(user_id, self.contact_count)
        
        # Ingest data via HTTP
        async with httpx.AsyncClient() as client:
            total_ingested = 0
            
            # Ingest emails
            emails_ingested = 0
            for email in emails:
                try:
                    response = await client.post(
                        f"{self.vespa_loader_url}/ingest",
                        json=email,
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        emails_ingested += 1
                        total_ingested += 1
                    else:
                        logger.warning(f"Failed to ingest email: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.warning(f"Failed to ingest email: {e}")
            
            # Ingest calendar events
            calendar_ingested = 0
            for event in calendar_events:
                try:
                    response = await client.post(
                        f"{self.vespa_loader_url}/ingest",
                        json=event,
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        calendar_ingested += 1
                        total_ingested += 1
                    else:
                        logger.warning(f"Failed to ingest calendar event: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.warning(f"Failed to ingest calendar event: {e}")
            
            # Ingest contacts
            contacts_ingested = 0
            for contact in contacts:
                try:
                    response = await client.post(
                        f"{self.vespa_loader_url}/ingest",
                        json=contact,
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        contacts_ingested += 1
                        total_ingested += 1
                    else:
                        logger.warning(f"Failed to ingest contact: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.warning(f"Failed to ingest contact: {e}")
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return {
            "user_id": user_id,
            "emails_ingested": emails_ingested,
            "calendar_events_ingested": calendar_ingested,
            "contacts_ingested": contacts_ingested,
            "total_documents": total_ingested,
            "duration_seconds": duration
        }
    
    def _generate_demo_emails(self, user_id: str, count: int) -> List[Dict[str, Any]]:
        """Generate demo email data"""
        emails = []
        
        for i in range(count):
            # Sample subjects and content
            subjects = [
                "Weekly Team Update",
                "Project Status Report", 
                "Meeting Invitation",
                "Client Feedback",
                "Budget Review",
                "Technical Discussion",
                "Product Launch Planning",
                "Quarterly Review"
            ]
            
            email = {
                "id": f"demo_email_{user_id}_{i}_{random.randint(1000, 9999)}",
                "user_id": user_id,
                "type": "email",
                "provider": random.choice(["microsoft", "google"]),
                "subject": random.choice(subjects),
                "sender": f"sender{i}@example.com",
                "recipients": [f"recipient{i}@example.com"],
                "body": f"This is demo email content for testing purposes. Email #{i} contains sample data to test the Vespa ingestion functionality.",
                "thread_id": f"thread_{i}",
                "folder": random.choice(["INBOX", "SENT", "DRAFTS"]),
                "is_read": random.choice([True, False]),
                "is_starred": random.choice([True, False]),
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "demo_data": True,
                    "word_count": random.randint(20, 100),
                    "has_attachments": random.choice([True, False])
                }
            }
            emails.append(email)
        
        return emails
    
    def _generate_demo_calendar_events(self, user_id: str, count: int) -> List[Dict[str, Any]]:
        """Generate demo calendar event data"""
        events = []
        
        for i in range(count):
            # Sample event types
            event_types = [
                "Meeting", "Appointment", "Conference Call", "Team Standup",
                "Client Presentation", "Training Session", "Review Meeting"
            ]
            
            start_time = datetime.now(timezone.utc) + timedelta(
                days=random.randint(1, 30), 
                hours=random.randint(9, 17)
            )
            
            event = {
                "id": f"demo_event_{user_id}_{i}_{random.randint(1000, 9999)}",
                "user_id": user_id,
                "type": "calendar_event",
                "provider": random.choice(["microsoft", "google"]),
                "title": f"{random.choice(event_types)} #{i}",
                "description": f"This is a demo calendar event for testing purposes. Event #{i} contains sample data.",
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(hours=random.randint(1, 3))).isoformat(),
                "location": random.choice(["Conference Room A", "Zoom Meeting", "Office", "Client Site"]),
                "attendees": [f"attendee{i}@example.com"],
                "is_all_day": random.choice([True, False]),
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "demo_data": True,
                    "attendee_count": random.randint(1, 4),
                    "is_recurring": random.choice([True, False])
                }
            }
            events.append(event)
        
        return events
    
    def _generate_demo_contacts(self, user_id: str, count: int) -> List[Dict[str, Any]]:
        """Generate demo contact data"""
        contacts = []
        
        # Sample names and companies
        first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
        companies = ["Tech Corp", "Innovation Inc", "Global Solutions", "Startup Co", "Enterprise Ltd"]
        job_titles = ["Software Engineer", "Product Manager", "Sales Director", "Marketing Manager", "CEO"]
        
        for i in range(count):
            contact = {
                "id": f"demo_contact_{user_id}_{i}_{random.randint(1000, 9999)}",
                "user_id": user_id,
                "type": "contact",
                "provider": random.choice(["microsoft", "google"]),
                "display_name": f"{random.choice(first_names)} {random.choice(last_names)}",
                "email_addresses": [f"{random.choice(first_names).lower()}.{random.choice(last_names).lower()}@{random.choice(companies).lower().replace(' ', '')}.com"],
                "phone_numbers": [f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"],
                "company": random.choice(companies),
                "job_title": random.choice(job_titles),
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "demo_data": True,
                    "email_count": 1,
                    "phone_count": 1,
                    "has_company": True,
                    "has_job_title": True
                }
            }
            contacts.append(contact)
        
        return contacts
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted results"""
        print("\n" + "=" * 60)
        print("VESPA BACKFILL DEMO RESULTS")
        print("=" * 60)
        
        print(f"Status: {results['status']}")
        print(f"Duration: {results.get('duration_seconds', 0):.1f} seconds")
        print(f"Users Processed: {results['users_processed']}")
        print(f"Successful Ingests: {results['successful_ingests']}")
        print(f"Failed Ingests: {results['failed_ingests']}")
        print(f"Total Data Ingested: {results['total_data_ingested']} documents")
        
        if results['status'] == 'failed' and 'error' in results:
            print(f"Error: {results['error']}")
        
        # Print ingest details
        if results['ingest_details']:
            print(f"\nIngest Details:")
            for ingest in results['ingest_details']:
                if ingest['status'] == 'success':
                    print(f"  ✅ {ingest['user_id']}: {ingest['total_documents']} documents "
                          f"({ingest['emails_ingested']} emails, {ingest['calendar_events_ingested']} calendar, "
                          f"{ingest['contacts_ingested']} contacts) in {ingest['duration_seconds']:.1f}s")
                else:
                    print(f"  ❌ {ingest['user_id']}: {ingest.get('error', 'Unknown error')}")
        
        print("=" * 60)

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Vespa Backfill Demo")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--users", type=str, nargs="+", default=["demo_user_1"], 
                       help="Demo user IDs")
    parser.add_argument("--emails", type=int, default=50, 
                       help="Number of emails to ingest per user")
    parser.add_argument("--calendar", type=int, default=25, 
                       help="Number of calendar events to ingest per user")
    parser.add_argument("--contacts", type=int, default=10, 
                       help="Number of contacts to ingest per user")
    parser.add_argument("--vespa-loader-url", default="http://localhost:9001", 
                       help="Vespa loader service URL")
    
    args = parser.parse_args()
    
    # Load config if provided
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            return
    
    # Override config with command line args
    config.update({
        "demo_users": args.users,
        "email_count": args.emails,
        "calendar_count": args.calendar,
        "contact_count": args.contacts,
        "vespa_loader_url": args.vespa_loader_url
    })
    
    # Create and run demo
    demo = VespaBackfillDemo(config)
    results = await demo.run_backfill_demo()
    demo.print_results(results)

if __name__ == "__main__":
    asyncio.run(main())
