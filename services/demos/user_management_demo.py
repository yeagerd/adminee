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
- Valid OAuth credentials configured (for OAuth demo)
- Web browser available for OAuth flows

Usage:
- python user_management_demo.py              # Interactive demo with OAuth menu
- python user_management_demo.py --simple     # Simple non-interactive demo
"""

import argparse
import asyncio
import json
import os
import sys
import time
import webbrowser
from datetime import datetime, timezone
from typing import Dict, List, Optional

import dotenv
import httpx
import structlog

# Import demo JWT utilities
try:
    from demo_jwt_utils import create_bearer_token, decode_token
except ImportError:
    print(
        "❌ demo_jwt_utils not found. Please ensure demo_jwt_utils.py is in the same directory."
    )
    exit(1)

# Set up logging
logger = structlog.get_logger(__name__)


class UserManagementDemo:
    """Demo class for user management service."""

    base_url: str
    client: httpx.AsyncClient
    demo_user_id: str
    demo_database_user_id: Optional[int]
    service_api_key: Optional[str]
    api_key_source: str
    auth_token: str
    test_results: Dict[str, bool]

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        user_management_api_key: Optional[str] = None,
    ):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.demo_user_id = "demo_user_12345"  # This is the external auth ID (Clerk ID)
        self.demo_database_user_id = None  # This will be set after user creation

        # Set service API key with precedence: arg > env var > default
        if user_management_api_key:
            self.service_api_key = user_management_api_key
            self.api_key_source = "command line argument"
        elif os.getenv("API_FRONTEND_USER_KEY"):
            self.service_api_key = os.getenv("API_FRONTEND_USER_KEY") or ""
            self.api_key_source = "API_FRONTEND_USER_KEY environment variable"
        elif os.path.exists("../../.env"):
            dotenv.load_dotenv()
            self.service_api_key = os.getenv("API_FRONTEND_USER_KEY")
            self.api_key_source = "API_FRONTEND_USER_KEY environment variable"
        else:
            # No default for security - internal API test will fail gracefully
            self.service_api_key = None
            self.api_key_source = "not configured (internal API test will fail)"

        # Generate valid JWT token for demo user
        self.auth_token = create_bearer_token(
            self.demo_user_id, "demo.user@example.com"
        )
        # Track test results for accurate summary
        self.test_results = {
            "service_health": False,
            "service_readiness": False,
            "user_creation": False,
            "profile_operations": False,
            "preferences": False,
            "integrations": False,
            "oauth_initiation": False,
            "internal_api": False,
        }

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
                        "verification": {"status": "verified"},
                    }
                ],
                "first_name": "Demo",
                "last_name": "User",
                "image_url": "https://images.clerk.dev/demo-avatar.png",  # Changed from profile_image_url
                "created_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            },
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
                },
            )
            self.print_response(response, "Demo user creation via webhook")

            # Store the database user ID for later use by getting the created user profile
            if response.status_code in [200, 201]:
                # Get the user profile to extract the database ID
                profile_response = await self.client.get(
                    f"{self.base_url}/users/me",
                    headers={"Authorization": self.auth_token},
                )
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    self.demo_database_user_id = profile_data.get("id")
                    print(
                        f"   💾 Stored database user ID: {self.demo_database_user_id}"
                    )

            return response.status_code in [200, 201]
        except Exception as e:
            print(f"🔴 Failed to create demo user: {e}")
            return False

    async def get_user_profile(self) -> Optional[Dict]:
        """Get user profile."""
        self.print_section("Getting User Profile")

        try:
            # Use /users/me endpoint to get current user's profile
            response = await self.client.get(
                f"{self.base_url}/users/me", headers={"Authorization": self.auth_token}
            )
            self.print_response(response, "User profile retrieval")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"🔴 Failed to get user profile: {e}")
            return None

    async def update_user_profile(self) -> bool:
        """Update user profile."""
        self.print_section("Updating User Profile")

        # First get the user profile to confirm it exists and get the data
        profile = await self.get_user_profile()
        if not profile:
            print("🔴 Cannot update profile - user profile not found")
            return False

        # Use the database user ID for the update endpoint
        if not self.demo_database_user_id:
            print("🔴 Database user ID not available - user may not have been created")
            return False

        update_data = {
            "first_name": "Demo Updated",
            "last_name": "User Updated",
        }

        try:
            # Use the database ID for the update endpoint
            response = await self.client.put(
                f"{self.base_url}/users/{self.demo_database_user_id}",
                json=update_data,
                headers={"Authorization": self.auth_token},
            )
            self.print_response(response, "User profile update")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to update user profile: {e}")
            return False

    async def get_user_clerk_id(self) -> Optional[str]:
        """Get the user's Clerk ID from the JWT token."""
        try:
            # For demo purposes, we'll extract from our known demo user ID
            # In production, this would be extracted from the JWT token claims

            # Remove 'Bearer ' prefix if present
            token = self.auth_token
            if token.startswith("Bearer "):
                token = token[7:]

            claims = decode_token(token)
            return claims.get("sub")  # 'sub' claim contains the user ID
        except Exception as e:
            print(f"🔴 Failed to extract Clerk ID from token: {e}")
            # Fallback to our demo user ID
            return self.demo_user_id

    async def get_user_preferences(self) -> Optional[Dict]:
        """Get user preferences."""
        self.print_section("Getting User Preferences")

        # Get Clerk ID for preferences endpoint (expects string user_id)
        clerk_id = await self.get_user_clerk_id()
        if not clerk_id:
            print("🔴 Could not get user Clerk ID")
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/users/{clerk_id}/preferences",
                headers={"Authorization": self.auth_token},
            )
            self.print_response(response, "User preferences retrieval")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"🔴 Failed to get user preferences: {e}")
            return None

    async def update_user_preferences(self) -> bool:
        """Update user preferences."""
        self.print_section("Updating User Preferences")

        # Get Clerk ID for preferences endpoint (expects string user_id)
        clerk_id = await self.get_user_clerk_id()
        if not clerk_id:
            print("🔴 Could not get user Clerk ID")
            return False

        preferences_update = {
            "ui_preferences": {
                "theme": "dark",
                "language": "en",
                "timezone": "America/Los_Angeles",
                "date_format": "MM/DD/YYYY",
                "time_format": "12h",
            },
            "notification_preferences": {
                "email_notifications": True,
                "push_notifications": True,
                "sms_notifications": False,
                "marketing_emails": False,
            },
            "ai_preferences": {
                "enable_ai_features": True,
                "ai_model_preference": "gpt-4",
                "auto_suggestions": True,
                "data_sharing_consent": True,
            },
        }

        try:
            response = await self.client.put(
                f"{self.base_url}/users/{clerk_id}/preferences",
                json=preferences_update,
                headers={"Authorization": self.auth_token},
            )
            self.print_response(response, "User preferences update")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to update user preferences: {e}")
            return False

    async def list_integrations(self) -> Optional[List[Dict]]:
        """List user integrations."""
        self.print_section("Listing User Integrations")

        # Get Clerk ID for integrations endpoint (expects string user_id)
        clerk_id = await self.get_user_clerk_id()
        if not clerk_id:
            print("🔴 Could not get user Clerk ID")
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/users/{clerk_id}/integrations",
                headers={"Authorization": self.auth_token},
            )
            self.print_response(response, "User integrations list")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"🔴 Failed to list integrations: {e}")
            return None

    async def start_oauth_flow(self, provider: str) -> Optional[str]:
        """Start OAuth flow for a provider."""
        self.print_section(f"Starting OAuth Flow for {provider.title()}")

        # Get Clerk ID for integrations endpoint (expects string user_id)
        clerk_id = await self.get_user_clerk_id()
        if not clerk_id:
            print("🔴 Could not get user Clerk ID")
            return None

        redirect_uri = "http://localhost:8000/oauth/callback"
        scopes = ["read", "write"] if provider == "google" else ["read"]

        try:
            response = await self.client.post(
                f"{self.base_url}/users/{clerk_id}/integrations/{provider}/oauth/start",
                json={"redirect_uri": redirect_uri, "scopes": scopes},
                headers={"Authorization": self.auth_token},
            )

            if response.status_code == 200:
                data = response.json()
                auth_url = data.get("authorization_url")
                state = data.get("state")

                print("🟢 OAuth flow started successfully")
                print(f"   Authorization URL: {auth_url}")
                print(f"   State: {state}")

                # Open browser for OAuth authorization
                print(
                    f"\n🌐 Opening browser for {provider.title()} OAuth authorization..."
                )
                print("   Please complete the OAuth flow in your browser.")
                print(
                    "   After authorization, you'll be redirected back to the service."
                )

                webbrowser.open(auth_url)

                # Wait for user to complete OAuth flow
                input(
                    f"\nPress Enter after completing the {provider.title()} OAuth flow..."
                )

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

        # Get Clerk ID for integrations endpoint (expects string user_id)
        clerk_id = await self.get_user_clerk_id()
        if not clerk_id:
            print("🔴 Could not get user Clerk ID")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/users/{clerk_id}/integrations/{provider}/oauth/callback",
                json={"code": code, "state": state},
                headers={"Authorization": self.auth_token},
            )
            self.print_response(response, f"{provider.title()} OAuth completion")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to complete OAuth flow: {e}")
            return False

    async def get_integration_status(self, provider: str) -> Optional[Dict]:
        """Get integration status for a provider."""
        self.print_section(f"Getting {provider.title()} Integration Status")

        # Get Clerk ID for integrations endpoint (expects string user_id)
        clerk_id = await self.get_user_clerk_id()
        if not clerk_id:
            print("🔴 Could not get user Clerk ID")
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/users/{clerk_id}/integrations/{provider}",
                headers={"Authorization": self.auth_token},
            )
            self.print_response(response, f"{provider.title()} integration status")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"🔴 Failed to get integration status: {e}")
            return None

    async def refresh_integration_token(self, provider: str) -> bool:
        """Refresh integration token for a provider."""
        self.print_section(f"Refreshing {provider.title()} Integration Token")

        # Get Clerk ID for integrations endpoint (expects string user_id)
        clerk_id = await self.get_user_clerk_id()
        if not clerk_id:
            print("🔴 Could not get user Clerk ID")
            return False

        try:
            response = await self.client.put(
                f"{self.base_url}/users/{clerk_id}/integrations/{provider}/refresh",
                headers={"Authorization": self.auth_token},
            )
            self.print_response(response, f"{provider.title()} token refresh")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to refresh integration token: {e}")
            return False

    async def test_internal_api(self) -> bool:
        """Test internal service-to-service API."""
        self.print_section("Testing Internal Service-to-Service API")

        print(f"   🔑 Using API key from: {self.api_key_source}")

        if self.service_api_key is None:
            print("   ⚠️  No API key configured - test will fail as expected")
            print("   💡 Set SERVICE_API_KEY env var or use --service-api-key flag")
            return False

        print(
            f"   🔑 API key: {self.service_api_key[:8]}..."
            if len(self.service_api_key) > 8
            else f"   🔑 API key: {self.service_api_key}"
        )

        token_request = {
            "user_id": self.demo_user_id,
            "provider": "google",
            "scopes": ["read"],
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/internal/tokens/get",
                json=token_request,
                headers={
                    "X-API-Key": self.service_api_key,
                    "X-Service-Name": "demo-service",
                },
            )
            self.print_response(response, "Internal token retrieval")
            return response.status_code == 200
        except Exception as e:
            print(f"🔴 Failed to test internal API: {e}")
            return False

    async def disconnect_integration(self, provider: str) -> bool:
        """Disconnect integration for a provider."""
        self.print_section(f"Disconnecting {provider.title()} Integration")

        # Get Clerk ID for integrations endpoint (expects string user_id)
        clerk_id = await self.get_user_clerk_id()
        if not clerk_id:
            print("🔴 Could not get user Clerk ID")
            return False

        try:
            response = await self.client.delete(
                f"{self.base_url}/users/{clerk_id}/integrations/{provider}",
                headers={"Authorization": self.auth_token},
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
            print(
                "   cd services/user_management && uvicorn main:app --reload --port 8000"
            )
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

        proceed = (
            input(f"Do you want to proceed with {provider.title()} OAuth? (y/n): ")
            .strip()
            .lower()
        )
        if proceed != "y":
            print("Skipping OAuth flow.")
            return

        # Start OAuth flow
        state = await self.start_oauth_flow(provider)
        if not state:
            print(f"Failed to start {provider.title()} OAuth flow.")
            return

        # In a real scenario, the OAuth callback would be handled by the service
        # For this demo, we'll simulate the completion
        print("\n⚠️  OAuth callback simulation:")
        print(
            f"   In a real scenario, {provider.title()} would redirect back to the service"
        )
        print("   with an authorization code that would be exchanged for tokens.")
        print("   For this demo, we'll check the integration status instead.")

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

    async def run_simple_demo(self):
        """Run a simple non-interactive demo."""
        self.print_header("User Management Service Simple Demo")

        print("This simple demo showcases core user management functionality:")
        print("• Health and readiness checks")
        print("• User profile management")
        print("• User preferences")
        print("• Integration listing")
        print("• OAuth flow initiation (without completion)")
        print("• Service-to-service API")
        print()

        # Check service health
        self.print_section("Service Health Check")
        self.test_results["service_health"] = await self.check_service_health()
        if not self.test_results["service_health"]:
            print("❌ Service is not running. Please start the service first:")
            print("   cd /Users/yeagerd/github/briefly")
            print("   uvicorn services.user_management.main:app --reload --port 8000")
            return False

        # Check service readiness
        self.test_results["service_readiness"] = await self.check_service_readiness()

        # Create demo user
        self.test_results["user_creation"] = await self.create_demo_user()

        # User profile operations
        profile_get = await self.get_user_profile()
        profile_update = await self.update_user_profile()
        self.test_results["profile_operations"] = (
            profile_get is not None and profile_update
        )

        # User preferences
        prefs_get = await self.get_user_preferences()
        prefs_update = await self.update_user_preferences()
        self.test_results["preferences"] = prefs_get is not None and prefs_update

        # List current integrations
        integrations = await self.list_integrations()
        self.test_results["integrations"] = integrations is not None

        # Test OAuth flow initiation (without completion)
        self.print_section("Testing OAuth Flow Initiation")
        google_oauth = await self.start_oauth_flow("google")
        microsoft_oauth = await self.start_oauth_flow("microsoft")
        self.test_results["oauth_initiation"] = (
            google_oauth is not None and microsoft_oauth is not None
        )

        # Test internal API
        self.test_results["internal_api"] = await self.test_internal_api()

        # Show accurate summary
        self.print_header("Simple Demo Summary")

        # Determine overall success
        failed_tests = [
            name for name, passed in self.test_results.items() if not passed
        ]
        overall_success = len(failed_tests) == 0

        if overall_success:
            print("✅ Demo completed successfully!")
        else:
            print("⚠️ Demo completed with some failures.")

        print("📋 All core functionality tested:")

        # Helper function to get status icon
        def get_status(passed: bool) -> str:
            return "✅" if passed else "❌"

        print(f"   - Service health: {get_status(self.test_results['service_health'])}")
        print(
            f"   - Service readiness: {get_status(self.test_results['service_readiness'])}"
        )
        print(f"   - User creation: {get_status(self.test_results['user_creation'])}")
        print(
            f"   - Profile operations: {get_status(self.test_results['profile_operations'])}"
        )
        print(f"   - Preferences: {get_status(self.test_results['preferences'])}")
        print(f"   - Integrations: {get_status(self.test_results['integrations'])}")
        print(
            f"   - OAuth initiation: {get_status(self.test_results['oauth_initiation'])}"
        )
        print(f"   - Internal API: {get_status(self.test_results['internal_api'])}")

        if failed_tests:
            print(f"\n❌ Failed tests: {', '.join(failed_tests)}")
            if "oauth_initiation" in failed_tests:
                print(
                    "   • OAuth endpoints not implemented or credentials not configured"
                )
            if "internal_api" in failed_tests:
                print("   • Service API key validation issues")

        print()
        print("💡 For interactive OAuth flows, run without --simple flag")

        return overall_success


async def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(
        description="User Management Service Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python user_management_demo.py              # Interactive demo with OAuth menu
  python user_management_demo.py --simple     # Simple non-interactive demo
  
Environment Variables:
  API_FRONTEND_USER_KEY          Service-to-service API key for internal API testing
        """,
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Run simple non-interactive demo (skips OAuth menu)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the user management service (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--service-api-key",
        help="Service API key for internal API testing (overrides API_FRONTEND_USER_KEY env var)",
    )

    args = parser.parse_args()

    print("🎯 User Management Service Demo")
    print("================================")
    print()

    if args.simple:
        print("Running in SIMPLE mode (non-interactive)")
        print()
        print("This demo requires:")
        print("• User management service running on", args.base_url)
        print()
    else:
        print("Running in INTERACTIVE mode")
        print()
        print("This demo requires:")
        print("• User management service running on", args.base_url)
        print("• Valid OAuth credentials (optional for OAuth demo)")
        print("• Web browser for OAuth flows")
        print()

    async with UserManagementDemo(
        base_url=args.base_url,
        user_management_api_key=getattr(args, "service_api_key", None),
    ) as demo:
        if args.simple:
            success = await demo.run_simple_demo()
        else:
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
