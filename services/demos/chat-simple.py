#!/usr/bin/env python3
"""
Interactive Multi-Agent Chat Demo for WorkflowAgent.

This script provides a simple command-line interface to chat with the WorkflowAgent
multi-agent system. Features specialized agents for calendar, email, documents, and drafting.

Usage:
    python services/demos/chat-simple.py
"""

import asyncio
import logging
import os
import sys
from typing import Optional

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.chat.agents.workflow_agent import WorkflowAgent

# Configure logging (quieter for interactive use)
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ChatDemo:
    """Interactive multi-agent chat demo for WorkflowAgent."""

    def __init__(self):
        self.agent: Optional[WorkflowAgent] = None
        self.thread_id = 1
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
        
        print(f"✅ Multi-Agent system ready with {len(agent.specialized_agents)} specialized agents:")
        for agent_name in agent.specialized_agents.keys():
            print(f"   • {agent_name}")
        
        return agent

    def show_welcome(self):
        """Show welcome message and instructions."""
        print("=" * 60)
        print("🚀 Welcome to the Multi-Agent WorkflowAgent Demo!")
        print("=" * 60)
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
        
        # Increment thread ID to start fresh
        self.thread_id += 1
        self.agent = await self.create_agent()

    async def chat_loop(self):
        """Main chat loop."""
        self.show_welcome()
        
        # Create the multi-agent system
        self.agent = await self.create_agent()
        
        print(f"\n💬 Multi-Agent chat started!")
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
                    # Get response from the agent
                    response = await self.agent.chat(user_input)
                    print(response)
                    
                except Exception as e:
                    print(f"Sorry, I encountered an error: {str(e)}")
                    logger.error(f"Chat error: {e}")
                
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
        print("This shows how the multi-agent system generates responses in real-time.\n")
        
        self.agent = await self.create_agent()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input or user_input.lower() in ["quit", "exit"]:
                    break
                
                print("🤖 Briefly: ", end="", flush=True)
                
                # Stream the response
                async for chunk in self.agent.stream_chat(user_input):
                    if hasattr(chunk, 'delta') and chunk.delta:
                        print(chunk.delta, end="", flush=True)
                
                print("\n")  # New line after streaming
                
            except KeyboardInterrupt:
                print("\n\n👋 Streaming demo interrupted. Goodbye!")
                break
            
            except Exception as e:
                print(f"\n❌ Streaming error: {str(e)}")
                break


async def main():
    """Run the interactive chat demo."""
    demo = ChatDemo()
    
    # Check if user wants streaming demo
    if len(sys.argv) > 1 and sys.argv[1] == "--streaming":
        await demo.run_streaming_demo()
    else:
        await demo.chat_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Demo failed to start: {e}")
        sys.exit(1) 