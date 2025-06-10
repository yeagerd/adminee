#!/usr/bin/env python3
"""
User Management Service Demo

This demo showcases the user management service functionality including:
- User profile management
- OAuth integration flows (Google, Microsoft)
- User preferences
- Real API calls to running service
- Interactive OAuth flows with browser windows

Requirements:
- User management service running on http://localhost:8000
- Valid OAuth credentials configured
- Web browser available for OAuth flows
"""

import asyncio
import json
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx
import structlog

# Import demo JWT utilities
try:
    from demo_jwt_utils import create_bearer_token
except ImportError:
    print("❌ demo_jwt_utils not found. Please ensure demo_jwt_utils.py is in the same directory.")
    exit(1)

# Set up logging
logger = structlog.get_logger(__name__)


class UserManagementDemo:
    """Demo class for user management service."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.demo_user_id = "demo_user_12345"
        self.service_api_key = "demo-service-key-12345"  # For internal API calls
        # Generate valid JWT token for demo user
        self.auth_token = create_bearer_token(
            self.demo_user_id,
            "demo.user@example.com"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    def print_header(self, title: str):
        """Print a formatted header."""
        print("\n" + "=" * 60)
        print(f" {title}")
        print("=" * 60)

    def print_section(self, title: str):
        """Print a formatted section header."""
        print(f"\n--- {title} ---")

    def print_response(self, response: httpx.Response, description: str = ""):
        """Print formatted response information."""
        status_color = "🟢" if response.status_code < 400 else "🔴"
        print(f"{status_color} {response.status_code} {response.reason_phrase}")
        if description:
            print(f"   {description}")
        
        try:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        except Exception:
            print(f"   Response: {response.text[:200]}...")

    async def check_service_health(self) -> bool:
        """Check if the user management service is running."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            self.print_response(response, "Health check")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Service not available: {e}")
            return False

    async def check_service_readiness(self) -> bool:
        """Check if the service is ready."""
        try:
            response = await self.client.get(f"{self.base_url}/ready")
            self.print_response(response, "Readiness check")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Service not ready: {e}")
            return False

    async def create_demo_user(self) -> bool:
        """Create a demo user via webhook simulation."""
        self.print_section("Creating Demo User via Webhook")
        
        # Simulate Clerk webhook for user creation
        webhook_payload = {
            "type": "user.created",
            "object": "event",  # Required by ClerkWebhookEvent schema
            "data": {
                "id": self.demo_user_id,
                "email_addresses": [
                    {
                        "email_address": "demo.user@example.com",
                        "verification": {"status": "verified"}
                    }
                ],
                "first_name": "Demo",
                "last_name": "User",
                "image_url": "https://images.clerk.dev/demo-avatar.png",  # Changed from profile_image_url
                "created_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/webhooks/clerk",
                json=webhook_payload,
                headers={
                    "Content-Type": "application/json",
                    "svix-id": "msg_demo_12345",
                    "svix-timestamp": str(int(time.time())),
                    "svix-signature": "v1,demo_signature",  # Would be real in production
                }
            )
            self.print_response(response, "Demo user creation via webhook")
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"🔴 Failed to create demo user: {e}")
            return False

    async def get_user_profile(self) -> Optional[Dict]:
        """Get user profile."""
        self.print_section("Getting User Profile")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/users/{self.demo_user_id}",
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, "User profile retrieval")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"🔴 Failed to get user profile: {e}")
            return None

    async def update_user_profile(self) -> bool:
        """Update user profile."""
        self.print_section("Updating User Profile")
        
        update_data = {
            "first_name": "Demo Updated",
            "last_name": "User Updated",
            "bio": "This is a demo user for testing the user management service!",
            "location": "San Francisco, CA",
            "website": "https://demo.example.com"
        }

        try:
            response = await self.client.put(
                f"{self.base_url}/users/{self.demo_user_id}",
                json=update_data,
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, "User profile update")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to update user profile: {e}")
            return False

    async def get_user_preferences(self) -> Optional[Dict]:
        """Get user preferences."""
        self.print_section("Getting User Preferences")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/users/{self.demo_user_id}/preferences",
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, "User preferences retrieval")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"🔴 Failed to get user preferences: {e}")
            return None

    async def update_user_preferences(self) -> bool:
        """Update user preferences."""
        self.print_section("Updating User Preferences")
        
        preferences_update = {
            "ui_preferences": {
                "theme": "dark",
                "language": "en",
                "timezone": "America/Los_Angeles",
                "date_format": "MM/DD/YYYY",
                "time_format": "12h"
            },
            "notification_preferences": {
                "email_notifications": True,
                "push_notifications": True,
                "sms_notifications": False,
                "marketing_emails": False
            },
            "ai_preferences": {
                "enable_ai_features": True,
                "ai_model_preference": "gpt-4",
                "auto_suggestions": True,
                "data_sharing_consent": True
            }
        }

        try:
            response = await self.client.put(
                f"{self.base_url}/users/{self.demo_user_id}/preferences",
                json=preferences_update,
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, "User preferences update")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to update user preferences: {e}")
            return False

    async def list_integrations(self) -> Optional[List[Dict]]:
        """List user integrations."""
        self.print_section("Listing User Integrations")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/users/{self.demo_user_id}/integrations",
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, "User integrations list")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"🔴 Failed to list integrations: {e}")
            return None

    async def start_oauth_flow(self, provider: str) -> Optional[str]:
        """Start OAuth flow for a provider."""
        self.print_section(f"Starting OAuth Flow for {provider.title()}")
        
        redirect_uri = "http://localhost:8000/oauth/callback"
        scopes = ["read", "write"] if provider == "google" else ["read"]
        
        try:
            response = await self.client.post(
                f"{self.base_url}/users/{self.demo_user_id}/integrations/{provider}/oauth/start",
                json={
                    "redirect_uri": redirect_uri,
                    "scopes": scopes
                },
                headers={"Authorization": self.auth_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                auth_url = data.get("authorization_url")
                state = data.get("state")
                
                print(f"🟢 OAuth flow started successfully")
                print(f"   Authorization URL: {auth_url}")
                print(f"   State: {state}")
                
                # Open browser for OAuth authorization
                print(f"\n🌐 Opening browser for {provider.title()} OAuth authorization...")
                print("   Please complete the OAuth flow in your browser.")
                print("   After authorization, you'll be redirected back to the service.")
                
                webbrowser.open(auth_url)
                
                # Wait for user to complete OAuth flow
                input(f"\nPress Enter after completing the {provider.title()} OAuth flow...")
                
                return state
            else:
                self.print_response(response, f"Failed to start {provider} OAuth flow")
                return None
        except Exception as e:
            print(f"🔴 Failed to start OAuth flow: {e}")
            return None

    async def complete_oauth_flow(self, provider: str, state: str, code: str) -> bool:
        """Complete OAuth flow with authorization code."""
        self.print_section(f"Completing OAuth Flow for {provider.title()}")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/users/{self.demo_user_id}/integrations/{provider}/oauth/callback",
                json={
                    "code": code,
                    "state": state
                },
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, f"{provider.title()} OAuth completion")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to complete OAuth flow: {e}")
            return False

    async def get_integration_status(self, provider: str) -> Optional[Dict]:
        """Get integration status for a provider."""
        self.print_section(f"Getting {provider.title()} Integration Status")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/users/{self.demo_user_id}/integrations/{provider}",
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, f"{provider.title()} integration status")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"🔴 Failed to get integration status: {e}")
            return None

    async def refresh_integration_token(self, provider: str) -> bool:
        """Refresh integration token."""
        self.print_section(f"Refreshing {provider.title()} Token")
        
        try:
            response = await self.client.put(
                f"{self.base_url}/users/{self.demo_user_id}/integrations/{provider}/refresh",
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, f"{provider.title()} token refresh")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to refresh token: {e}")
            return False

    async def test_internal_api(self) -> bool:
        """Test internal service-to-service API."""
        self.print_section("Testing Internal Service-to-Service API")
        
        token_request = {
            "user_id": self.demo_user_id,
            "provider": "google",
            "scopes": ["read"]
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/internal/tokens/get",
                json=token_request,
                headers={
                    "X-API-Key": self.service_api_key,
                    "X-Service-Name": "demo-service"
                }
            )
            self.print_response(response, "Internal token retrieval")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to test internal API: {e}")
            return False

    async def disconnect_integration(self, provider: str) -> bool:
        """Disconnect an integration."""
        self.print_section(f"Disconnecting {provider.title()} Integration")
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/users/{self.demo_user_id}/integrations/{provider}",
                headers={"Authorization": self.auth_token}
            )
            self.print_response(response, f"{provider.title()} integration disconnect")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to disconnect integration: {e}")
            return False

    async def run_interactive_demo(self):
        """Run an interactive demo with user choices."""
        self.print_header("User Management Service Interactive Demo")
        
        # Check service health
        if not await self.check_service_health():
            print("❌ Service is not running. Please start the service first:")
            print("   cd services/user_management && uvicorn main:app --reload --port 8000")
            return False

        # Check service readiness
        await self.check_service_readiness()

        # Create demo user
        await self.create_demo_user()

        # User profile operations
        await self.get_user_profile()
        await self.update_user_profile()
        await self.get_user_profile()  # Show updated profile

        # User preferences
        await self.get_user_preferences()
        await self.update_user_preferences()
        await self.get_user_preferences()  # Show updated preferences

        # List current integrations
        await self.list_integrations()

        # Interactive OAuth flow
        while True:
            print("\n" + "🔗" * 20)
            print("OAuth Integration Demo")
            print("🔗" * 20)
            print("1. Connect Google Integration")
            print("2. Connect Microsoft Integration")
            print("3. View Integration Status")
            print("4. Refresh Integration Token")
            print("5. Test Internal API")
            print("6. Disconnect Integration")
            print("7. Skip OAuth Demo")
            print("0. Exit Demo")
            
            choice = input("\nEnter your choice (0-7): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                await self.demo_oauth_flow("google")
            elif choice == "2":
                await self.demo_oauth_flow("microsoft")
            elif choice == "3":
                provider = input("Enter provider (google/microsoft): ").strip().lower()
                if provider in ["google", "microsoft"]:
                    await self.get_integration_status(provider)
            elif choice == "4":
                provider = input("Enter provider (google/microsoft): ").strip().lower()
                if provider in ["google", "microsoft"]:
                    await self.refresh_integration_token(provider)
            elif choice == "5":
                await self.test_internal_api()
            elif choice == "6":
                provider = input("Enter provider (google/microsoft): ").strip().lower()
                if provider in ["google", "microsoft"]:
                    await self.disconnect_integration(provider)
            elif choice == "7":
                break
            else:
                print("Invalid choice. Please try again.")

        print("\n✅ Demo completed!")
        return True

    async def demo_oauth_flow(self, provider: str):
        """Demo OAuth flow for a provider."""
        print(f"\n🚀 Starting {provider.title()} OAuth Demo")
        print("This will open your browser for OAuth authorization.")
        print("Note: You'll need valid OAuth credentials configured for this to work.")
        
        proceed = input(f"Do you want to proceed with {provider.title()} OAuth? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Skipping OAuth flow.")
            return

        # Start OAuth flow
        state = await self.start_oauth_flow(provider)
        if not state:
            print(f"Failed to start {provider.title()} OAuth flow.")
            return

        # In a real scenario, the OAuth callback would be handled by the service
        # For this demo, we'll simulate the completion
        print(f"\n⚠️  OAuth callback simulation:")
        print(f"   In a real scenario, {provider.title()} would redirect back to the service")
        print(f"   with an authorization code that would be exchanged for tokens.")
        print(f"   For this demo, we'll check the integration status instead.")
        
        # Check integration status
        await self.get_integration_status(provider)

    async def run_comprehensive_demo(self):
        """Run a comprehensive demo showing all features."""
        self.print_header("User Management Service Comprehensive Demo")
        
        print("This demo showcases the user management service capabilities:")
        print("• Health and readiness checks")
        print("• User profile management")
        print("• User preferences")
        print("• OAuth integrations (Google, Microsoft)")
        print("• Service-to-service API")
        print("• Real API calls to running service")
        print("• Interactive OAuth flows")
        
        return await self.run_interactive_demo()


async def main():
    """Main demo function."""
    print("🎯 User Management Service Demo")
    print("================================")
    print()
    print("This demo requires:")
    print("• User management service running on http://localhost:8000")
    print("• Valid OAuth credentials (optional for OAuth demo)")
    print("• Web browser for OAuth flows")
    print()

    async with UserManagementDemo() as demo:
        success = await demo.run_comprehensive_demo()
        if success:
            print("\n🎉 Demo completed successfully!")
        else:
            print("\n❌ Demo encountered issues.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        sys.exit(1) 