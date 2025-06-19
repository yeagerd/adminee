#!/usr/bin/env python3
"""
Full Briefly Demo - Integrated Chat, Office, and User Services

This demo combines all three services (chat, office, user) to provide a complete
Briefly experience with OAuth authentication and enhanced chat functionality.

Features:
- OAuth authentication via user service
- Full chat interface with multi-agent support
- Draft management (delete, send)
- Integrated office operations (email, calendar, files)
- Graceful fallback when services are unavailable

Commands (interactive mode):
  help                Show this help message
  list                List all chat threads
  new                 Start a new thread
  switch <thread_id>  Switch to an existing thread
  clear               Clear conversation history
  delete              Delete the current draft
  send                Send the current draft via email
  auth                Re-authenticate with services
  status              Show service and integration status
  exit                Exit the demo

Usage:
    python services/demos/full_demo.py                    # API mode (default)
    python services/demos/full_demo.py --local            # Local multi-agent mode
    python services/demos/full_demo.py --streaming        # API streaming demo
    python services/demos/full_demo.py --local --streaming # Local streaming demo
    python services/demos/full_demo.py --no-auth          # Skip authentication
    python services/demos/full_demo.py --message "hi"     # Send single message
"""

import argparse
import asyncio
import logging
import os
import sys
import time
import webbrowser
from typing import Any, Dict, List, Optional

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import httpx
import requests

# Set environment variables to disable cost tracking
os.environ["LITELLM_LOG"] = "WARNING"
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "False")

from services.chat.agents.workflow_agent import WorkflowAgent

# Try to import OAuth utilities
try:
    from demo_jwt_utils import create_bearer_token
    from oauth_callback_handler import OAuthCallbackServer

    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Set specific loggers for visibility
logging.getLogger("services.chat.agents.workflow_agent").setLevel(logging.INFO)
logging.getLogger("services.chat.agents.coordinator_agent").setLevel(logging.INFO)

# Suppress noisy loggers
for logger_name in [
    "aiosqlite",
    "asyncio",
    "httpx",
    "openai._base_client",
    "llama_index",
    "LiteLLM",
    "litellm",
    "litellm.cost_calculator",
    "litellm.utils",
    "litellm.cost_calculation",
    "litellm._logging",
]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


def actor(message):
    """Returns a string indicating the actor of the message."""
    return (
        "briefly"
        if getattr(message, "llm_generated", False)
        else getattr(message, "user_id", "user")
    )


class ServiceClient:
    """Base client for service interactions."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.available = True

    async def health_check(self) -> bool:
        """Check if service is available."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                self.available = response.status_code == 200
                return self.available
        except Exception:
            self.available = False
            return False


