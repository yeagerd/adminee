#!/usr/bin/env python3
"""
NextAuth Demo Utilities

Utility functions for testing NextAuth authentication flows with the chat.py demo.
This allows testing the proposed NextAuth approach alongside the existing Clerk setup.
"""

import asyncio
import os
import sys
import time
from typing import Dict, Optional

import httpx
import jwt

from services.common.logging_config import get_logger

logger = get_logger(__name__)


class NextAuthClient:
    """Client for interacting with NextAuth test server."""

    def __init__(self, base_url: str = "http://localhost:8090"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 30.0
        self.available = False
        self.jwt_token: Optional[str] = None
        self.user_data: Optional[Dict] = None

    async def health_check(self) -> bool:
        """Check if NextAuth test server is available."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/")
                self.available = response.status_code == 200
                if self.available:
                    data = response.json()
                    logger.info(f"NextAuth server available: {data.get('service')}")
                return self.available
        except Exception as e:
            logger.warning(f"NextAuth server not available: {e}")
            self.available = False
            return False

    async def start_oauth_flow(self, provider: str) -> Optional[str]:
        """Start OAuth flow with NextAuth server."""
        if not self.available:
            return None

        try:
            # Set up callback URL to point to NextAuth test server
            callback_url = f"{self.base_url}/auth/oauth/callback/{provider}"

            # Define provider-specific scopes
            if provider == "google":
                scopes = [
                    "openid",
                    "email",
                    "profile",
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/calendar",
                ]
            elif provider == "microsoft":
                scopes = [
                    "openid",
                    "email",
                    "profile",
                    "offline_access",
                    "https://graph.microsoft.com/User.Read",
                    "https://graph.microsoft.com/Calendars.ReadWrite",
                    "https://graph.microsoft.com/Mail.Read",
                ]
            else:
                scopes = ["openid", "email", "profile"]

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/auth/oauth/start",
                    json={
                        "provider": provider,
                        "redirect_uri": callback_url,
                        "scopes": scopes,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("authorization_url")
                else:
                    logger.error(
                        f"OAuth start failed: {response.status_code} {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"OAuth start error: {e}")
            return None

    async def verify_token(self, token: str) -> Optional[Dict]:
        """Verify NextAuth JWT token."""
        if not self.available:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/auth/verify", json={"token": token}
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Token verification failed: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None

    def set_token(self, token: str):
        """Set the JWT token for this client."""
        self.jwt_token = token

        # Decode token to extract user data (without verification for demo)
        try:
            # Decode without verification for demo purposes
            payload = jwt.decode(token, options={"verify_signature": False})
            self.user_data = {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "provider": payload.get("provider"),
            }
            logger.info(f"NextAuth token set for user: {self.user_data['email']}")
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")

    async def get_session(self) -> Optional[Dict]:
        """Get current session information."""
        if not self.available or not self.jwt_token:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/auth/session",
                    headers={"Authorization": f"Bearer {self.jwt_token}"},
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Session request failed: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Session request error: {e}")
            return None


async def test_nextauth_flow(provider: str = "google") -> Optional[str]:
    """
    Test NextAuth OAuth flow interactively.

    Args:
        provider: OAuth provider ("google" or "microsoft")

    Returns:
        JWT token if successful, None otherwise
    """
    print(f"\n🔵 Testing NextAuth OAuth Flow - {provider.title()}")
    print("=" * 50)

    # Initialize NextAuth client
    client = NextAuthClient()

    # Check if server is available
    print("🔍 Checking NextAuth test server...")
    available = await client.health_check()

    if not available:
        print("❌ NextAuth test server not available")
        print("   Start it with: python services/demos/nextauth_test_server.py")
        return None

    print("✅ NextAuth test server is available")

    # Start OAuth flow
    print(f"\n🚀 Starting {provider.title()} OAuth flow...")
    auth_url = await client.start_oauth_flow(provider)

    if not auth_url:
        print(f"❌ Failed to start {provider} OAuth flow")
        return None

    print("✅ OAuth flow started successfully")
    print(f"\n🔗 Please visit this URL to authenticate with {provider.title()}:")
    print(f"   {auth_url}")
    print()

    # After printing the OAuth URL and instructions...
    print("\nWhen you have completed the OAuth flow and copied your JWT token:")
    print(
        "Type 'vi' (or your preferred editor command) and press Enter to open the editor for pasting the token."
    )
    print(
        "Or just press Enter to paste the token directly into the terminal (Ctrl+D to finish).\n"
    )
    editor_choice = input("Editor command (default: vi): ").strip()
    if editor_choice:
        editor = editor_choice
    else:
        editor = os.environ.get("EDITOR", "vi")

    token = None
    if editor_choice:
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jwt", mode="r+", delete=False) as tf:
            temp_path = tf.name
        try:
            print(
                f"\n📝 Opening {editor}. Paste your NextAuth JWT token, save, and close the editor."
            )
            subprocess.call([editor, temp_path])
            with open(temp_path, "r") as tf:
                token = tf.read().strip()
            if not token:
                print("❌ No token entered in editor.")
                token = None
        finally:
            os.unlink(temp_path)

    if not token:
        print(
            "Paste your NextAuth JWT token below. Press Ctrl+D (Unix/macOS/Linux) or Ctrl+Z then Enter (Windows) when done:"
        )
        token = sys.stdin.read().strip()

    if token.lower() == "skip":
        print("⏭️  NextAuth test skipped")
        return None
    if not token:
        print("❌ Please enter a token or 'skip'")
        return None
    # Verify token
    print("🔍 Verifying token...")
    verification = await client.verify_token(token)
    if verification and verification.get("valid"):
        print("✅ Token verified successfully!")
        print(f"   User: {verification.get('email')}")
        print(f"   Provider: {verification.get('provider')}")
        # Set token in client
        client.set_token(token)
        # Test session
        session = await client.get_session()
        if session:
            print("✅ Session retrieved successfully!")
            print(
                f"   Access Token: {'✅ Available' if session.get('access_token') else '❌ Not available'}"
            )
            print(
                f"   Refresh Token: {'✅ Available' if session.get('refresh_token') else '❌ Not available'}"
            )
        return token
    else:
        error = (
            verification.get("error", "Unknown error")
            if verification
            else "Verification failed"
        )
        print(f"❌ Token verification failed: {error}")
        print("   Please try again or type 'skip' to cancel")
        return None


def create_nextauth_jwt_for_demo(user_id: str, email: str, provider: str) -> str:
    """
    Create a demo NextAuth JWT token for testing purposes.

    Args:
        user_id: User ID
        email: User email
        provider: OAuth provider

    Returns:
        NextAuth-style JWT token
    """
    now = int(time.time())
    expires = now + 3600  # 1 hour

    payload = {
        "sub": user_id,
        "email": email,
        "name": email.split("@")[0].title(),
        "provider": provider,
        "iat": now,
        "exp": expires,
        "iss": "nextauth-demo",
        "aud": "briefly-demo",
    }

    # Use demo secret (matches NextAuth test server)
    secret = os.getenv("NEXTAUTH_SECRET", "demo-nextauth-secret")

    return jwt.encode(payload, secret, algorithm="HS256")


def compare_auth_approaches(
    clerk_token: Optional[str], nextauth_token: Optional[str]
) -> None:
    """
    Compare Clerk and NextAuth tokens side by side.

    Args:
        clerk_token: Clerk JWT token
        nextauth_token: NextAuth JWT token
    """
    print("\n🔍 Authentication Approach Comparison")
    print("=" * 60)

    def decode_token_safely(token: str, name: str) -> Dict:
        """Safely decode a token for comparison."""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            return {"error": f"Failed to decode {name} token: {e}"}

    # Decode both tokens
    clerk_data = (
        decode_token_safely(clerk_token, "Clerk")
        if clerk_token
        else {"error": "No Clerk token"}
    )
    nextauth_data = (
        decode_token_safely(nextauth_token, "NextAuth")
        if nextauth_token
        else {"error": "No NextAuth token"}
    )

    # Compare key fields
    fields_to_compare = [
        ("User ID", "sub"),
        ("Email", "email"),
        ("Name", "name"),
        ("Provider", "provider"),
        ("Issued At", "iat"),
        ("Expires", "exp"),
        ("Issuer", "iss"),
        ("Access Token", "access_token"),
        ("Refresh Token", "refresh_token"),
    ]

    print(f"{'Field':<15} {'Clerk':<30} {'NextAuth':<30}")
    print("-" * 75)

    for field_name, field_key in fields_to_compare:
        clerk_value = clerk_data.get(field_key, "N/A")
        nextauth_value = nextauth_data.get(field_key, "N/A")

        # Format timestamps
        if field_key in ["iat", "exp"] and isinstance(clerk_value, (int, float)):
            clerk_value = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(clerk_value)
            )
        if field_key in ["iat", "exp"] and isinstance(nextauth_value, (int, float)):
            nextauth_value = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(nextauth_value)
            )

        # Truncate long values
        clerk_str = (
            str(clerk_value)[:28] + "..."
            if len(str(clerk_value)) > 28
            else str(clerk_value)
        )
        nextauth_str = (
            str(nextauth_value)[:28] + "..."
            if len(str(nextauth_value)) > 28
            else str(nextauth_value)
        )

        print(f"{field_name:<15} {clerk_str:<30} {nextauth_str:<30}")

    print()

    # Analysis
    print("🔍 Key Differences:")
    if nextauth_data.get("access_token") and not clerk_data.get("access_token"):
        print("  • NextAuth includes OAuth access tokens directly in JWT")
    if nextauth_data.get("provider") and not clerk_data.get("provider"):
        print("  • NextAuth includes OAuth provider information")
    if clerk_data.get("iss", "").find("clerk") != -1:
        print("  • Clerk tokens are issued by Clerk service")
    if nextauth_data.get("iss", "").find("nextauth") != -1:
        print("  • NextAuth tokens are self-issued")

    print("\n💡 Architectural Implications:")
    print("  • Clerk: Separate auth + OAuth setup required")
    print("  • NextAuth: Combined auth + OAuth in single flow")
    print("  • Clerk: External dependency on Clerk service")
    print("  • NextAuth: Self-contained authentication system")


async def demonstrate_nextauth_integration() -> Optional[str]:
    """
    Demonstrate how NextAuth would integrate with Briefly services.
    """
    print("\n🚀 NextAuth Integration Demonstration")
    print("=" * 50)

    print("This demonstrates how NextAuth would work with Briefly:")
    print()
    print("1. 🔐 User visits Briefly app")
    print("2. 🔵 Clicks 'Sign in with Google' or 'Sign in with Microsoft'")
    print("3. 🌐 Redirected to Google/Microsoft OAuth")
    print("4. ✅ After approval, returns with NextAuth JWT containing:")
    print("   • User identity (email, name)")
    print("   • OAuth access tokens for calendar/email")
    print("   • Provider information")
    print("5. 🎯 Frontend uses JWT for all API calls")
    print("6. 🏗️  Backend validates JWT and extracts user info")
    print("7. 📧 Services use embedded OAuth tokens for calendar/email access")
    print()
    print("🎉 Result: Single login gives both app access AND data access!")
    print()

    # Test the flow
    provider = (
        input("Test OAuth flow? Enter 'google', 'microsoft', or 'skip': ")
        .strip()
        .lower()
    )

    if provider in ["google", "microsoft"]:
        token = await test_nextauth_flow(provider)
        if token:
            print("\n✅ NextAuth flow completed successfully!")
            print("This token would be used for all Briefly API calls.")
            return token

    print("Demo completed.")
    return None


if __name__ == "__main__":
    """Run NextAuth demonstration."""
    asyncio.run(demonstrate_nextauth_integration())
