#!/usr/bin/env python3
"""
Interactive Chat Demo for WorkflowAgent.

This script provides a simple command-line interface to chat with the WorkflowAgent
in both single-agent and multi-agent modes. Great for testing and demonstration.

Usage:
    python services/demos/chat-simple.py
"""

import asyncio
import logging
import os
import sys
from typing import Optional

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chat.agents.workflow_agent import WorkflowAgent

# Configure logging (quieter for interactive use)
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ChatDemo:
    """Interactive chat demo for WorkflowAgent."""

    def __init__(self):
        self.agent: Optional[WorkflowAgent] = None
        self.thread_id = 1
        self.user_id = "demo_user"

    async def create_agent(self, use_multi_agent: bool = True) -> WorkflowAgent:
        """Create and initialize a WorkflowAgent."""
        print(f"\n🤖 Creating {'Multi-Agent' if use_multi_agent else 'Single-Agent'} WorkflowAgent...")
        
        agent = WorkflowAgent(
            thread_id=self.thread_id,
            user_id=self.user_id,
            llm_model="gpt-3.5-turbo",  # You can change this to your preferred model
            llm_provider="openai",
            max_tokens=2000,
            use_multi_agent=use_multi_agent,
            office_service_url="http://localhost:8001",
        )
        
        # Build the agent (this initializes the workflow)
        await agent.build_agent("Hello, I'm ready to help!")
        
        if use_multi_agent:
            print(f"✅ Multi-Agent system ready with {len(agent.specialized_agents)} specialized agents:")
            for agent_name in agent.specialized_agents.keys():
                print(f"   • {agent_name}")
        else:
            print("✅ Single-Agent system ready")
        
        return agent

    def show_welcome(self):
        """Show welcome message and instructions."""
        print("=" * 60)
        print("🚀 Welcome to the Interactive WorkflowAgent Demo!")
        print("=" * 60)
        print()
        print("This demo lets you chat with the WorkflowAgent system.")
        print("You can test both single-agent and multi-agent modes.")
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
        print("  • 'switch' - Switch between single and multi-agent modes")
        print("  • 'help' - Show this help message")
        print("  • 'clear' - Clear the conversation history")
        print()

    def show_help(self):
        """Show help message."""
        print("\n📋 Available Commands:")
        print("  • Type any message to chat with the agent")
        print("  • 'quit' or 'exit' - Exit the demo")
        print("  • 'switch' - Switch between single and multi-agent modes")
        print("  • 'help' - Show this help message")
        print("  • 'clear' - Clear the conversation history")
        print()
        print("📋 Example prompts:")
        print("  • 'What meetings do I have this week?'")
        print("  • 'Show me my unread emails from today'")
        print("  • 'Find my notes about the quarterly planning'")
        print("  • 'Draft an email to john@example.com about the project'")
        print("  • 'Help me organize my calendar for tomorrow'")
        print()

    async def switch_mode(self):
        """Switch between single-agent and multi-agent modes."""
        if self.agent is None:
            return
        
        current_mode = "Multi-Agent" if self.agent.use_multi_agent else "Single-Agent"
        new_mode = not self.agent.use_multi_agent
        
        print(f"\n🔄 Switching from {current_mode} to {'Multi-Agent' if new_mode else 'Single-Agent'} mode...")
        
        # Increment thread ID to start fresh
        self.thread_id += 1
        self.agent = await self.create_agent(use_multi_agent=new_mode)

    async def clear_history(self):
        """Clear the conversation history by creating a new agent."""
        if self.agent is None:
            return
        
        print("\n🧹 Clearing conversation history...")
        
        # Increment thread ID to start fresh
        self.thread_id += 1
        current_mode = self.agent.use_multi_agent
        self.agent = await self.create_agent(use_multi_agent=current_mode)

    async def chat_loop(self):
        """Main chat loop."""
        self.show_welcome()
        
        # Ask user to choose mode
        while True:
            mode_choice = input("Choose mode (1=Multi-Agent, 2=Single-Agent, default=1): ").strip()
            if mode_choice in ["", "1"]:
                use_multi_agent = True
                break
            elif mode_choice == "2":
                use_multi_agent = False
                break
            else:
                print("Please enter 1, 2, or press Enter for default.")
        
        # Create the agent
        self.agent = await self.create_agent(use_multi_agent=use_multi_agent)
        
        print(f"\n💬 Chat started! (Current mode: {'Multi-Agent' if self.agent.use_multi_agent else 'Single-Agent'})")
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
                
                elif user_input.lower() == "switch":
                    await self.switch_mode()
                    print(f"💬 Switched to {'Multi-Agent' if self.agent.use_multi_agent else 'Single-Agent'} mode. Continue chatting!\n")
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
        """Demo streaming chat (if you want to show streaming responses)."""
        print("\n🌊 Streaming Demo Mode")
        print("This shows how responses are generated in real-time.\n")
        
        self.agent = await self.create_agent(use_multi_agent=True)
        
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