#!/usr/bin/env python3
"""
Full Office Service Integration Demo

This demo demonstrates the complete Office Service by making HTTP requests
to a running Office Service instance. It shows the full request/response cycle
including unified API responses from multiple providers.

Prerequisites:
1. Office Service must be running (cd services/office_service && uvicorn app.main:app --port 8000 --host 0.0.0.0)
2. Set demo tokens in environment variables
3. Set DEMO_MODE=true in the Office Service environment

Setup:
1. Start the Office Service in demo mode:
   cd services/office_service
       DEMO_MODE=true DEMO_GOOGLE_TOKEN=your-token DEMO_MICROSOFT_TOKEN=your-token uvicorn app.main:app --port 8000 --host 0.0.0.0

2. Run this demo:
   python services/demos/office_full.py user@example.com

This demonstrates the Office Service as it would be used in production,
with HTTP API calls and unified response formats.
"""

import argparse
import asyncio
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


class OfficeServiceClient:
    """Client for making requests to the Office Service HTTP API."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        """Initialize the Office Service client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def health_check(self) -> Dict[str, Any]:
        """Check if the Office Service is healthy."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def health_check_integrations(self, user_id: str) -> Dict[str, Any]:
        """Check health of provider integrations for a user."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/health/integrations/{user_id}"
            )
            response.raise_for_status()
            return response.json()

    async def get_emails(
        self, user_id: str, limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        """Get unified email messages from all providers."""
        params = {"user_id": user_id, "limit": limit, "offset": offset}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/email/messages", params=params
            )
            response.raise_for_status()
            return response.json()

    async def get_email_by_id(self, message_id: str, user_id: str) -> Dict[str, Any]:
        """Get a specific email message by ID."""
        params = {"user_id": user_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/email/messages/{message_id}", params=params
            )
            response.raise_for_status()
            return response.json()

    async def send_email(
        self, user_id: str, email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send an email through the unified API."""
        payload = {"user_id": user_id, **email_data}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/email/send", json=payload)
            response.raise_for_status()
            return response.json()

    async def get_calendar_events(
        self,
        user_id: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get unified calendar events from all providers."""
        params = {"user_id": user_id, "limit": limit}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/calendar/events", params=params
            )
            response.raise_for_status()
            return response.json()

    async def create_calendar_event(
        self, user_id: str, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a calendar event through the unified API."""
        payload = {"user_id": user_id, **event_data}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/calendar/events", json=payload
            )
            response.raise_for_status()
            return response.json()

    async def get_files(
        self, user_id: str, limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        """Get unified files from all providers."""
        params = {"user_id": user_id, "limit": limit, "offset": offset}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/files/", params=params)
            response.raise_for_status()
            return response.json()

    async def search_files(self, user_id: str, query: str) -> Dict[str, Any]:
        """Search for files across all providers."""
        params = {"user_id": user_id, "q": query}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/files/search", params=params)
            response.raise_for_status()
            return response.json()


class FullOfficeDemo:
    """Comprehensive Office Service demonstration using HTTP API."""

    def __init__(self, email: str, service_url: str = "http://localhost:8000"):
        """Initialize the demo."""
        self.email = email
        self.client = OfficeServiceClient(service_url)
        self.errors: List[str] = []

    async def run_demo(self):
        """Run the complete Office Service demo."""
        print("🚀 Office Service Full Integration Demo")
        print("=" * 60)
        print(f"👤 User: {self.email}")
        print(f"🌐 Service URL: {self.client.base_url}")

        try:
            # 1. Health Check
            await self._check_service_health()

            # 2. Provider Integration Health
            await self._check_provider_health()

            # 3. Email Operations
            await self._demo_email_operations()

            # 4. Calendar Operations
            await self._demo_calendar_operations()

            # 5. File Operations
            await self._demo_file_operations()

            # 6. Summary
            await self._show_summary()

        except Exception as e:
            self.errors.append(f"Demo failed: {e}")
            print(f"❌ Demo failed with error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    async def _check_service_health(self):
        """Check if the Office Service is running and healthy."""
        print("\n" + "=" * 50)
        print(" 🏥 HEALTH CHECK")
        print("=" * 50)

        try:
            health = await self.client.health_check()
            print("✅ Office Service is healthy")
            print(f"   Status: {health.get('status', 'unknown')}")
            print(f"   Database: {health.get('database', 'unknown')}")
            print(f"   Redis: {health.get('redis', 'unknown')}")
        except Exception as e:
            self.errors.append(f"Health check failed: {e}")
            print(f"❌ Health check failed: {e}")
            raise

    async def _check_provider_health(self):
        """Check provider integration health."""
        print("\n" + "=" * 50)
        print(" 🔌 PROVIDER INTEGRATION HEALTH")
        print("=" * 50)

        try:
            integrations = await self.client.health_check_integrations(self.email)
            print(f"✅ Provider integrations checked for {self.email}")

            providers = integrations.get("data", {}).get("providers", {})
            for provider, status in providers.items():
                icon = "✅" if status.get("healthy", False) else "❌"
                print(
                    f"   {icon} {provider.title()}: {status.get('status', 'unknown')}"
                )

        except Exception as e:
            self.errors.append(f"Provider health check failed: {e}")
            print(f"❌ Provider health check failed: {e}")

    async def _demo_email_operations(self):
        """Demonstrate email operations."""
        print("\n" + "=" * 50)
        print(" 📧 EMAIL OPERATIONS")
        print("=" * 50)

        try:
            # Get emails
            print("📥 Fetching emails...")
            emails_response = await self.client.get_emails(self.email, limit=5)
            emails_data = emails_response.get("data", {})

            total_emails = 0
            for provider, provider_data in emails_data.items():
                messages = provider_data.get("messages", [])
                total_emails += len(messages)
                print(f"   {provider.title()}: {len(messages)} messages")

                # Show sample messages
                for i, msg in enumerate(messages[:2], 1):
                    subject = msg.get("subject", "No subject")[:50]
                    sender = ""
                    from_addr = msg.get("from_address")
                    if from_addr:
                        sender = from_addr.get("email", "Unknown")
                    print(f"     {i}. From: {sender} | Subject: {subject}")

            print(f"✅ Total emails fetched: {total_emails}")

            # Try to get a specific email if we have one
            if total_emails > 0:
                # Get the first message ID from any provider
                for provider_data in emails_data.values():
                    messages = provider_data.get("messages", [])
                    if messages:
                        message_id = messages[0].get("id")
                        if message_id:
                            print(f"📄 Fetching specific email: {message_id}")
                            email_detail = await self.client.get_email_by_id(
                                message_id, self.email
                            )
                            msg_data = email_detail.get("data", {})
                            subject = msg_data.get("subject", "No subject")
                            print(f"   ✅ Retrieved: {subject}")
                            break

        except Exception as e:
            self.errors.append(f"Email operations failed: {e}")
            print(f"❌ Email operations failed: {e}")

    async def _demo_calendar_operations(self):
        """Demonstrate calendar operations."""
        print("\n" + "=" * 50)
        print(" 📅 CALENDAR OPERATIONS")
        print("=" * 50)

        try:
            # Get calendar events
            print("📆 Fetching calendar events...")
            now = datetime.now().isoformat()
            events_response = await self.client.get_calendar_events(
                self.email, limit=5, start_date=now
            )
            events_data = events_response.get("data", {})

            total_events = 0
            for provider, provider_data in events_data.items():
                events = provider_data.get("events", [])
                total_events += len(events)
                print(f"   {provider.title()}: {len(events)} events")

                # Show sample events
                for i, event in enumerate(events[:2], 1):
                    title = event.get("title", "No title")[:50]
                    start_time = event.get("start_time", "Unknown time")
                    print(f"     {i}. {title} | Start: {start_time}")

            print(f"✅ Total events fetched: {total_events}")

        except Exception as e:
            self.errors.append(f"Calendar operations failed: {e}")
            print(f"❌ Calendar operations failed: {e}")

    async def _demo_file_operations(self):
        """Demonstrate file operations."""
        print("\n" + "=" * 50)
        print(" 📁 FILE OPERATIONS")
        print("=" * 50)

        try:
            # Get files
            print("📂 Fetching files...")
            files_response = await self.client.get_files(self.email, limit=5)
            files_data = files_response.get("data", {})

            total_files = 0
            for provider, provider_data in files_data.items():
                files = provider_data.get("files", [])
                total_files += len(files)
                print(f"   {provider.title()}: {len(files)} files")

                # Show sample files
                for i, file_item in enumerate(files[:2], 1):
                    name = file_item.get("name", "Unknown file")[:40]
                    size = file_item.get("size", "Unknown size")
                    print(f"     {i}. {name} | Size: {size}")

            print(f"✅ Total files fetched: {total_files}")

            # Try a search
            print("🔍 Searching for files containing 'document'...")
            search_response = await self.client.search_files(self.email, "document")
            search_data = search_response.get("data", {})

            search_total = 0
            for provider, provider_data in search_data.items():
                search_files = provider_data.get("files", [])
                search_total += len(search_files)

            print(f"✅ Search results: {search_total} files found")

        except Exception as e:
            self.errors.append(f"File operations failed: {e}")
            print(f"❌ File operations failed: {e}")

    async def _show_summary(self):
        """Show final demo summary."""
        print("\n" + "=" * 50)
        print(" 🎯 DEMO SUMMARY")
        print("=" * 50)

        if self.errors:
            print("❌ Demo completed with errors:")
            for error in self.errors:
                print(f"   • {error}")
            print(
                "\n💡 Note: Some errors are expected if you don't have valid API tokens"
            )
            sys.exit(1)
        else:
            print("✅ All operations completed successfully!")
            print("🎉 The Office Service unified API is working perfectly!")
            print("\n🔥 This demonstrates the power of the unified Office Service API:")
            print("   • Single HTTP endpoint for multiple providers")
            print("   • Standardized response formats")
            print("   • Automatic token management")
            print("   • Error handling and logging")
            print("   • Caching and rate limiting")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Full Office Service integration demo with HTTP API calls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequisites:
1. Start Office Service in demo mode:
   cd services/office_service
       DEMO_MODE=true DEMO_GOOGLE_TOKEN=your-token uvicorn app.main:app --port 8000 --host 0.0.0.0

2. Run this demo:
   python services/demos/office_full.py user@example.com

Environment Variables for Office Service:
  DEMO_MODE=true               Enable demo mode (bypasses user service)
  DEMO_GOOGLE_TOKEN           Your Google OAuth2 access token
  DEMO_MICROSOFT_TOKEN        Your Microsoft Graph access token
        """,
    )

    parser.add_argument(
        "email", help="Email address to use for the demo (used as user identifier)"
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Office Service URL (default: http://localhost:8000)",
    )

    return parser.parse_args()


async def main():
    """Main demo function."""
    args = parse_arguments()

    print("🚀 Starting Office Service Full Integration Demo")
    print(f"📧 User: {args.email}")
    print(f"🌐 Service URL: {args.url}")
    print(
        "\n💡 Make sure the Office Service is running in demo mode before continuing!"
    )

    # Create and run demo
    demo = FullOfficeDemo(args.email, args.url)
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
