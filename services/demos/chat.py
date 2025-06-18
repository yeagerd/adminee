#!/usr/bin/env python3
"""
Interactive chat demo with multi-agent WorkflowAgent and API support.

This script provides two modes:
1. Direct multi-agent mode (default): Chat directly with WorkflowAgent multi-agent system
2. API mode (--api): Chat through the chat service API

Commands (interactive mode):
  help                Show this help message.
  list                List all threads for the user (API mode only).
  new                 Start a new thread.
  switch <thread_id>  Switch to an existing thread (API mode only).
  clear               Clear conversation history.
  exit                Exit the chat.

Type any other text to send as a message.

Usage:
    python services/demos/chat.py                           # Direct multi-agent mode
    python services/demos/chat.py --api                     # API mode
    python services/demos/chat.py --streaming               # Direct streaming demo
    python services/demos/chat.py --message "hi"            # Send single message (direct mode)
    python services/demos/chat.py --api --message "hi"      # Send single message (API mode)
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

import httpx
import requests

# Set environment variables to disable cost tracking
os.environ["LITELLM_LOG"] = "WARNING"  # Set LiteLLM log level to WARNING
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "False")  # Disable local cost map

from services.chat.agents.workflow_agent import WorkflowAgent
from services.chat.models import ChatResponse

# Configure logging (clean for demo use)
logging.basicConfig(
    level=logging.INFO,  # Show info and above
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Set specific loggers for multi-agent workflow visibility
logging.getLogger("services.chat.agents.workflow_agent").setLevel(logging.INFO)
logging.getLogger("services.chat.agents.coordinator_agent").setLevel(logging.INFO)
logging.getLogger("services.chat.agents.calendar_agent").setLevel(logging.INFO)
logging.getLogger("services.chat.agents.email_agent").setLevel(logging.INFO)
logging.getLogger("services.chat.agents.document_agent").setLevel(logging.INFO)
logging.getLogger("services.chat.agents.draft_agent").setLevel(logging.INFO)

# Suppress noisy loggers
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Hide HTTP request logs
logging.getLogger("openai._base_client").setLevel(
    logging.WARNING
)  # Hide OpenAI client logs
logging.getLogger("llama_index").setLevel(logging.WARNING)  # Reduce LlamaIndex noise
logging.getLogger("LiteLLM").setLevel(
    logging.WARNING
)  # Only show warnings/errors from LiteLLM
# Suppress cost calculation and model selection messages
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("litellm.cost_calculator").setLevel(logging.ERROR)
logging.getLogger("litellm.utils").setLevel(logging.WARNING)
# Additional suppression based on GitHub issue #9815
logging.getLogger("litellm.cost_calculation").setLevel(logging.ERROR)
logging.getLogger("litellm._logging").setLevel(logging.WARNING)


def print_help():
    print(__doc__)


def actor(message):
    """
    Returns a string indicating the actor of the message.
    """
    return "briefly" if message.llm_generated else message.user_id


class ChatDemo:
    """Interactive chat demo supporting both direct multi-agent and API modes."""

    def __init__(self, use_api: bool, chat_url: str, user_id: str = "demo_user"):
        self.use_api = use_api
        self.chat_url = chat_url.rstrip("/")
        self.user_id = user_id
        self.agent: Optional[WorkflowAgent] = None
        # Generate a new thread ID based on current timestamp to ensure each session is unique
        self.thread_id = int(time.time())
        self.active_thread = None  # For API mode

    async def create_agent(self) -> WorkflowAgent:
        """Create and initialize a multi-agent WorkflowAgent (direct mode only)."""
        if self.use_api:
            return None

        print("\n🤖 Creating Multi-Agent WorkflowAgent...")

        agent = WorkflowAgent(
            thread_id=self.thread_id,
            user_id=self.user_id,
            llm_model="gpt-4.1-nano",  # You can change this to your preferred model
            llm_provider="openai",
            max_tokens=2000,
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
        if self.use_api:
            print("🚀 Welcome to the Chat Service API Demo!")
        else:
            print("🚀 Welcome to the Multi-Agent WorkflowAgent Demo!")
        print("=" * 60)

        if self.use_api:
            print(f"🌐 API URL: {self.chat_url}")
            print(f"👤 User ID: {self.user_id}")
        else:
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
        print("  • 'Create a calendar event at 8am tomorrow with Bob'")
        print()
        print("💡 Commands:")
        print("  • 'quit' or 'exit' - Exit the demo")
        print("  • 'help' - Show this help message")
        if self.use_api:
            print("  • 'list' - List all threads")
            print("  • 'new' - Start a new thread")
            print("  • 'switch <thread_id>' - Switch to existing thread")
        else:
            print("  • 'clear' - Clear the conversation history")
        print()

    def show_help(self):
        """Show help message."""
        print("\n📋 Available Commands:")
        print("  • Type any message to chat with the system")
        print("  • 'quit' or 'exit' - Exit the demo")
        print("  • 'help' - Show this help message")

        if self.use_api:
            print("  • 'list' - List all threads for the user")
            print("  • 'new' - Start a new thread")
            print("  • 'switch <thread_id>' - Switch to an existing thread")
        else:
            print("  • 'clear' - Clear the conversation history")
            print()
            print("🤖 Specialized Agents:")
            print(
                "  • CoordinatorAgent - Orchestrates tasks and delegates to other agents"
            )
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
        print("  • 'Create a calendar event for tomorrow at 2pm'")
        print()

    async def clear_history(self):
        """Clear the conversation history."""
        if self.use_api:
            self.active_thread = None
            print("\n🧹 Starting new thread. Next message will create it.")
        else:
            if self.agent is None:
                return

            print("\n🧹 Clearing conversation history...")

            # Generate a new thread ID to start fresh
            old_thread_id = self.thread_id
            self.thread_id = int(time.time())
            print(
                f"📝 New conversation thread: {self.thread_id} (was: {old_thread_id})"
            )
            self.agent = await self.create_agent()

    async def send_message_direct(self, message: str):
        """Send a message using direct multi-agent workflow."""
        # Create the multi-agent system if not already created
        if self.agent is None:
            self.agent = await self.create_agent()

        try:
            # Get response from the agent (backend logs will show details)
            response = await self.agent.chat(message)

            # Get structured draft data and render as text for the demo
            draft_data = await self.agent.get_draft_data()
            if draft_data:
                draft_text = self._render_drafts_as_text(draft_data)
                response += f"\n\n{draft_text}"

            return response

        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            logger.error(f"Chat error: {e}")
            import traceback

            traceback.print_exc()
            return error_msg

    def _render_drafts_as_text(self, drafts):
        """Render structured draft data as text for the demo."""
        if not drafts:
            return ""

        lines = ["📋 **Drafts Created:**"]

        for draft in drafts:
            draft_type = draft.get("type", "unknown")

            if draft_type == "email":
                title = "Email Draft"
                details = []
                if draft.get("to"):
                    details.append(f"To: {draft['to']}")
                if draft.get("cc"):
                    details.append(f"CC: {draft['cc']}")
                if draft.get("subject"):
                    details.append(f"Subject: {draft['subject']}")
                if draft.get("body"):
                    body_preview = (
                        draft["body"][:100] + "..."
                        if len(draft["body"]) > 100
                        else draft["body"]
                    )
                    details.append(f"Body: {body_preview}")
                lines.append(
                    f"• {title}: {', '.join(details) if details else 'Created'}"
                )

            elif draft_type == "calendar_event":
                title = "Calendar Event Draft"
                details = []
                if draft.get("title"):
                    details.append(f"Title: {draft['title']}")
                if draft.get("start_time"):
                    details.append(f"Start: {draft['start_time']}")
                if draft.get("end_time"):
                    details.append(f"End: {draft['end_time']}")
                if draft.get("location"):
                    details.append(f"Location: {draft['location']}")
                lines.append(
                    f"• {title}: {', '.join(details) if details else 'Created'}"
                )

            elif draft_type == "calendar_change":
                title = "Calendar Change Draft"
                details = []
                if draft.get("event_id"):
                    details.append(f"Event ID: {draft['event_id']}")
                if draft.get("change_type"):
                    details.append(f"Change: {draft['change_type']}")
                if draft.get("new_title"):
                    details.append(f"New Title: {draft['new_title']}")
                if draft.get("new_start_time"):
                    details.append(f"New Start: {draft['new_start_time']}")
                lines.append(
                    f"• {title}: {', '.join(details) if details else 'Created'}"
                )

            else:
                lines.append(f"• {draft_type.replace('_', ' ').title()}: Created")

        return "\n".join(lines)

    def send_message_api(self, message: str):
        """Send a message using the chat service API."""
        payload = {"user_id": self.user_id, "message": message}
        if self.active_thread:
            payload["thread_id"] = self.active_thread

        try:
            resp = requests.post(f"{self.chat_url}/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            chat_resp = ChatResponse.model_validate(data)
            self.active_thread = chat_resp.thread_id

            # Extract the latest response
            messages = chat_resp.messages or []
            if messages:
                latest_message = messages[-1]
                response = latest_message.content

                # Render structured draft data as text for the demo
                if chat_resp.drafts:
                    draft_text = self._render_drafts_as_text(
                        [draft.model_dump() for draft in chat_resp.drafts]
                    )
                    response += f"\n\n{draft_text}"

                return response
            else:
                return "No response received."

        except requests.RequestException as e:
            return f"Error sending message: {e}"

    async def send_message(self, message: str):
        """Send a single message and return the response (non-interactive mode)."""
        if self.use_api:
            response = self.send_message_api(message)
        else:
            response = await self.send_message_direct(message)

        print(f"\nYou: {message}")
        print(f"🤖 Briefly: {response}")
        return response

    def handle_api_commands(self, line: str) -> bool:
        """Handle API-specific commands. Returns True if command was handled."""
        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "list":
            try:
                resp = requests.get(
                    f"{self.chat_url}/threads", params={"user_id": self.user_id}
                )
                resp.raise_for_status()
                threads = resp.json()
                if not threads:
                    print("No threads found.")
                else:
                    for t in threads:
                        print(
                            f"{t['thread_id']}\t(created: {t['created_at']}, updated: {t['updated_at']})"
                        )
            except requests.RequestException as e:
                print(f"Error listing threads: {e}")
            return True

        elif cmd == "new":
            self.active_thread = None
            print("New thread started. Next message will create it.")
            return True

        elif cmd == "switch":
            if len(parts) < 2:
                print("Usage: switch <thread_id>")
            else:
                thread_id = parts[1]
                try:
                    resp = requests.get(f"{self.chat_url}/threads/{thread_id}/history")
                    resp.raise_for_status()
                    self.active_thread = thread_id
                    data = resp.json()
                    chat_resp = ChatResponse.model_validate(data)
                    messages = chat_resp.messages or []
                    print(f"Switched to thread {thread_id}.")
                    if not messages:
                        print("No messages in this thread.")
                    else:
                        for m in messages:
                            uid = actor(m)
                            content = m.content
                            print(f"{uid}: {content}")
                except requests.RequestException as e:
                    print(f"Error switching thread: {e}")
            return True

        return False

    async def chat_loop(self):
        """Main chat loop."""
        self.show_welcome()

        # Create the multi-agent system for direct mode
        if not self.use_api:
            self.agent = await self.create_agent()

        mode_text = "API" if self.use_api else "Multi-Agent"
        print(f"\n💬 {mode_text} chat started!")
        print("Type 'help' for commands or start chatting!\n")

        while True:
            try:
                # Get user input
                if self.use_api and self.active_thread:
                    prompt = f"[{self.active_thread}]> "
                else:
                    prompt = "You: "

                user_input = input(prompt).strip()

                # Handle empty input
                if not user_input:
                    continue

                # Handle common commands
                if user_input.lower() in ["quit", "exit", "q"]:
                    print(f"\n👋 Thanks for using the {mode_text} demo! Goodbye!")
                    break

                elif user_input.lower() == "help":
                    self.show_help()
                    continue

                elif user_input.lower() == "clear":
                    await self.clear_history()
                    print("💬 History cleared. Continue chatting!\n")
                    continue

                # Handle API-specific commands
                if self.use_api and self.handle_api_commands(user_input):
                    continue

                # Process the chat message
                if not self.use_api:
                    print("🤖 Briefly:", end=" ", flush=True)

                try:
                    if self.use_api:
                        # Erase the previous input line (prompt + user input)
                        print("\033[F\033[K", end="")  # Move cursor up and clear line
                        print(f"{self.user_id}: {user_input}")

                        response = self.send_message_api(user_input)
                        print(f"briefly: {response}")
                    else:
                        # Get response from the agent (backend logs will show details)
                        response = await self.send_message_direct(user_input)
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
        """Demo streaming chat (supports both direct and API modes)."""

        mode_text = "API" if self.use_api else "Direct Multi-Agent"
        print(f"\n🌊 {mode_text} Streaming Demo")
        print("This shows how the system generates responses in real-time.\n")

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

        payload = {"user_id": self.user_id, "message": message}
        if self.active_thread:
            payload["thread_id"] = self.active_thread

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.chat_url}/chat/stream",
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


async def main():
    """Run the chat demo with command line argument support."""
    parser = argparse.ArgumentParser(
        description="Interactive chat demo with multi-agent WorkflowAgent and API support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python services/demos/chat.py                           # Direct multi-agent mode
  python services/demos/chat.py --api                     # API mode
  python services/demos/chat.py --streaming               # Direct streaming demo
  python services/demos/chat.py --api --streaming         # API streaming demo
  python services/demos/chat.py --message "hi"            # Send single message (direct)
  python services/demos/chat.py --api --message "hi"      # Send single message (API)
        """,
    )

    parser.add_argument(
        "--api",
        action="store_true",
        help="Use chat service API instead of direct multi-agent workflow",
    )

    parser.add_argument(
        "--chat-url",
        type=str,
        default="http://localhost:8001",
        help="Base URL for the chat service API (default: http://localhost:8001)",
    )

    parser.add_argument(
        "--user-id",
        type=str,
        default="demo_user",
        help="User ID for chat (default: demo_user)",
    )

    parser.add_argument(
        "--message", "-m", type=str, help="Send a single message (non-interactive mode)"
    )

    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Run streaming demo instead of regular chat (supports both direct and API modes)",
    )

    args = parser.parse_args()

    demo = ChatDemo(use_api=args.api, chat_url=args.chat_url, user_id=args.user_id)

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
    asyncio.run(main())
