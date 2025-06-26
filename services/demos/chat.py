#!/usr/bin/env python3
"""
Enhanced Briefly Demo with NextAuth Testing.

This demo provides a comprehensive testing environment for the Briefly platform,
including authentication testing with both Clerk and NextAuth, OAuth integration,
and multi-agent workflow capabilities.

Features:
- Clerk authentication with JWT tokens
- NextAuth integration testing
- OAuth flow simulation (Google, Microsoft)
- Multi-agent workflow testing
- Service health monitoring
- User preference management
- Timezone handling
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import httpx
import requests
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

from services.chat.agents.workflow_agent import WorkflowAgent

# Try to import OAuth utilities
try:
    from demo_jwt_utils import create_bearer_token
    from oauth_callback_handler import OAuthCallbackServer

    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False

# Try to import NextAuth utilities
try:
    from services.demos.nextauth_demo_utils import (
        NextAuthClient,
        compare_auth_approaches,
        create_nextauth_jwt_for_demo,
        demonstrate_nextauth_integration,
        test_nextauth_flow,
    )

    NEXTAUTH_AVAILABLE = True
except ImportError:
    NEXTAUTH_AVAILABLE = False


class DemoSettings(BaseSettings):
    """Demo settings loaded from environment variables."""

    model_config = ConfigDict(extra="ignore")
    API_FRONTEND_USER_KEY: str = "test-FRONTEND_USER_KEY"
    API_FRONTEND_OFFICE_KEY: str = "test-FRONTEND_OFFICE_KEY"
    API_FRONTEND_CHAT_KEY: str = "test-FRONTEND_CHAT_KEY"
    API_CHAT_USER_KEY: str = "test-CHAT_USER_KEY"
    API_CHAT_OFFICE_KEY: str = "test-OFFICE_USER_KEY"
    API_OFFICE_USER_KEY: str = "test-OFFICE_USER_KEY"


# Load settings
settings = DemoSettings()

# Set default user ID
DEFAULT_USER_ID = "trybriefly@outlook.com"

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
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True
            ) as client:
                response = await client.get(f"{self.base_url}/health")
                self.available = response.status_code == 200
                return self.available
        except Exception:
            self.available = False
            return False


class UserServiceClient(ServiceClient):
    """Client for user service operations."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        super().__init__(base_url)
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None

    async def start_oauth_flow(self, provider: str) -> Optional[str]:
        """Start OAuth flow for a provider."""
        if not self.auth_token:
            return None

        try:
            # Use provider-specific default scopes
            if provider == "microsoft":
                scopes = [
                    "openid",
                    "email",
                    "profile",
                    "offline_access",
                    "https://graph.microsoft.com/User.Read",
                    "https://graph.microsoft.com/Calendars.ReadWrite",
                ]
            elif provider == "google":
                scopes = ["read", "write"]
            else:
                scopes = ["read"]

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/users/{self.user_id}/integrations/oauth/start",
                    json={"provider": provider, "scopes": scopes},
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
                    f"{self.base_url}/users/{self.user_id}/integrations/oauth/callback?provider={provider}",
                    json={"code": code, "state": state},
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OAuth completion failed: {e}")
        return False

    async def get_integrations_status(self) -> Dict[str, Any]:
        """Get status of all integrations."""
        if not self.auth_token or not self.user_id:
            raise Exception("No authentication token or user ID provided")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try the public endpoint first (requires Bearer token)
                response = await client.get(
                    f"{self.base_url}/users/{self.user_id}/integrations",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )

                if response.status_code == 401:
                    raise Exception("Authentication failed: Invalid token")

                if response.status_code == 404:
                    raise Exception("User not found")

                if response.status_code == 200:
                    return response.json()

                # Fallback to internal endpoint
                response = await client.get(
                    f"{self.base_url}/internal/users/{self.user_id}/integrations",
                    headers={"X-API-Key": settings.API_FRONTEND_USER_KEY},
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise Exception("User not found")

                raise Exception(f"Failed to get integrations: {response.status_code}")

        except httpx.TimeoutException:
            raise Exception("Service timeout - user service is unresponsive")
        except httpx.ConnectError:
            raise Exception("Service connection error - user service is down")
        except Exception as e:
            # Re-raise the exception with more context
            if "User not found" in str(e):
                raise
            elif "Authentication failed" in str(e):
                raise
            elif "Service timeout" in str(e):
                raise
            elif "Service connection error" in str(e):
                raise
            else:
                raise Exception(f"Unexpected error getting integrations: {str(e)}")

    async def check_user_exists_internal(self, user_id: str) -> bool:
        """Return True if user exists, False if not. Raise if service is down."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/internal/users/{user_id}/integrations",
                    headers={"X-API-Key": settings.API_FRONTEND_USER_KEY},
                )
                if response.status_code == 200:
                    return True
                elif response.status_code == 404:
                    return False
                else:
                    raise RuntimeError(f"User service error: {response.status_code}")
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"User service connection error: {e}")
            raise RuntimeError("User service is down or unreachable")
        except Exception as e:
            logger.warning(f"Unexpected error checking if user {user_id} exists: {e}")
            raise RuntimeError(f"Unexpected error: {e}")

    async def get_user_preferences(self) -> Optional[Dict[str, Any]]:
        """Get user preferences."""
        if not self.auth_token or not self.user_id:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/users/{self.user_id}/preferences/",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # User preferences don't exist yet, return defaults
                    return {
                        "version": "1.0",
                        "ui_preferences": {},
                        "notification_preferences": {},
                        "ai_preferences": {},
                        "integration_preferences": {},
                        "privacy_preferences": {},
                    }
                else:
                    logger.warning(f"Failed to get preferences: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return None

    async def update_user_preferences(self, preferences_update: Dict[str, Any]) -> bool:
        """Update user preferences."""
        if not self.auth_token or not self.user_id:
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/users/{self.user_id}/preferences/",
                    json=preferences_update,
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return False


class ChatServiceClient(ServiceClient):
    """Client for chat service operations."""

    def __init__(self, base_url: str = "http://localhost:8002"):
        super().__init__(base_url)

    def send_message(
        self, user_id: str, message: str, thread_id: Optional[str] = None
    ) -> Optional[str]:
        """Send a message to the chat service."""
        try:
            response = requests.post(
                f"{self.base_url}/chat/message",
                json={
                    "user_id": user_id,
                    "message": message,
                    "thread_id": thread_id,
                },
                headers={"X-API-Key": settings.API_FRONTEND_CHAT_KEY},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                return response.json().get("response")
        except Exception as e:
            logger.error(f"Chat service error: {e}")
        return None

    def delete_draft(self, user_id: str, thread_id: Optional[str] = None) -> bool:
        """Delete the current draft."""
        try:
            response = requests.delete(
                f"{self.base_url}/chat/draft",
                json={"user_id": user_id, "thread_id": thread_id},
                headers={"X-API-Key": settings.API_FRONTEND_CHAT_KEY},
                timeout=self.timeout,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Delete draft error: {e}")
            return False

    def get_threads(self, user_id: str) -> List[Dict]:
        """Get all chat threads for a user."""
        try:
            response = requests.get(
                f"{self.base_url}/chat/threads",
                params={"user_id": user_id},
                headers={"X-API-Key": settings.API_FRONTEND_CHAT_KEY},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                return response.json().get("threads", [])
        except Exception as e:
            logger.error(f"Get threads error: {e}")
        return []


class OfficeServiceClient(ServiceClient):
    """Client for office service operations."""

    def __init__(self, base_url: str = "http://localhost:8003"):
        super().__init__(base_url)

    async def send_email(self, user_id: str, email_data: Dict[str, Any]) -> bool:
        """Send an email via the office service."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/email/send",
                    json={"user_id": user_id, **email_data},
                    headers={"X-API-Key": settings.API_FRONTEND_OFFICE_KEY},
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Send email error: {e}")
            return False


class FullDemo:
    """Full demo with integrated services and NextAuth testing capabilities."""

    def __init__(
        self,
        use_api: bool,
        chat_url: str,
        office_url: str,
        user_url: str,
        user_id: str,
        skip_auth: bool = False,
    ):
        self.use_api = use_api
        self.user_id = user_id
        self.skip_auth = skip_auth
        self.user_timezone = "UTC"
        self.timeout = 30.0  # Default timeout for HTTP requests

        # Service clients
        self.chat_client = ChatServiceClient(chat_url)
        self.office_client = OfficeServiceClient(office_url)
        self.user_client = UserServiceClient(user_url)

        # Service availability
        self.services_available = {
            "chat": False,
            "office": False,
            "user": False,
        }

        # Authentication tracking
        self.auth_token: Optional[str] = None
        self.authenticated = False

        # Chat state
        self.current_thread_id: Optional[str] = None
        self.agent: Optional[WorkflowAgent] = None

        # NextAuth client
        self.nextauth_client: Optional[NextAuthClient] = None
        self.nextauth_token: Optional[str] = None

        # Track available authentication methods
        self.auth_methods = {
            "clerk": True,  # Always available in base demo
            "nextauth": NEXTAUTH_AVAILABLE,
        }

    async def check_services(self):
        """Check availability of all services including NextAuth server."""
        print("🔍 Checking service availability...")

        # Check main services
        self.services_available["chat"] = await self.chat_client.health_check()
        self.services_available["office"] = await self.office_client.health_check()
        self.services_available["user"] = await self.user_client.health_check()

        # Check NextAuth test server
        if NEXTAUTH_AVAILABLE:
            print("🔍 Checking NextAuth test server...")
            self.nextauth_client = NextAuthClient()
            nextauth_available = await self.nextauth_client.health_check()
            self.auth_methods["nextauth"] = nextauth_available

            if nextauth_available:
                print("  NextAuth Test Server: ✅")
            else:
                print("  NextAuth Test Server: ❌")
                print("    Start with: python services/demos/nextauth_test_server.py")

        # Show status
        for service, available in self.services_available.items():
            status = "✅ Available" if available else "❌ Unavailable"
            print(f"  {service.title()}: {status}")

    async def authenticate(self, email: Optional[str] = None) -> bool:
        """Authenticate with the user service."""
        if self.skip_auth:
            print("⏭️  Skipping authentication (--no-auth flag)")
            self.authenticated = True
            return True

        if not self.services_available["user"]:
            print("❌ User service not available")
            return False

        # Use provided email or default
        auth_email = email or self.user_id

        try:
            # Generate a Clerk-style user ID from the email
            user_id = f"user_{auth_email.replace('@', '_').replace('.', '_')}"

            # Create user if it doesn't exist (before creating the token)
            if not await self._create_user_if_not_exists(auth_email, user_id):
                print(f"❌ Failed to create user {auth_email}")
                return False

            # Now create a demo JWT token with the user ID and email
            self.auth_token = create_bearer_token(user_id, auth_email)
            self.user_client.auth_token = self.auth_token
            self.user_client.user_id = user_id

            # Verify the token works by trying to get integrations
            try:
                await self.user_client.get_integrations_status()
            except Exception as e:
                logger.warning(
                    f"Could not verify integrations, but user was created: {e}"
                )

            self.authenticated = True
            print(f"✅ Authenticated as {auth_email} (ID: {user_id})")
            return True

        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            self.authenticated = False
            return False

    async def _create_user_if_not_exists(self, email: str, user_id: str) -> bool:
        """Create a user if they don't exist."""
        try:
            user_exists = await self.user_client.check_user_exists_internal(user_id)
        except Exception as e:
            logger.error(
                f"User service is down, cannot determine if user {user_id} exists: {e}"
            )
            return False

        if user_exists:
            logger.info(f"User {user_id} already exists")
            return True
        else:
            logger.info(f"User {user_id} not found, creating via webhook")
            # Create user via webhook simulation
            webhook_payload = {
                "type": "user.created",
                "object": "event",
                "data": {
                    "id": user_id,
                    "email_addresses": [
                        {
                            "email_address": email,
                            "verification": {"status": "verified"},
                        }
                    ],
                    "first_name": "Demo",
                    "last_name": "User",
                    "image_url": "https://images.clerk.dev/demo-avatar.png",
                    "created_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                },
            }
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.user_client.base_url}/webhooks/clerk",
                        json=webhook_payload,
                        headers={
                            "Content-Type": "application/json",
                            "svix-id": "msg_demo_12345",
                            "svix-timestamp": str(int(time.time())),
                            "svix-signature": "v1,demo_signature",
                        },
                    )
                    if response.status_code in [200, 201]:
                        logger.info(f"Successfully created user {user_id} via webhook")
                        return True
                    else:
                        logger.error(
                            f"Failed to create user via webhook: {response.status_code}"
                        )
                        return False
            except Exception as webhook_error:
                logger.error(f"Webhook creation failed: {webhook_error}")
                return False

    async def setup_oauth_integration(self, provider: str) -> bool:
        """Set up OAuth integration for a provider."""
        if not self.authenticated:
            print("❌ Not authenticated")
            return False

        if not OAUTH_AVAILABLE:
            print("❌ OAuth utilities not available")
            return False

        try:
            # Start OAuth flow
            auth_url = await self.user_client.start_oauth_flow(provider)
            if not auth_url:
                print(f"❌ Failed to start {provider} OAuth flow")
                return False

            print(f"🔗 Starting {provider} OAuth flow...")
            print(f"   URL: {auth_url}")

            # Start callback server
            callback_server = OAuthCallbackServer()
            await callback_server.start()

            try:
                # Wait for callback
                code, state = await callback_server.wait_for_callback()
                print(f"✅ Received OAuth callback: code={code[:10]}..., state={state}")

                # Complete OAuth flow
                success = await self.user_client.complete_oauth_flow(
                    provider, code, state
                )
                if success:
                    print(f"✅ {provider.title()} OAuth integration successful!")
                    return True
                else:
                    print(f"❌ {provider.title()} OAuth integration failed")
                    return False

            finally:
                await callback_server.stop()

        except Exception as e:
            print(f"❌ OAuth setup failed: {e}")
            return False

    async def create_agent(self) -> Optional[WorkflowAgent]:
        """Create a workflow agent for local mode."""
        if not self.use_api:
            try:
                agent = WorkflowAgent()
                await agent.initialize()
                return agent
            except Exception as e:
                logger.error(f"Failed to create agent: {e}")
        return None

    async def load_user_timezone(self):
        """Load user timezone from preferences."""
        if not self.authenticated:
            return

        try:
            preferences = await self.user_client.get_user_preferences()
            if preferences:
                ui_prefs = preferences.get("ui_preferences", {})
                self.user_timezone = ui_prefs.get("timezone", "UTC")
                logger.info(f"Loaded user timezone: {self.user_timezone}")
        except Exception as e:
            logger.warning(f"Failed to load user timezone: {e}")

    def show_welcome(self):
        """Show welcome message with NextAuth information."""
        print("=" * 80)
        print("🚀 Welcome to the Enhanced Briefly Demo with NextAuth Testing!")
        print("=" * 80)

        mode = "API" if self.use_api else "Local Multi-Agent"
        print(f"🔧 Mode: {mode}")
        print(f"👤 User: {self.user_id}")
        print(f"🌍 Timezone: {self.user_timezone}")

        # Show service status
        print("\n📊 Service Status:")
        for service, available in self.services_available.items():
            status = "✅ Available" if available else "❌ Unavailable"
            print(f"  {service.title()}: {status}")

        # Show authentication methods
        print("\n🔐 Authentication Methods:")
        for method, available in self.auth_methods.items():
            status = "✅ Available" if available else "❌ Unavailable"
            print(f"  {method.title()}: {status}")

        print("\n💡 Enhanced Commands (NextAuth Testing):")
        print("  • 'nextauth google' - Test NextAuth with Google OAuth")
        print("  • 'nextauth microsoft' - Test NextAuth with Microsoft OAuth")
        print("  • 'compare' - Compare Clerk vs NextAuth tokens")
        print("  • 'demo-nextauth' - Run NextAuth integration demonstration")

        print("\n💡 Original Commands:")
        print("  • Type any message to chat")
        print("  • 'delete' - Delete current draft")
        print("  • 'send' - Send current draft via email")
        print("  • 'status' - Show service status")
        print("  • 'auth' - Re-authenticate (prompts for email)")
        print("  • 'oauth google' - Set up Google integration (Clerk)")
        print("  • 'help' - Show all commands")
        print("  • 'exit' - Exit demo")

        if self.use_api:
            print("  • 'list' - List chat threads")
            print("  • 'new' - Start new thread")
            print("  • 'switch <id>' - Switch thread")

        print()

    def show_help(self):
        """Show enhanced help with NextAuth commands."""
        print("\n" + "=" * 60)
        print("📋 Enhanced Briefly Demo - Help")
        print("=" * 60)

        print("\n🔵 NextAuth Testing Commands:")
        print("  • 'nextauth google' - Test NextAuth OAuth flow with Google")
        print("  • 'nextauth microsoft' - Test NextAuth OAuth flow with Microsoft")
        print("  • 'compare' - Compare Clerk vs NextAuth authentication approaches")
        print("  • 'demo-nextauth' - Run full NextAuth integration demonstration")

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
        print("  • 'auth' - Re-authenticate with Clerk")
        print("  • 'oauth google' - Set up Google OAuth integration (Clerk)")
        print("  • 'oauth microsoft' - Set up Microsoft OAuth integration (Clerk)")
        print("  • 'help' - Show this help message")
        print("  • 'exit' or 'quit' - Exit the demo")

        print("\n💡 Comparison Examples:")
        print("  1. Run 'auth' to set up Clerk authentication")
        print("  2. Run 'nextauth google' to test NextAuth with Google")
        print("  3. Run 'compare' to see the differences")

    async def send_message_local(self, message: str) -> str:
        """Send a message using local agent."""
        if not self.agent:
            return "❌ Agent not available"

        try:
            response = await self.agent.process_message(message)
            return response
        except Exception as e:
            logger.error(f"Local agent error: {e}")
            return f"❌ Error: {e}"

    def _render_drafts_as_text(self, drafts):
        """Render drafts as text for display."""
        if not drafts:
            return "No drafts available"

        text = "📝 Current Drafts:\n"
        for i, draft in enumerate(drafts, 1):
            text += f"\n{i}. {draft.get('type', 'Unknown')} Draft\n"
            text += f"   Subject: {draft.get('subject', 'No subject')}\n"
            text += f"   To: {', '.join(draft.get('to', []))}\n"
            text += f"   Content: {draft.get('content', 'No content')[:100]}...\n"
            text += f"   Created: {draft.get('created_at', 'Unknown')}\n"

        return text

    def send_message_api(self, message: str) -> str:
        """Send a message using API."""
        response = self.chat_client.send_message(
            self.user_id, message, self.current_thread_id
        )
        if response:
            return response
        else:
            return "❌ Failed to send message"

    async def send_message(self, message: str) -> str:
        """Send a message using the appropriate method."""
        if self.use_api:
            return self.send_message_api(message)
        else:
            return await self.send_message_local(message)

    async def handle_delete_command(self) -> str:
        """Handle delete command."""
        if self.use_api:
            success = self.chat_client.delete_draft(
                self.user_id, self.current_thread_id
            )
            return "✅ Draft deleted" if success else "❌ Failed to delete draft"
        else:
            return "❌ Delete not supported in local mode"

    async def handle_send_command(self) -> str:
        """Handle send command."""
        if not self.services_available["office"]:
            return "❌ Office service not available"

        # For demo purposes, send a test email
        email_data = {
            "to": ["demo@example.com"],
            "subject": "Test Email from Briefly Demo",
            "body": "This is a test email sent from the Briefly demo.",
        }

        success = await self.office_client.send_email(self.user_id, email_data)
        return "✅ Email sent" if success else "❌ Failed to send email"

    async def handle_status_command(self) -> str:
        """Handle status command."""
        status = "📊 Service Status:\n"
        for service, available in self.services_available.items():
            status += f"  {service.title()}: {'✅ Available' if available else '❌ Unavailable'}\n"

        status += f"\n🔐 Authentication: {'✅ Authenticated' if self.authenticated else '❌ Not authenticated'}\n"
        status += f"👤 User: {self.user_id}\n"
        status += f"🌍 Timezone: {self.user_timezone}\n"

        if self.use_api:
            status += f"🧵 Thread: {self.current_thread_id or 'None'}\n"

        return status

    async def handle_auth_command(self, email: Optional[str] = None) -> str:
        """Handle auth command."""
        success = await self.authenticate(email)
        return "✅ Authentication successful" if success else "❌ Authentication failed"

    async def handle_timezone_command(self, timezone: str) -> str:
        """Handle timezone command."""
        if not self.authenticated:
            return "❌ Not authenticated"

        try:
            # Update user preferences with new timezone
            preferences_update = {"ui_preferences": {"timezone": timezone}}
            success = await self.user_client.update_user_preferences(preferences_update)
            if success:
                self.user_timezone = timezone
                return f"✅ Timezone updated to {timezone}"
            else:
                return "❌ Failed to update timezone"
        except Exception as e:
            return f"❌ Error updating timezone: {e}"

    async def handle_nextauth_command(self, provider: str) -> str:
        """Handle NextAuth testing command."""
        if not NEXTAUTH_AVAILABLE:
            return "❌ NextAuth utilities not available"

        if not self.auth_methods.get("nextauth"):
            return "❌ NextAuth test server not available. Start with: python services/demos/nextauth_test_server.py"

        if provider not in ["google", "microsoft"]:
            return "❌ Supported providers: google, microsoft"

        print(f"\n🎭 Testing NextAuth OAuth Flow - {provider.title()}")
        print("=" * 50)

        token = await test_nextauth_flow(provider)
        if token:
            self.nextauth_token = token
            return f"✅ NextAuth {provider} authentication successful!"
        else:
            return f"❌ NextAuth {provider} authentication failed"

    async def handle_compare_command(self) -> str:
        """Handle compare command to compare authentication approaches."""
        if not NEXTAUTH_AVAILABLE:
            return "❌ NextAuth utilities not available"

        if not self.auth_token:
            return "❌ No Clerk token available. Run 'auth' first."

        if not self.nextauth_token:
            return "❌ No NextAuth token available. Run 'nextauth <provider>' first."

        print("\n🔍 Running authentication comparison...")
        comparison = await compare_auth_approaches(self.auth_token, self.nextauth_token)
        return comparison

    async def handle_demo_nextauth_command(self) -> str:
        """Handle demo-nextauth command."""
        if not NEXTAUTH_AVAILABLE:
            return "❌ NextAuth utilities not available"

        print("\n🎭 Running NextAuth Integration Demonstration")
        print("=" * 50)

        demo_result = await demonstrate_nextauth_integration()
        return demo_result

    def handle_api_commands(self, command: str) -> tuple[bool, str]:
        """Handle API-specific commands."""
        if command == "list":
            if not self.services_available["chat"]:
                return True, "❌ Chat service not available"

            threads = self.chat_client.get_threads(self.user_id)
            if not threads:
                return True, "📝 No chat threads found"

            result = "📝 Chat Threads:\n"
            for thread in threads:
                result += f"  {thread['id']}: {thread.get('title', 'Untitled')}\n"
            return True, result

        elif command.startswith("switch "):
            thread_id = command[7:].strip()
            if thread_id:
                self.current_thread_id = thread_id
                return True, f"✅ Switched to thread {thread_id}"
            else:
                return True, "❌ Please provide a thread ID"

        elif command == "new":
            self.current_thread_id = None
            return True, "✅ Started new thread"

        return False, ""

    async def chat_loop(self):
        """Main chat loop with NextAuth command support."""
        print("🚀 Starting chat loop... (type 'help' for commands, 'exit' to quit)")

        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()

                if not user_input:
                    continue

                # Handle exit commands
                if user_input.lower() in ["exit", "quit"]:
                    print("👋 Goodbye!")
                    break

                # Handle help command
                if user_input.lower() == "help":
                    self.show_help()
                    continue

                # Handle status command
                if user_input.lower() == "status":
                    status = await self.handle_status_command()
                    print(f"\n{status}")
                    continue

                # Handle auth command
                if user_input.lower() == "auth":
                    email = input("Enter email (or press Enter for default): ").strip()
                    email = email if email else None
                    result = await self.handle_auth_command(email)
                    print(f"\n{result}")
                    continue

                # Handle OAuth commands
                if user_input.lower().startswith("oauth "):
                    provider = user_input[6:].strip()
                    if provider in ["google", "microsoft"]:
                        result = await self.setup_oauth_integration(provider)
                        print(
                            f"\n{'✅ OAuth setup successful' if result else '❌ OAuth setup failed'}"
                        )
                    else:
                        print("❌ Supported providers: google, microsoft")
                    continue

                # Handle NextAuth commands
                if user_input.lower().startswith("nextauth "):
                    provider = user_input[10:].strip()
                    result = await self.handle_nextauth_command(provider)
                    print(f"\n{result}")
                    continue

                # Handle compare command
                if user_input.lower() == "compare":
                    result = await self.handle_compare_command()
                    print(f"\n{result}")
                    continue

                # Handle demo-nextauth command
                if user_input.lower() == "demo-nextauth":
                    result = await self.handle_demo_nextauth_command()
                    print(f"\n{result}")
                    continue

                # Handle timezone command
                if user_input.lower().startswith("timezone "):
                    timezone = user_input[9:].strip()
                    result = await self.handle_timezone_command(timezone)
                    print(f"\n{result}")
                    continue

                # Handle API-specific commands
                if self.use_api:
                    handled, result = self.handle_api_commands(user_input)
                    if handled:
                        print(f"\n{result}")
                        continue

                # Handle delete command
                if user_input.lower() == "delete":
                    result = await self.handle_delete_command()
                    print(f"\n{result}")
                    continue

                # Handle send command
                if user_input.lower() == "send":
                    result = await self.handle_send_command()
                    print(f"\n{result}")
                    continue

                # Handle clear command
                if user_input.lower() == "clear":
                    print("🧹 Conversation cleared")
                    continue

                # Send message
                print("\n🤖 Briefly: ", end="", flush=True)
                response = await self.send_message(user_input)
                print(response)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    async def run_streaming_demo(self):
        """Run streaming demo."""
        print("🌊 Running streaming demo...")
        print("Type messages to see streaming responses (type 'exit' to quit)")

        while True:
            try:
                user_input = input("\n👤 You: ").strip()

                if user_input.lower() in ["exit", "quit"]:
                    break

                if not user_input:
                    continue

                print("\n🤖 Briefly: ", end="", flush=True)
                await self._stream_api_response(user_input)

            except KeyboardInterrupt:
                break

        print("\n👋 Streaming demo finished!")

    async def _stream_api_response(self, message: str):
        """Stream API response."""
        if not self.services_available["chat"]:
            print("❌ Chat service not available")
            return

        try:
            # This would implement actual streaming
            # For now, just simulate it
            response = self.send_message_api(message)
            for char in response:
                print(char, end="", flush=True)
                await asyncio.sleep(0.01)
            print()

        except Exception as e:
            print(f"❌ Streaming error: {e}")

    async def cleanup(self):
        """Clean up resources."""
        if self.agent:
            await self.agent.cleanup()


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Briefly Demo")
    parser.add_argument(
        "--local", action="store_true", help="Use local multi-agent mode"
    )
    parser.add_argument("--streaming", action="store_true", help="Run streaming demo")
    parser.add_argument("--no-auth", action="store_true", help="Skip authentication")
    parser.add_argument("--message", help="Send a single message and exit")
    parser.add_argument("--email", help="Use custom email for authentication")
    parser.add_argument(
        "--nextauth-only", action="store_true", help="NextAuth testing only"
    )
    parser.add_argument("--compare", action="store_true", help="Run comparison demo")

    args = parser.parse_args()

    # Set up demo
    use_api = not args.local
    chat_url = "http://localhost:8002"
    office_url = "http://localhost:8003"
    user_url = "http://localhost:8001"
    user_id = args.email or DEFAULT_USER_ID

    demo = FullDemo(
        use_api=use_api,
        chat_url=chat_url,
        office_url=office_url,
        user_url=user_url,
        user_id=user_id,
        skip_auth=args.no_auth,
    )

    try:
        # Check services
        await demo.check_services()

        # Handle NextAuth-only mode
        if args.nextauth_only:
            if not NEXTAUTH_AVAILABLE:
                print("❌ NextAuth utilities not available")
                return

            print("🔵 NextAuth Testing Mode")
            print("=" * 30)

            # Test NextAuth flows
            for provider in ["google", "microsoft"]:
                print(f"\n🎭 Testing {provider} OAuth flow...")
                token = await test_nextauth_flow(provider)
                if token:
                    print(f"✅ {provider.title()} OAuth successful")
                else:
                    print(f"❌ {provider.title()} OAuth failed")

            # Run comparison if requested
            if args.compare:
                print("\n🔍 Running authentication comparison...")
                comparison = await compare_auth_approaches(None, None)
                print(comparison)

            return

        # Handle comparison mode
        if args.compare:
            if not NEXTAUTH_AVAILABLE:
                print("❌ NextAuth utilities not available")
                return

            print("🔍 Authentication Comparison Mode")
            print("=" * 30)

            # Create demo tokens for comparison
            clerk_token = create_bearer_token(user_id)
            nextauth_token = create_nextauth_jwt_for_demo(user_id)

            comparison = await compare_auth_approaches(clerk_token, nextauth_token)
            print(comparison)
            return

        # Authenticate
        if not await demo.authenticate():
            print("❌ Authentication failed")
            return

        # Load user timezone
        await demo.load_user_timezone()

        # Create agent for local mode
        if not use_api:
            demo.agent = await demo.create_agent()

        # Show welcome
        demo.show_welcome()

        # Handle single message mode
        if args.message:
            print(f"🤖 Sending message: {args.message}")
            response = await demo.send_message(args.message)
            print(f"🤖 Response: {response}")
            return

        # Handle streaming mode
        if args.streaming:
            await demo.run_streaming_demo()
            return

        # Start chat loop
        await demo.chat_loop()

    except KeyboardInterrupt:
        print("\n👋 Demo interrupted")
    except Exception as e:
        print(f"❌ Demo error: {e}")
    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
