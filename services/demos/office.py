#!/usr/bin/env python3
"""
Live Demo for Office Service

This demo shows how to use the Office Service with real API credentials
to fetch emails, calendar events, and files from Google and Microsoft.

Setup:
1. Set environment variables for your API tokens:
   - GOOGLE_ACCESS_TOKEN: Your Google OAuth2 access token
   - MICROSOFT_ACCESS_TOKEN: Your Microsoft Graph access token

2. Run from the repo root:
   cd /path/to/briefly
   python services/demos/office.py

Note: This demo bypasses the user management service and uses tokens directly.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Add the office service to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'office_service'))

from core.clients.google import GoogleAPIClient
from core.clients.microsoft import MicrosoftAPIClient
from core.normalizer import normalize_google_email, normalize_microsoft_email
from schemas import EmailMessage, CalendarEvent, DriveFile


class OfficeDemoService:
    """Simplified Office Service for demonstration purposes."""
    
    def __init__(self, google_token: Optional[str] = None, microsoft_token: Optional[str] = None):
        """Initialize with optional API tokens."""
        self.google_token = google_token
        self.microsoft_token = microsoft_token
        self.user_id = "demo-user"
    
    async def get_emails(self, limit: int = 5) -> Dict[str, List[EmailMessage]]:
        """Fetch emails from all available providers."""
        results = {"google": [], "microsoft": []}
        
        # Fetch from Google
        if self.google_token:
            try:
                google_client = GoogleAPIClient(self.google_token, self.user_id)
                async with google_client:
                    print("📧 Fetching emails from Gmail...")
                    response = await google_client.get_messages(max_results=limit)
                    
                    if "messages" in response:
                        for msg_ref in response["messages"][:limit]:
                            # Get full message details
                            full_msg = await google_client.get_message(msg_ref["id"], format="full")
                            normalized = normalize_google_email(full_msg)
                            results["google"].append(normalized)
                            
                    print(f"✅ Found {len(results['google'])} Gmail messages")
            except Exception as e:
                print(f"❌ Error fetching Gmail: {e}")
        
        # Fetch from Microsoft
        if self.microsoft_token:
            try:
                microsoft_client = MicrosoftAPIClient(self.microsoft_token, self.user_id)
                async with microsoft_client:
                    print("📧 Fetching emails from Outlook...")
                    response = await microsoft_client.get_messages(top=limit)
                    
                    if "value" in response:
                        for msg in response["value"][:limit]:
                            normalized = normalize_microsoft_email(msg)
                            results["microsoft"].append(normalized)
                            
                    print(f"✅ Found {len(results['microsoft'])} Outlook messages")
            except Exception as e:
                print(f"❌ Error fetching Outlook: {e}")
        
        return results
    
    async def get_calendar_events(self, limit: int = 5) -> Dict[str, List[Dict]]:
        """Fetch calendar events from all available providers."""
        results = {"google": [], "microsoft": []}
        
        # Get current time for filtering recent events
        now = datetime.now(timezone.utc).isoformat()
        
        # Fetch from Google Calendar
        if self.google_token:
            try:
                google_client = GoogleAPIClient(self.google_token, self.user_id)
                async with google_client:
                    print("📅 Fetching events from Google Calendar...")
                    response = await google_client.get_events(
                        calendar_id="primary",
                        time_min=now,
                        max_results=limit
                    )
                    
                    if "items" in response:
                        results["google"] = response["items"][:limit]
                        
                    print(f"✅ Found {len(results['google'])} Google Calendar events")
            except Exception as e:
                print(f"❌ Error fetching Google Calendar: {e}")
        
        # Fetch from Microsoft Calendar
        if self.microsoft_token:
            try:
                microsoft_client = MicrosoftAPIClient(self.microsoft_token, self.user_id)
                async with microsoft_client:
                    print("📅 Fetching events from Outlook Calendar...")
                    response = await microsoft_client.get_events(
                        top=limit,
                        filter=f"start/dateTime ge '{now}'"
                    )
                    
                    if "value" in response:
                        results["microsoft"] = response["value"][:limit]
                        
                    print(f"✅ Found {len(results['microsoft'])} Outlook Calendar events")
            except Exception as e:
                print(f"❌ Error fetching Outlook Calendar: {e}")
        
        return results
    
    async def get_files(self, limit: int = 5) -> Dict[str, List[Dict]]:
        """Fetch files from all available providers."""
        results = {"google": [], "microsoft": []}
        
        # Fetch from Google Drive
        if self.google_token:
            try:
                google_client = GoogleAPIClient(self.google_token, self.user_id)
                async with google_client:
                    print("📁 Fetching files from Google Drive...")
                    response = await google_client.get_files(page_size=limit)
                    
                    if "files" in response:
                        results["google"] = response["files"][:limit]
                        
                    print(f"✅ Found {len(results['google'])} Google Drive files")
            except Exception as e:
                print(f"❌ Error fetching Google Drive: {e}")
        
        # Fetch from Microsoft OneDrive
        if self.microsoft_token:
            try:
                microsoft_client = MicrosoftAPIClient(self.microsoft_token, self.user_id)
                async with microsoft_client:
                    print("📁 Fetching files from OneDrive...")
                    response = await microsoft_client.get_drive_items(top=limit)
                    
                    if "value" in response:
                        results["microsoft"] = response["value"][:limit]
                        
                    print(f"✅ Found {len(results['microsoft'])} OneDrive files")
            except Exception as e:
                print(f"❌ Error fetching OneDrive: {e}")
        
        return results


def print_section_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")


def print_email_summary(emails: Dict[str, List[EmailMessage]]):
    """Print a summary of fetched emails."""
    print_section_header("📧 EMAIL SUMMARY")
    
    for provider, messages in emails.items():
        if messages:
            print(f"\n{provider.upper()} ({len(messages)} messages):")
            for i, msg in enumerate(messages, 1):
                # Extract sender email from the from_address field
                sender = msg.from_address.email if msg.from_address else "Unknown"
                print(f"  {i}. From: {sender}")
                print(f"     Subject: {msg.subject}")
                print(f"     Date: {msg.date.strftime('%Y-%m-%d %H:%M')}")
                if msg.snippet:
                    snippet = msg.snippet[:80] + "..." if len(msg.snippet) > 80 else msg.snippet
                    print(f"     Preview: {snippet}")
                print()


def print_calendar_summary(events: Dict[str, List[Dict]]):
    """Print a summary of fetched calendar events."""
    print_section_header("📅 CALENDAR SUMMARY")
    
    for provider, event_list in events.items():
        if event_list:
            print(f"\n{provider.upper()} ({len(event_list)} events):")
            for i, event in enumerate(event_list, 1):
                if provider == "google":
                    title = event.get("summary", "No title")
                    start_time = event.get("start", {}).get("dateTime", "No start time")
                else:  # Microsoft
                    title = event.get("subject", "No title")
                    start_time = event.get("start", {}).get("dateTime", "No start time")
                
                print(f"  {i}. {title}")
                print(f"     Start: {start_time}")
                print()


def print_files_summary(files: Dict[str, List[Dict]]):
    """Print a summary of fetched files."""
    print_section_header("📁 FILES SUMMARY")
    
    for provider, file_list in files.items():
        if file_list:
            print(f"\n{provider.upper()} ({len(file_list)} files):")
            for i, file_item in enumerate(file_list, 1):
                if provider == "google":
                    name = file_item.get("name", "Unnamed file")
                    mime_type = file_item.get("mimeType", "Unknown type")
                    size = file_item.get("size", "Unknown size")
                else:  # Microsoft
                    name = file_item.get("name", "Unnamed file")
                    mime_type = file_item.get("file", {}).get("mimeType", "Unknown type")
                    size = file_item.get("size", "Unknown size")
                
                print(f"  {i}. {name}")
                print(f"     Type: {mime_type}")
                print(f"     Size: {size} bytes" if size != "Unknown size" else f"     Size: {size}")
                print()


async def run_demo():
    """Run the Office Service demo."""
    print("🚀 Office Service Live Demo")
    print("=" * 50)
    
    # Get tokens from environment variables
    google_token = os.getenv("GOOGLE_ACCESS_TOKEN")
    microsoft_token = os.getenv("MICROSOFT_ACCESS_TOKEN")
    
    if not google_token and not microsoft_token:
        print("❌ No API tokens found!")
        print("\nPlease set one or both of these environment variables:")
        print("  - GOOGLE_ACCESS_TOKEN: Your Google OAuth2 access token")
        print("  - MICROSOFT_ACCESS_TOKEN: Your Microsoft Graph access token")
        print("\nExample:")
        print("  export GOOGLE_ACCESS_TOKEN='your-google-token-here'")
        print("  export MICROSOFT_ACCESS_TOKEN='your-microsoft-token-here'")
        print("  python services/demos/office.py")
        return
    
    # Show which providers are available
    providers = []
    if google_token:
        providers.append("Google (Gmail, Calendar, Drive)")
    if microsoft_token:
        providers.append("Microsoft (Outlook, Calendar, OneDrive)")
    
    print(f"🔑 Available providers: {', '.join(providers)}")
    
    # Initialize the demo service
    demo = OfficeDemoService(google_token, microsoft_token)
    
    try:
        # Fetch emails
        print_section_header("FETCHING EMAILS")
        emails = await demo.get_emails(limit=3)
        print_email_summary(emails)
        
        # Fetch calendar events
        print_section_header("FETCHING CALENDAR EVENTS")
        events = await demo.get_calendar_events(limit=3)
        print_calendar_summary(events)
        
        # Fetch files
        print_section_header("FETCHING FILES")
        files = await demo.get_files(limit=3)
        print_files_summary(files)
        
        # Summary
        total_emails = sum(len(msgs) for msgs in emails.values())
        total_events = sum(len(evts) for evts in events.values())
        total_files = sum(len(fls) for fls in files.values())
        
        print_section_header("✅ DEMO COMPLETE")
        print(f"Successfully fetched:")
        print(f"  📧 {total_emails} emails")
        print(f"  📅 {total_events} calendar events")
        print(f"  📁 {total_files} files")
        print(f"\nThe Office Service unified API is working! 🎉")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if we're running from the correct directory
    if not os.path.exists("services/office_service"):
        print("❌ Please run this demo from the repository root:")
        print("   cd /path/to/briefly")
        print("   python services/demos/office.py")
        sys.exit(1)
    
    # Run the demo
    asyncio.run(run_demo()) 