#!/usr/bin/env python3
"""
Enhanced Briefly Demo with NextAuth Testing

This demo extends the existing chat.py demo to include NextAuth testing capabilities.
You can now test both Clerk and NextAuth authentication approaches side by side.

Features:
- All existing chat.py functionality
- NextAuth OAuth flow testing
- Side-by-side authentication comparison
- Real Google/Microsoft OAuth integration testing

Commands (interactive mode):
  All existing chat.py commands plus:
  nextauth <provider>     Test NextAuth OAuth flow (google/microsoft)
  compare                 Compare Clerk vs NextAuth tokens
  demo-nextauth          Run NextAuth integration demonstration

Usage:
    python services/demos/chat_nextauth.py                    # Enhanced demo with NextAuth support
    python services/demos/chat_nextauth.py --nextauth-only    # NextAuth testing only
    python services/demos/chat_nextauth.py --compare          # Run comparison demo

Environment Variables:
    All existing chat.py environment variables plus:
    GOOGLE_CLIENT_ID        Google OAuth client ID
    GOOGLE_CLIENT_SECRET    Google OAuth client secret
    MICROSOFT_CLIENT_ID     Microsoft OAuth client ID
    MICROSOFT_CLIENT_SECRET Microsoft OAuth client secret
    NEXTAUTH_SECRET         NextAuth JWT secret
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the base demo functionality
from services.demos.chat import FullDemo, DEFAULT_USER_ID, logger

# Import NextAuth utilities
try:
    from services.demos.nextauth_demo_utils import (
        NextAuthClient,
        test_nextauth_flow,
        create_nextauth_jwt_for_demo,
        compare_auth_approaches,
        demonstrate_nextauth_integration,
    )
    NEXTAUTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"NextAuth utilities not available: {e}")
    NEXTAUTH_AVAILABLE = False


class EnhancedDemo(FullDemo):
    """Enhanced demo with NextAuth testing capabilities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # NextAuth client
        self.nextauth_client: Optional[NextAuthClient] = None
        self.nextauth_token: Optional[str] = None
        
        # Track available authentication methods
        self.auth_methods = {
            "clerk": True,  # Always available in base demo
            "nextauth": NEXTAUTH_AVAILABLE,
        }

    async def check_services(self):
        """Enhanced service checking including NextAuth server."""
        # Call parent method
        await super().check_services()
        
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

    def show_welcome(self):
        """Enhanced welcome message with NextAuth information."""
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
        """Enhanced help with NextAuth commands."""
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

    async def handle_nextauth_command(self, provider: str) -> str:
        """Handle NextAuth testing command."""
        if not NEXTAUTH_AVAILABLE:
            return "❌ NextAuth utilities not available"

        if not self.auth_methods.get("nextauth"):
            return "❌ NextAuth test server not available. Start with: python services/demos/nextauth_test_server.py"

        if provider not in ["google", "microsoft"]:
            return "❌ Supported providers: google, microsoft"

        print(f"\n🔵 Testing NextAuth OAuth Flow - {provider.title()}")
        print("=" * 50)

        token = await test_nextauth_flow(provider)
        if token:
            self.nextauth_token = token
            return f"✅ NextAuth {provider} authentication successful!"
        else:
            return f"❌ NextAuth {provider} authentication failed"

    async def handle_compare_command(self) -> str:
        """Handle authentication comparison command."""
        if not NEXTAUTH_AVAILABLE:
            return "❌ NextAuth utilities not available for comparison"

        clerk_token = getattr(self.user_client, 'auth_token', None)
        if clerk_token and clerk_token.startswith("Bearer "):
            clerk_token = clerk_token[7:]  # Remove "Bearer " prefix

        if not clerk_token and not self.nextauth_token:
            return "❌ No authentication tokens available for comparison. Try 'auth' and 'nextauth google' first."

        compare_auth_approaches(clerk_token, self.nextauth_token)
        return "✅ Authentication comparison completed"

    async def chat_loop(self):
        """Enhanced chat loop with NextAuth commands."""
        if not self.use_api:
            self.agent = await self.create_agent()

        while True:
            try:
                # Show prompt with authentication status
                auth_status = ""
                if hasattr(self.user_client, 'auth_token') and self.user_client.auth_token:
                    auth_status += "🔑"
                if self.nextauth_token:
                    auth_status += "🔵"

                thread_info = (
                    f" (thread: {self.active_thread})" if self.active_thread else ""
                )
                prompt = f"💬 {auth_status}{self.user_id}{thread_info}: "
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # Handle exit commands
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Thanks for using Enhanced Briefly! Goodbye!")
                    break

                # Handle NextAuth commands
                elif user_input.lower().startswith("nextauth"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        print("🔵 Usage: nextauth <provider>")
                        print("   Available providers: google, microsoft")
                        continue

                    provider = parts[1].lower()
                    response = await self.handle_nextauth_command(provider)
                    print(f"🔵 {response}")
                    continue

                elif user_input.lower() == "compare":
                    response = await self.handle_compare_command()
                    print(response)
                    continue

                elif user_input.lower() == "demo-nextauth":
                    if NEXTAUTH_AVAILABLE:
                        token = await demonstrate_nextauth_integration()
                        if token:
                            self.nextauth_token = token
                            print("✅ NextAuth demonstration completed successfully!")
                        else:
                            print("✅ NextAuth demonstration completed")
                    else:
                        print("❌ NextAuth utilities not available")
                    continue

                # Handle all other commands from parent class
                elif user_input.lower() == "help":
                    self.show_help()
                    continue

                elif user_input.lower() == "clear":
                    if not self.use_api and self.agent:
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

                elif user_input.lower().startswith("auth"):
                    parts = user_input.split(maxsplit=1)
                    email = parts[1] if len(parts) > 1 else None
                    response = await self.handle_auth_command(email)
                    print(f"🔐 {response}")
                    continue

                elif user_input.lower().startswith("oauth"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        print("🔗 Usage: oauth <provider>")
                        print("   Available providers: google, microsoft")
                        continue

                    provider = parts[1].lower()
                    if provider not in ["google", "microsoft"]:
                        print("🔗 Available providers: google, microsoft")
                        continue

                    if not self.services_available["user"]:
                        print("❌ User service unavailable for OAuth setup")
                        continue

                    success = await self.setup_oauth_integration(provider)
                    if success:
                        print(f"✅ Clerk OAuth setup completed for {provider}")
                    else:
                        print(f"❌ Clerk OAuth setup failed for {provider}")
                    continue

                elif user_input.lower().startswith("timezone"):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) < 2:
                        print(
                            "🌍 Usage: timezone <timezone> (e.g., timezone America/New_York)"
                        )
                        continue

                    timezone = parts[1]
                    response = await self.handle_timezone_command(timezone)
                    print(response)
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


async def main():
    """Run the enhanced demo with NextAuth testing."""
    parser = argparse.ArgumentParser(
        description="Enhanced Briefly Demo with NextAuth Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python services/demos/chat_nextauth.py                    # Enhanced demo with both auth methods
  python services/demos/chat_nextauth.py --nextauth-only    # NextAuth testing only
  python services/demos/chat_nextauth.py --compare          # Run comparison demo
  python services/demos/chat_nextauth.py --local            # Local multi-agent mode
        """,
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local multi-agent mode instead of API mode",
    )

    parser.add_argument(
        "--nextauth-only",
        action="store_true",
        help="Run NextAuth demonstration only (skip Clerk setup)",
    )

    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run authentication comparison demonstration",
    )

    parser.add_argument(
        "--chat-url",
        type=str,
        default="http://localhost:8002",
        help="Chat service URL",
    )

    parser.add_argument(
        "--office-url",
        type=str,
        default="http://localhost:8003",
        help="Office service URL",
    )

    parser.add_argument(
        "--user-url",
        type=str,
        default="http://localhost:8001",
        help="User service URL",
    )

    parser.add_argument(
        "--user-id",
        type=str,
        default="demo_user",
        help="User ID",
    )

    parser.add_argument(
        "--message",
        "-m",
        type=str,
        help="Send a single message (non-interactive mode)",
    )

    args = parser.parse_args()

    # Handle special modes
    if args.nextauth_only:
        if NEXTAUTH_AVAILABLE:
            await demonstrate_nextauth_integration()
        else:
            print("❌ NextAuth utilities not available")
        return

    if args.compare:
        print("🔍 Authentication Comparison Demo")
        print("=" * 40)
        print("This demo will help you compare Clerk vs NextAuth authentication.")
        print()
        
        # Create demo tokens for comparison
        clerk_token = None
        nextauth_token = None
        
        if NEXTAUTH_AVAILABLE:
            print("Creating demo tokens for comparison...")
            nextauth_token = create_nextauth_jwt_for_demo("demo123", "demo@example.com", "google")
            print("✅ Demo tokens created")
            
            compare_auth_approaches(clerk_token, nextauth_token)
        else:
            print("❌ NextAuth utilities not available for comparison")
        return

    # Create enhanced demo instance
    demo = EnhancedDemo(
        use_api=not args.local,
        chat_url=args.chat_url,
        office_url=args.office_url,
        user_url=args.user_url,
        user_id=args.user_id,
        skip_auth=args.nextauth_only,  # Skip Clerk auth if NextAuth only
    )

    try:
        # Check service availability (including NextAuth)
        await demo.check_services()

        # Set up Clerk authentication (unless NextAuth only)
        if not args.nextauth_only:
            await demo.authenticate()

        # Load timezone preferences
        await demo.load_user_timezone()

        # Show welcome
        demo.show_welcome()

        if args.message:
            # Single message mode
            response = await demo.send_message(args.message)
            print(f"🤖 Briefly: {response}")
        else:
            # Interactive mode
            await demo.chat_loop()

    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 