class UserServiceClient(ServiceClient):
    """Client for user service operations."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None

    async def start_oauth_flow(self, provider: str) -> Optional[str]:
        """Start OAuth flow for a provider."""
        if not self.auth_token:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/integrations/oauth/{provider}/start",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("authorization_url")
        except Exception as e:
            logger.error(f"OAuth start failed: {e}")
        return None

    async def complete_oauth_flow(self, provider: str, code: str, state: str) -> bool:
        """Complete OAuth flow with authorization code."""
        if not self.auth_token:
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/integrations/oauth/{provider}/callback",
                    json={"code": code, "state": state},
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OAuth completion failed: {e}")
        return False

    async def get_integrations_status(self) -> Dict[str, Any]:
        """Get status of all integrations."""
        if not self.auth_token:
            return {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/integrations/status",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Get integrations status failed: {e}")
        return {}


class ChatServiceClient(ServiceClient):
    """Client for chat service operations."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        super().__init__(base_url)

    def send_message(
        self, user_id: str, message: str, thread_id: Optional[str] = None
    ) -> Optional[str]:
        """Send a message to the chat service."""
        payload = {"user_id": user_id, "message": message}
        if thread_id:
            payload["thread_id"] = thread_id

        try:
            response = requests.post(
                f"{self.base_url}/chat/message", json=payload, timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            logger.error(f"Send message failed: {e}")
        return None

    def delete_draft(self, user_id: str, thread_id: Optional[str] = None) -> bool:
        """Delete the current draft."""
        try:
            payload = {"user_id": user_id}
            if thread_id:
                payload["thread_id"] = thread_id

            response = requests.delete(
                f"{self.base_url}/chat/draft", json=payload, timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Delete draft failed: {e}")
        return False

    def get_threads(self, user_id: str) -> List[Dict]:
        """List all threads for a user."""
        try:
            response = requests.get(
                f"{self.base_url}/chat/threads",
                params={"user_id": user_id},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                return response.json().get("threads", [])
        except Exception as e:
            logger.error(f"Get threads failed: {e}")
        return []


class OfficeServiceClient(ServiceClient):
    """Client for office service operations."""

    def __init__(self, base_url: str = "http://localhost:8002"):
        super().__init__(base_url)

    async def send_email(self, user_id: str, email_data: Dict[str, Any]) -> bool:
        """Send an email through the office service."""
        try:
            payload = {"user_id": user_id, **email_data}
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/email/send", json=payload
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Send email failed: {e}")
        return False


class FullDemo:
    """Comprehensive demo integrating all services."""

    def __init__(
        self,
        use_api: bool = True,
        chat_url: str = "http://localhost:8001",
        office_url: str = "http://localhost:8002",
        user_url: str = "http://localhost:8000",
        user_id: str = "demo_user",
        skip_auth: bool = False,
    ):
        self.use_api = use_api
        self.user_id = user_id
        self.skip_auth = skip_auth
        self.thread_id = int(time.time())
        self.active_thread = None

        # Initialize service clients
        self.chat_client = ChatServiceClient(chat_url)
        self.office_client = OfficeServiceClient(office_url)
        self.user_client = UserServiceClient(user_url)

        # For local mode
        self.agent: Optional[WorkflowAgent] = None

        # OAuth server for authentication
        self.oauth_server: Optional[OAuthCallbackServer] = None

        # Service availability
        self.services_available = {"chat": False, "office": False, "user": False}

    async def check_services(self):
        """Check availability of all services."""
        print("🔍 Checking service availability...")

        # Check services in parallel
        chat_task = self.chat_client.health_check()
        office_task = self.office_client.health_check()
        user_task = self.user_client.health_check()

        results = await asyncio.gather(
            chat_task, office_task, user_task, return_exceptions=True
        )

        self.services_available["chat"] = (
            results[0] if not isinstance(results[0], Exception) else False
        )
        self.services_available["office"] = (
            results[1] if not isinstance(results[1], Exception) else False
        )
        self.services_available["user"] = (
            results[2] if not isinstance(results[2], Exception) else False
        )

        print(f"  Chat Service: {'✅' if self.services_available['chat'] else '❌'}")
        print(
            f"  Office Service: {'✅' if self.services_available['office'] else '❌'}"
        )
        print(f"  User Service: {'✅' if self.services_available['user'] else '❌'}")

    async def authenticate(self) -> bool:
        """Authenticate with user service and set up OAuth."""
        if self.skip_auth or not self.services_available["user"]:
            print("🔐 Skipping authentication (disabled or user service unavailable)")
            return True

        if not OAUTH_AVAILABLE:
            print("⚠️  OAuth utilities not available, skipping authentication")
            return True

        print("\n🔐 Setting up authentication...")

        # Create demo JWT token
        self.user_client.auth_token = create_bearer_token(
            self.user_id, f"{self.user_id}@example.com"
        )
        self.user_client.user_id = self.user_id

        # Start OAuth server
        if not self.oauth_server:
            self.oauth_server = OAuthCallbackServer()
            self.oauth_server.start()

        # Check if we need to set up OAuth integrations
        integrations = await self.user_client.get_integrations_status()

        if not integrations:
            print("🔗 No integrations found. Setting up OAuth flows...")

            # Offer to set up Google OAuth
            if input("Set up Google integration? (y/n): ").lower() == "y":
                await self.setup_oauth_integration("google")

            # Offer to set up Microsoft OAuth
            if input("Set up Microsoft integration? (y/n): ").lower() == "y":
                await self.setup_oauth_integration("microsoft")
        else:
            print("✅ Existing integrations found")
            for provider, status in integrations.items():
                print(f"  {provider}: {'✅' if status.get('connected') else '❌'}")

        return True

    async def setup_oauth_integration(self, provider: str) -> bool:
        """Set up OAuth integration for a provider."""
        print(f"\n🔗 Setting up {provider} integration...")

        # Start OAuth flow
        auth_url = await self.user_client.start_oauth_flow(provider)
        if not auth_url:
            print(f"❌ Failed to start {provider} OAuth flow")
            return False

        print(f"🌐 Opening {provider} authorization URL...")
        print(f"URL: {auth_url}")

        # Open browser
        webbrowser.open(auth_url)

        # Wait for callback
        print("⏳ Waiting for OAuth callback...")
        callback_data = self.oauth_server.wait_for_callback(timeout=300)

        if not callback_data or callback_data.get("error"):
            print(
                f"❌ OAuth flow failed: {callback_data.get('error') if callback_data else 'Timeout'}"
            )
            return False

        # Complete OAuth flow
        code = callback_data.get("code")
        state = callback_data.get("state")

        if not code:
            print("❌ No authorization code received")
            return False

        success = await self.user_client.complete_oauth_flow(provider, code, state)

        if success:
            print(f"✅ {provider} integration completed successfully")
        else:
            print(f"❌ Failed to complete {provider} integration")

        return success

    async def create_agent(self) -> Optional[WorkflowAgent]:
        """Create multi-agent workflow (local mode only)."""
        if self.use_api:
            return None

        print("\n🤖 Creating Multi-Agent WorkflowAgent...")

        agent = WorkflowAgent(
            thread_id=self.thread_id,
            user_id=self.user_id,
            llm_model="gpt-4o-mini",
            llm_provider="openai",
            max_tokens=2000,
        )

        await agent.build_agent("Hello, I'm ready to help!")

        print(
            f"✅ Multi-Agent system ready with {len(agent.specialized_agents)} specialized agents"
        )
        return agent

    def show_welcome(self):
        """Show welcome message."""
        print("=" * 80)
        print("🚀 Welcome to the Full Briefly Demo!")
        print("=" * 80)

        mode = "API" if self.use_api else "Local Multi-Agent"
        print(f"🔧 Mode: {mode}")
        print(f"👤 User: {self.user_id}")

        # Show service status
        print("\n📊 Service Status:")
        for service, available in self.services_available.items():
            status = "✅ Available" if available else "❌ Unavailable"
            print(f"  {service.title()}: {status}")

        print("\n💡 Enhanced Commands:")
        print("  • Type any message to chat")
        print("  • 'delete' - Delete current draft")
        print("  • 'send' - Send current draft via email")
        print("  • 'status' - Show service status")
        print("  • 'auth' - Re-authenticate")
        print("  • 'help' - Show all commands")
        print("  • 'exit' - Exit demo")

        if self.use_api:
            print("  • 'list' - List chat threads")
            print("  • 'new' - Start new thread")
            print("  • 'switch <id>' - Switch thread")

        print()

    def show_help(self):
        """Show detailed help."""
        print("\n" + "=" * 60)
        print("📋 Full Briefly Demo - Help")
        print("=" * 60)

        print("\n🗣️  Chat Commands:")
        print("  • Type any message to chat with Briefly")
        print("  • 'clear' - Clear conversation history")

        if self.use_api:
            print("  • 'list' - List all chat threads")
            print("  • 'new' - Start a new thread")
            print("  • 'switch <thread_id>' - Switch to existing thread")

        print("\n📝 Draft Management:")
        print("  • 'delete' - Delete the current draft")
        print("  • 'send' - Send current draft via email")

        print("\n🔧 System Commands:")
        print("  • 'status' - Show service and integration status")
        print("  • 'auth' - Re-authenticate with services")
        print("  • 'help' - Show this help message")
        print("  • 'exit' or 'quit' - Exit the demo")

        print("\n💡 Example Usage:")
        print("  • 'Draft an email to the team about the meeting'")
        print("  • send (to send the drafted email)")
        print("  • 'What meetings do I have today?'")
        print("  • 'Show me my recent emails'")

    async def send_message_local(self, message: str) -> str:
        """Send message using local multi-agent."""
        if not self.agent:
            self.agent = await self.create_agent()

        if not self.agent:
            return "❌ Failed to create agent"

        try:
            response = await self.agent.process_message(message)
            return response.response if hasattr(response, "response") else str(response)
        except Exception as e:
            logger.error(f"Local message error: {e}")
            return f"❌ Error: {str(e)}"

    def _render_drafts_as_text(self, drafts):
        """Render structured draft data as text for the demo."""
        if not drafts:
            return ""

        lines = ["📋 **Drafts Created:**"]

        for draft in drafts:
            draft_type = draft.get("type", "unknown")

            if draft_type == "email":
                lines.append("• Email Draft:")
                # Display all non-empty email fields
                for field, label in [
                    ("to", "To"),
                    ("cc", "CC"),
                    ("bcc", "BCC"),
                    ("subject", "Subject"),
                    ("body", "Body"),
                ]:
                    value = draft.get(field)
                    if value:
                        if field == "body":
                            # Truncate body for readability
                            body_preview = (
                                value[:100] + "..." if len(value) > 100 else value
                            )
                            lines.append(f"  {label}: {body_preview}")
                        else:
                            lines.append(f"  {label}: {value}")

            elif draft_type == "calendar_event":
                lines.append("• Calendar Event Draft:")
                # Display all non-empty calendar event fields
                for field, label in [
                    ("title", "Title"),
                    ("start_time", "Start"),
                    ("end_time", "End"),
                    ("attendees", "Attendees"),
                    ("location", "Location"),
                    ("description", "Description"),
                ]:
                    value = draft.get(field)
                    if value:
                        if field == "description":
                            # Truncate description for readability
                            desc_preview = (
                                value[:100] + "..." if len(value) > 100 else value
                            )
                            lines.append(f"  {label}: {desc_preview}")
                        else:
                            lines.append(f"  {label}: {value}")

            elif draft_type == "calendar_change":
                lines.append("• Calendar Change Draft:")
                # Display all non-empty calendar change fields
                for field, label in [
                    ("event_id", "Event ID"),
                    ("change_type", "Change Type"),
                    ("new_title", "New Title"),
                    ("new_start_time", "New Start"),
                    ("new_end_time", "New End"),
                    ("new_attendees", "New Attendees"),
                    ("new_location", "New Location"),
                    ("new_description", "New Description"),
                ]:
                    value = draft.get(field)
                    if value:
                        if field == "new_description":
                            # Truncate description for readability
                            desc_preview = (
                                value[:100] + "..." if len(value) > 100 else value
                            )
                            lines.append(f"  {label}: {desc_preview}")
                        else:
                            lines.append(f"  {label}: {value}")

            else:
                lines.append(f"• {draft_type.replace('_', ' ').title()}: Created")

        return "\n".join(lines)

    def send_message_api(self, message: str) -> str:
        """Send message using chat service API."""
        if not self.services_available["chat"]:
            return "❌ Chat service unavailable"

        response = self.chat_client.send_message(
            self.user_id, message, self.active_thread
        )
        return response or "❌ Failed to get response"

    async def send_message(self, message: str) -> str:
        """Send message using appropriate method."""
        if self.use_api:
            return self.send_message_api(message)
        else:
            return await self.send_message_local(message)

    async def handle_delete_command(self) -> str:
        """Handle draft deletion."""
        if not self.services_available["chat"]:
            return "❌ Chat service unavailable for draft deletion"

        success = self.chat_client.delete_draft(self.user_id, self.active_thread)
        return "✅ Draft deleted" if success else "❌ Failed to delete draft"

    async def handle_send_command(self) -> str:
        """Handle draft sending via email."""
        if not self.services_available["office"]:
            return "❌ Office service unavailable for sending email"

        # For now, this is a placeholder - in a real implementation,
        # you'd retrieve the current draft and send it
        email_data = {
            "to": [f"{self.user_id}@example.com"],
            "subject": "Draft from Briefly",
            "body": "This is a draft email sent from Briefly demo.",
        }

        success = await self.office_client.send_email(self.user_id, email_data)
        return "✅ Draft sent via email" if success else "❌ Failed to send draft"

    async def handle_status_command(self) -> str:
        """Show system status."""
        status = "📊 System Status:\n"

        # Service status
        for service, available in self.services_available.items():
            icon = "✅" if available else "❌"
            status += f"  {service.title()} Service: {icon}\n"

        # Integration status (if user service available)
        if self.services_available["user"]:
            integrations = await self.user_client.get_integrations_status()
            if integrations:
                status += "\n🔗 Integrations:\n"
                for provider, info in integrations.items():
                    icon = "✅" if info.get("connected") else "❌"
                    status += f"  {provider.title()}: {icon}\n"

        return status.rstrip()

    async def handle_auth_command(self) -> str:
        """Handle re-authentication."""
        if not self.services_available["user"]:
            return "❌ User service unavailable for authentication"

        success = await self.authenticate()
        return "✅ Authentication completed" if success else "❌ Authentication failed"

    def handle_api_commands(self, command: str) -> tuple[bool, str]:
        """Handle API-specific commands."""
        if not self.use_api:
            return False, ""

        parts = command.strip().split()
        cmd = parts[0].lower()

        if cmd == "list":
            threads = self.chat_client.get_threads(self.user_id)
            if threads:
                result = "📋 Your threads:\n"
                for thread in threads:
                    result += (
                        f"  • {thread.get('id')}: {thread.get('title', 'Untitled')}\n"
                    )
                return True, result.rstrip()
            else:
                return True, "📋 No threads found"

        elif cmd == "new":
            self.active_thread = None
            return True, "✅ Started new thread"

        elif cmd == "switch" and len(parts) > 1:
            thread_id = parts[1]
            if not self.services_available["chat"]:
                return True, "❌ Chat service unavailable for thread switching"

            try:
                # Get thread history
                response = requests.get(
                    f"{self.chat_client.base_url}/threads/{thread_id}/history",
                    timeout=self.chat_client.timeout,
                )
                if response.status_code == 200:
                    self.active_thread = thread_id
                    data = response.json()
                    messages = data.get("messages", [])

                    result = f"✅ Switched to thread {thread_id}.\n"
                    if not messages:
                        result += "No messages in this thread."
                    else:
                        result += "Conversation history:\n"
                        for m in messages:
                            uid = (
                                actor(m)
                                if hasattr(m, "__dict__")
                                else m.get("user_id", "user")
                            )
                            content = getattr(m, "content", None) or m.get(
                                "content", ""
                            )
                            result += f"  {uid}: {content}\n"

                    return True, result.rstrip()
                else:
                    return (
                        True,
                        f"❌ Failed to switch to thread {thread_id}: {response.status_code}",
                    )
            except Exception as e:
                return True, f"❌ Error switching thread: {str(e)}"

        return False, ""

    async def chat_loop(self):
        """Main interactive chat loop."""
        if not self.use_api:
            self.agent = await self.create_agent()

        while True:
            try:
                # Show prompt
                thread_info = (
                    f" (thread: {self.active_thread})" if self.active_thread else ""
                )
                prompt = f"💬 {self.user_id}{thread_info}: "
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # Handle exit commands
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Thanks for using Briefly! Goodbye!")
                    break

                # Handle special commands
                if user_input.lower() == "help":
                    self.show_help()
                    continue

                elif user_input.lower() == "clear":
                    if not self.use_api and self.agent:
                        # Clear agent history
                        await self.agent.clear_history()
                    print("💬 History cleared")
                    continue

                elif user_input.lower() == "delete":
                    response = await self.handle_delete_command()
                    print(f"📝 {response}")
                    continue

                elif user_input.lower() == "send":
                    response = await self.handle_send_command()
                    print(f"📧 {response}")
                    continue

                elif user_input.lower() == "status":
                    response = await self.handle_status_command()
                    print(response)
                    continue

                elif user_input.lower() == "auth":
                    response = await self.handle_auth_command()
                    print(f"🔐 {response}")
                    continue

                # Handle API-specific commands
                if self.use_api:
                    handled, response = self.handle_api_commands(user_input)
                    if handled:
                        print(response)
                        continue

                # Process chat message
                print("🤖 Briefly:", end=" ", flush=True)

                try:
                    response = await self.send_message(user_input)
                    print(response)
                except Exception as e:
                    print(f"❌ Error: {str(e)}")
                    logger.error(f"Chat error: {e}")

                print()  # Blank line for readability

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ An error occurred: {str(e)}")
                logger.error(f"Demo error: {e}")
                print("Type 'exit' to quit or continue chatting.\n")

    async def run_streaming_demo(self):
        """Demo streaming chat (supports both local and API modes)."""
        # Check service availability first
        await self.check_services()

        mode_text = "API" if self.use_api else "Local Multi-Agent"
        print(f"\n🌊 {mode_text} Streaming Demo")
        print("This shows how the system generates responses in real-time.\n")

        # Create agent for local mode
        if not self.use_api:
            self.agent = await self.create_agent()

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input or user_input.lower() in ["quit", "exit"]:
                    break

                print("🤖 Briefly: ", end="", flush=True)

                if self.use_api:
                    # Stream via API using Server-Sent Events
                    await self._stream_api_response(user_input)
                else:
                    # Stream via direct multi-agent workflow
                    if self.agent:
                        async for chunk in self.agent.stream_chat(user_input):
                            if hasattr(chunk, "delta") and chunk.delta:
                                print(chunk.delta, end="", flush=True)

                print("\n")  # New line after streaming

            except KeyboardInterrupt:
                print("\n\n👋 Streaming demo interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Streaming error: {str(e)}")
                break

    async def _stream_api_response(self, message: str):
        """Stream response from the chat service API using Server-Sent Events."""
        if not self.services_available["chat"]:
            print("❌ Chat service unavailable for streaming")
            return

        payload = {"user_id": self.user_id, "message": message}
        if self.active_thread:
            payload["thread_id"] = self.active_thread

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.chat_client.base_url}/chat/stream",
                    json=payload,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    if response.status_code != 200:
                        print(f"Error: HTTP {response.status_code}")
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                import json

                                data = json.loads(line[6:])  # Remove "data: " prefix

                                if "delta" in data:
                                    print(data["delta"], end="", flush=True)
                                elif "thread_id" in data:
                                    self.active_thread = data["thread_id"]

                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"Streaming error: {e}")

    async def cleanup(self):
        """Clean up resources."""
        if self.oauth_server:
            self.oauth_server.stop()


async def main():
    """Run the full demo."""
    parser = argparse.ArgumentParser(
        description="Full Briefly Demo - Integrated Chat, Office, and User Services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python services/demos/full_demo.py                    # API mode (default)
  python services/demos/full_demo.py --local            # Local multi-agent mode
  python services/demos/full_demo.py --streaming        # API streaming demo
  python services/demos/full_demo.py --local --streaming # Local streaming demo
  python services/demos/full_demo.py --no-auth          # Skip authentication
  python services/demos/full_demo.py --message "hi"     # Send single message
        """,
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local multi-agent mode instead of API mode (default: API mode)",
    )

    parser.add_argument(
        "--chat-url",
        type=str,
        default="http://localhost:8001",
        help="Chat service URL (default: http://localhost:8001)",
    )

    parser.add_argument(
        "--office-url",
        type=str,
        default="http://localhost:8002",
        help="Office service URL (default: http://localhost:8002)",
    )

    parser.add_argument(
        "--user-url",
        type=str,
        default="http://localhost:8000",
        help="User service URL (default: http://localhost:8000)",
    )

    parser.add_argument(
        "--user-id",
        type=str,
        default="demo_user",
        help="User ID (default: demo_user)",
    )

    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Skip authentication setup",
    )

    parser.add_argument(
        "--message",
        "-m",
        type=str,
        help="Send a single message (non-interactive mode)",
    )

    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Run streaming demo instead of regular chat (supports both local and API modes)",
    )

    args = parser.parse_args()

    # Create demo instance
    demo = FullDemo(
        use_api=not args.local,  # API is default, --local switches to local mode
        chat_url=args.chat_url,
        office_url=args.office_url,
        user_url=args.user_url,
        user_id=args.user_id,
        skip_auth=args.no_auth,
    )

    try:
        # Check service availability
        await demo.check_services()

        # Set up authentication
        await demo.authenticate()

        # Show welcome
        demo.show_welcome()

        if args.message:
            # Single message mode
            response = await demo.send_message(args.message)
            print(f"🤖 Briefly: {response}")
        elif args.streaming:
            # Streaming demo mode
            await demo.run_streaming_demo()
        else:
            # Interactive mode
            await demo.chat_loop()

    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
