#!/usr/bin/env python3
"""
Interactive Multi-Agent Chat Demo for WorkflowAgent.

This script provides a command-line interface to chat with the WorkflowAgent
multi-agent system. Features specialized agents for calendar, email, documents, and drafting.

Usage:
    python services/demos/chat_simple.py                    # Interactive mode
    python services/demos/chat_simple.py --streaming        # Streaming demo
    python services/demos/chat_simple.py --message "hi"     # Send single message
    python services/demos/chat_simple.py -m "What meetings do I have today?"
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from typing import Optional

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.chat.agents.workflow_agent import WorkflowAgent

# Configure logging (verbose for debugging)
logging.basicConfig(
    level=logging.DEBUG,  # Show all logs including debug
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Set specific loggers to be more verbose for our services
logging.getLogger("services.chat.agents.workflow_agent").setLevel(logging.DEBUG)
logging.getLogger("services.chat.agents.coordinator_agent").setLevel(logging.DEBUG)
logging.getLogger("services.chat.agents.calendar_agent").setLevel(logging.DEBUG)
logging.getLogger("services.chat.agents.email_agent").setLevel(logging.DEBUG)
logging.getLogger("services.chat.agents.document_agent").setLevel(logging.DEBUG)
logging.getLogger("services.chat.agents.draft_agent").setLevel(logging.DEBUG)
logging.getLogger("llama_index").setLevel(logging.INFO)  # LlamaIndex logs at INFO level

# Suppress spammy database and library logs
logging.getLogger("aiosqlite").setLevel(
    logging.WARNING
)  # Only show warnings/errors from aiosqlite
logging.getLogger("asyncio").setLevel(
    logging.WARNING
)  # Only show warnings/errors from asyncio
logging.getLogger("LiteLLM").setLevel(
    logging.WARNING
)  # Only show warnings/errors from LiteLLM


class ChatDemo:
    """Interactive multi-agent chat demo for WorkflowAgent."""

    def __init__(self):
        self.agent: Optional[WorkflowAgent] = None
        # Generate a new thread ID based on current timestamp to ensure each session is unique
        self.thread_id = int(time.time())
        self.user_id = "demo_user"

    async def create_agent(self) -> WorkflowAgent:
        """Create and initialize a multi-agent WorkflowAgent."""
        print("\n🤖 Creating Multi-Agent WorkflowAgent...")

        agent = WorkflowAgent(
            thread_id=self.thread_id,
            user_id=self.user_id,
            llm_model="gpt-3.5-turbo",  # You can change this to your preferred model
            llm_provider="openai",
            max_tokens=2000,
            office_service_url="http://localhost:8001",
        )

        # Build the agent (this initializes the workflow)
        await agent.build_agent("Hello, I'm ready to help!")

        print(
            f"✅ Multi-Agent system ready with {len(agent.specialized_agents)} specialized agents:"
        )
        for agent_name in agent.specialized_agents.keys():
            print(f"   • {agent_name}")

        return agent

    def show_welcome(self):
        """Show welcome message and instructions."""
        print("=" * 60)
        print("🚀 Welcome to the Multi-Agent WorkflowAgent Demo!")
        print("=" * 60)
        print(f"📝 Starting new conversation thread: {self.thread_id}")
        print()
        print("This demo lets you chat with the multi-agent WorkflowAgent system.")
        print("Features specialized agents for different tasks:")
        print("  • CoordinatorAgent - Orchestrates and delegates tasks")
        print("  • CalendarAgent - Manages calendar and scheduling")
        print("  • EmailAgent - Handles email operations")
        print("  • DocumentAgent - Manages documents and notes")
        print("  • DraftAgent - Creates drafts and content")
        print()
        print("📋 Example prompts to try:")
        print("  • 'What meetings do I have this week?'")
        print("  • 'Show me my unread emails'")
        print("  • 'Find my notes about the project'")
        print("  • 'Draft an email to the team about the meeting'")
        print("  • 'Help me prepare for tomorrow's board meeting'")
        print()
        print("💡 Commands:")
        print("  • 'quit' or 'exit' - Exit the demo")
        print("  • 'help' - Show this help message")
        print("  • 'clear' - Clear the conversation history")
        print()

    def show_help(self):
        """Show help message."""
        print("\n📋 Available Commands:")
        print("  • Type any message to chat with the multi-agent system")
        print("  • 'quit' or 'exit' - Exit the demo")
        print("  • 'help' - Show this help message")
        print("  • 'clear' - Clear the conversation history")
        print()
        print("🤖 Specialized Agents:")
        print("  • CoordinatorAgent - Orchestrates tasks and delegates to other agents")
        print("  • CalendarAgent - Handles calendar queries and scheduling")
        print("  • EmailAgent - Manages email operations and searches")
        print("  • DocumentAgent - Finds and manages documents and notes")
        print("  • DraftAgent - Creates drafts of emails and content")
        print()
        print("📋 Example prompts:")
        print("  • 'What meetings do I have this week?'")
        print("  • 'Show me my unread emails from today'")
        print("  • 'Find my notes about the quarterly planning'")
        print("  • 'Draft an email to john@example.com about the project'")
        print("  • 'Help me organize my calendar for tomorrow'")
        print()

    async def clear_history(self):
        """Clear the conversation history by creating a new agent."""
        if self.agent is None:
            return

        print("\n🧹 Clearing conversation history...")

        # Generate a new thread ID to start fresh
        old_thread_id = self.thread_id
        self.thread_id = int(time.time())
        print(f"📝 New conversation thread: {self.thread_id} (was: {old_thread_id})")
        self.agent = await self.create_agent()

    async def send_message(self, message: str):
        """Send a single message and return the response (non-interactive mode)."""
        # Create the multi-agent system if not already created
        if self.agent is None:
            print("\n🤖 Creating Multi-Agent WorkflowAgent...")
            self.agent = await self.create_agent()
            print("✅ Multi-Agent system ready!")

        print(f"\nYou: {message}")
        print("🤖 Briefly:", end=" ", flush=True)

        try:
            # Get response from the agent (backend logs will show details)
            response = await self.agent.chat(message)
            print(response)
            return response

        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            print(error_msg)
            logger.error(f"Chat error: {e}")
            import traceback

            traceback.print_exc()
            return error_msg

    async def chat_loop(self):
        """Main chat loop."""
        self.show_welcome()

        # Create the multi-agent system
        self.agent = await self.create_agent()

        print("\n💬 Multi-Agent chat started!")
        print("Type 'help' for commands or start chatting!\n")

        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                # Handle empty input
                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Thanks for using the WorkflowAgent demo! Goodbye!")
                    break

                elif user_input.lower() == "help":
                    self.show_help()
                    continue

                elif user_input.lower() == "clear":
                    await self.clear_history()
                    print("💬 History cleared. Continue chatting!\n")
                    continue

                # Process the chat message
                print("🤖 Briefly:", end=" ", flush=True)

                try:
                    # Get response from the agent (backend logs will show details)
                    response = await self.agent.chat(user_input)
                    print(response)

                except Exception as e:
                    print(f"Sorry, I encountered an error: {str(e)}")
                    logger.error(f"Chat error: {e}")
                    import traceback

                    traceback.print_exc()

                print()  # Add a blank line for readability

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break

            except Exception as e:
                print(f"\n❌ An error occurred: {str(e)}")
                logger.error(f"Demo error: {e}")
                print("Type 'quit' to exit or continue chatting.\n")

    async def run_streaming_demo(self):
        """Demo streaming chat (shows how responses are generated in real-time)."""
        print("\n🌊 Multi-Agent Streaming Demo")
        print(
            "This shows how the multi-agent system generates responses in real-time.\n"
        )

        self.agent = await self.create_agent()

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input or user_input.lower() in ["quit", "exit"]:
                    break

                print("🤖 Briefly: ", end="", flush=True)

                # Stream the response
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


async def main():
    """Run the chat demo with command line argument support."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent WorkflowAgent Chat Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python services/demos/chat_simple.py                    # Interactive mode
  python services/demos/chat_simple.py --streaming        # Streaming demo
  python services/demos/chat_simple.py --message "hi"     # Send single message
  python services/demos/chat_simple.py -m "What meetings do I have today?"
        """,
    )

    parser.add_argument(
        "--message", "-m", type=str, help="Send a single message (non-interactive mode)"
    )

    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Run streaming demo instead of regular chat",
    )

    args = parser.parse_args()

    demo = ChatDemo()

    if args.message:
        # Non-interactive mode: send single message
        await demo.send_message(args.message)
    elif args.streaming:
        # Streaming demo mode
        await demo.run_streaming_demo()
    else:
        # Interactive chat mode
        await demo.chat_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Demo failed to start: {e}")
        sys.exit(1)
