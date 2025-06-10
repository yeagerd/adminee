#!/usr/bin/env python3
"""
Simple User Management Service Demo

A lightweight demo that showcases core user management functionality
without requiring OAuth credentials. Perfect for quick testing and
demonstration of the service capabilities.

Requirements:
- User management service running on http://localhost:8000
- Python 3.9+ with httpx installed
"""

import asyncio
import json
import time
import webbrowser
from datetime import datetime, timezone
from typing import Dict, Optional

try:
    import httpx
except ImportError:
    print("❌ httpx not installed. Install with: pip install httpx")
    exit(1)

# Import demo JWT utilities
try:
    from demo_jwt_utils import create_bearer_token
except ImportError:
    print("❌ demo_jwt_utils not found. Please ensure demo_jwt_utils.py is in the same directory.")
    exit(1)


class SimpleUserDemo:
    """Simple demo for user management service."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.demo_user_id = "simple_demo_user_123"
        # Generate valid JWT token for demo user
        self.auth_token = create_bearer_token(
            self.demo_user_id, 
            "simple.demo@example.com"
        )

    def print_banner(self, text: str, char: str = "="):
        """Print a banner."""
        print(f"\n{char * 60}")
        print(f" {text}")
        print(f"{char * 60}")

    def print_step(self, step: str):
        """Print a step."""
        print(f"\n🔸 {step}")

    def print_result(self, response, description: str = ""):
        """Print request result."""
        if response.status_code < 400:
            print(f"✅ {response.status_code} - {description}")
        else:
            print(f"❌ {response.status_code} - {description}")
        
        try:
            data = response.json()
            print(f"   📄 {json.dumps(data, indent=2)}")
        except:
            print(f"   📄 {response.text[:200]}...")

    async def run_demo(self):
        """Run the simple demo."""
        self.print_banner("Simple User Management Service Demo")
        
        print("This demo showcases core user management functionality:")
        print("• Health checks")
        print("• User profile management")
        print("• User preferences")
        print("• Integration listing")
        print("• OAuth flow initiation (without completion)")
        print(f"• Uses valid JWT tokens for authentication")
        
        async with httpx.AsyncClient() as client:
            # Health check
            self.print_step("Checking service health")
            try:
                response = await client.get(f"{self.base_url}/health")
                self.print_result(response, "Health check")
                
                if response.status_code != 200:
                    print("\n❌ Service is not healthy. Please start the service:")
                    print("   cd /path/to/briefly  # Navigate to project root")
                    print("   uvicorn services.user_management.main:app --reload --port 8000")
                    return False
            except Exception as e:
                print(f"❌ Cannot connect to service: {e}")
                print("\n💡 Please start the service first:")
                print("   cd /path/to/briefly  # Navigate to project root")
                print("   uvicorn services.user_management.main:app --reload --port 8000")
                return False

            # Readiness check
            self.print_step("Checking service readiness")
            try:
                response = await client.get(f"{self.base_url}/ready")
                self.print_result(response, "Readiness check")
            except Exception as e:
                print(f"❌ Readiness check failed: {e}")

            # Create demo user via webhook simulation
            self.print_step("Creating demo user (webhook simulation)")
            webhook_data = {
                "type": "user.created",
                "object": "event",  # Required by ClerkWebhookEvent schema
                "data": {
                    "id": self.demo_user_id,
                    "email_addresses": [{
                        "email_address": "simple.demo@example.com",
                        "verification": {"status": "verified"}
                    }],
                    "first_name": "Simple",
                    "last_name": "Demo",
                    "image_url": "https://images.clerk.dev/demo.png",  # Changed from profile_image_url
                    "created_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
            }

            try:
                response = await client.post(
                    f"{self.base_url}/webhooks/clerk",
                    json=webhook_data,
                    headers={
                        "Content-Type": "application/json",
                        "svix-id": "msg_simple_demo",
                        "svix-timestamp": str(int(time.time())),
                        "svix-signature": "v1,demo_signature_simple",
                    }
                )
                self.print_result(response, "User creation via webhook")
            except Exception as e:
                print(f"❌ User creation failed: {e}")

            # Get user profile
            self.print_step("Getting user profile")
            try:
                response = await client.get(
                    f"{self.base_url}/users/{self.demo_user_id}",
                    headers={"Authorization": self.auth_token}
                )
                self.print_result(response, "User profile retrieval")
            except Exception as e:
                print(f"❌ Profile retrieval failed: {e}")

            # Update user profile
            self.print_step("Updating user profile")
            update_data = {
                "bio": "This is a simple demo user!",
                "location": "Demo City",
                "website": "https://demo.example.com"
            }
            try:
                response = await client.put(
                    f"{self.base_url}/users/{self.demo_user_id}",
                    json=update_data,
                    headers={"Authorization": self.auth_token}
                )
                self.print_result(response, "User profile update")
            except Exception as e:
                print(f"❌ Profile update failed: {e}")

            # Get user preferences
            self.print_step("Getting user preferences")
            try:
                response = await client.get(
                    f"{self.base_url}/users/{self.demo_user_id}/preferences",
                    headers={"Authorization": self.auth_token}
                )
                self.print_result(response, "User preferences")
            except Exception as e:
                print(f"❌ Preferences retrieval failed: {e}")

            # Update user preferences
            self.print_step("Updating user preferences")
            prefs_data = {
                "ui_preferences": {
                    "theme": "dark",
                    "language": "en",
                    "timezone": "UTC"
                },
                "notification_preferences": {
                    "email_notifications": True,
                    "push_notifications": False
                }
            }
            try:
                response = await client.put(
                    f"{self.base_url}/users/{self.demo_user_id}/preferences",
                    json=prefs_data,
                    headers={"Authorization": self.auth_token}
                )
                self.print_result(response, "Preferences update")
            except Exception as e:
                print(f"❌ Preferences update failed: {e}")

            # List integrations
            self.print_step("Listing user integrations")
            try:
                response = await client.get(
                    f"{self.base_url}/users/{self.demo_user_id}/integrations",
                    headers={"Authorization": self.auth_token}
                )
                self.print_result(response, "Integration list")
            except Exception as e:
                print(f"❌ Integration listing failed: {e}")

            # OAuth flow demonstration (without completion)
            print("\n" + "🔗" * 30)
            print(" OAuth Flow Demo (Setup Only)")
            print("🔗" * 30)
            
            for provider in ["google", "microsoft"]:
                self.print_step(f"Starting {provider.title()} OAuth flow")
                try:
                    response = await client.post(
                        f"{self.base_url}/users/{self.demo_user_id}/integrations/{provider}/oauth/start",
                        json={
                            "redirect_uri": "http://localhost:8000/oauth/callback",
                            "scopes": ["read"]
                        },
                        headers={"Authorization": self.auth_token}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        auth_url = data.get("authorization_url", "N/A")
                        print(f"✅ OAuth flow setup successful")
                        print(f"   🌐 Authorization URL: {auth_url[:80]}...")
                        
                        # Ask if user wants to open browser
                        if auth_url != "N/A":
                            open_browser = input(f"\n   Open {provider.title()} OAuth in browser? (y/n): ").strip().lower()
                            if open_browser == 'y':
                                print(f"   🌐 Opening browser for {provider.title()}...")
                                webbrowser.open(auth_url)
                                print(f"   ⚠️  Note: OAuth completion requires valid credentials")
                    else:
                        self.print_result(response, f"{provider.title()} OAuth setup")
                        
                except Exception as e:
                    print(f"❌ {provider.title()} OAuth setup failed: {e}")

            # Internal API demo
            self.print_step("Testing internal service API")
            try:
                response = await client.post(
                    f"{self.base_url}/internal/tokens/get",
                    json={
                        "user_id": self.demo_user_id,
                        "provider": "google",
                        "scopes": ["read"]
                    },
                    headers={
                        "X-API-Key": "demo-service-key",
                        "X-Service-Name": "demo-service"
                    }
                )
                self.print_result(response, "Internal API token request")
            except Exception as e:
                print(f"❌ Internal API test failed: {e}")

            # API documentation
            self.print_step("Checking API documentation")
            try:
                response = await client.get(f"{self.base_url}/docs")
                if response.status_code == 200:
                    print("✅ API documentation available")
                    print(f"   🌐 Visit: {self.base_url}/docs")
                else:
                    print("❌ API documentation not available (may be disabled)")
            except Exception as e:
                print(f"❌ Documentation check failed: {e}")

        # Demo completion
        self.print_banner("Demo Completed! 🎉", "✨")
        print("What was demonstrated:")
        print("✅ Service health and readiness checks")
        print("✅ User creation via webhook")
        print("✅ User profile management")
        print("✅ User preferences management")
        print("✅ Integration listing")
        print("✅ OAuth flow initiation")
        print("✅ Internal service API")
        print("✅ Valid JWT token authentication")
        
        print(f"\n🌐 Explore more at: {self.base_url}/docs")
        print("📚 Full demo: python user_management_demo.py")
        
        return True


async def main():
    """Main function."""
    print("🚀 Simple User Management Service Demo")
    print("=====================================")
    
    # Check if service should be started
    start_service = input("\nIs the user management service running on http://localhost:8000? (y/n): ").strip().lower()
    if start_service == 'n':
        print("\n📋 To start the service:")
        print("   cd /path/to/briefly")
        print("   uvicorn services.user_management.main:app --reload --port 8000")
        print("\nPress Enter when ready...")
        input()

    demo = SimpleUserDemo()
    success = await demo.run_demo()
    
    if success:
        print("\n🎉 Demo completed successfully!")
    else:
        print("\n❌ Demo encountered issues.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        exit(1) 