#!/usr/bin/env python3
"""
Demo script for the new WorkflowAgent implementation.

This script demonstrates how to use the WorkflowAgent which integrates
LlamaIndex's AgentWorkflow with the existing ChatAgent and LLM manager
infrastructure.

Usage:
    python services/demos/workflow_agent_demo.py
"""

import asyncio
import logging
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.chat.agents.workflow_agent import WorkflowAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demo_basic_workflow():
    """Demonstrate basic WorkflowAgent usage."""
    print("=== Basic WorkflowAgent Demo ===")

    # Create a workflow agent
    agent = WorkflowAgent(
        thread_id=1,
        user_id="demo_user",
        llm_model="fake-model",  # Using fake model for demo
        llm_provider="fake",
        max_tokens=2000,
    )

    print(f"Created WorkflowAgent for user: {agent.user_id}")
    print(f"Using LLM: {agent.llm_model} from {agent.llm_provider}")

    # Test basic chat
    print("\n--- Testing Basic Chat ---")
    response = await agent.chat("Hello, can you introduce yourself?")
    print("User: Hello, can you introduce yourself?")
    print(f"Agent: {response}")

    # Test memory
    print("\n--- Testing Memory ---")
    response = await agent.chat("What did I just ask you?")
    print("User: What did I just ask you?")
    print(f"Agent: {response}")

    # Get memory info
    memory_info = await agent.get_memory_info()
    print(f"\nMemory info: {memory_info}")


async def demo_with_tools():
    """Demonstrate WorkflowAgent with tools."""
    print("\n=== WorkflowAgent with Tools Demo ===")

    # Create a simple tool
    def get_weather(location: str) -> str:
        """Get weather information for a location."""
        return f"The weather in {location} is sunny and 72°F"

    def calculate(expression: str) -> str:
        """Calculate a mathematical expression."""
        try:
            result = eval(expression)  # Note: eval is not safe in production
            return f"The result of {expression} is {result}"
        except Exception as e:
            return f"Error calculating {expression}: {str(e)}"

    # Create agent with tools
    agent = WorkflowAgent(
        thread_id=2,
        user_id="demo_user_tools",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=2000,
        tools=[get_weather, calculate],
    )

    print(f"Created WorkflowAgent with {len(agent.tools)} custom tools")

    # Test tool usage
    print("\n--- Testing Tool Usage ---")
    response = await agent.chat("What's the weather like in San Francisco?")
    print("User: What's the weather like in San Francisco?")
    print(f"Agent: {response}")

    response = await agent.chat("Calculate 15 * 7 + 3")
    print("User: Calculate 15 * 7 + 3")
    print(f"Agent: {response}")


async def demo_office_tools():
    """Demonstrate WorkflowAgent with office tools."""
    print("\n=== WorkflowAgent with Office Tools Demo ===")

    # Create agent with office tools enabled
    agent = WorkflowAgent(
        thread_id=3,
        user_id="demo_user_office",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=2000,
    )

    # Get available office tools
    tool_registry = agent.tool_registry
    available_tools = tool_registry.list_tools()

    print(f"Available office tools: {available_tools}")

    # Note: Actual office tool usage would require the office service to be running
    # and proper authentication tokens
    response = await agent.chat("What office tools do you have available?")
    print("User: What office tools do you have available?")
    print(f"Agent: {response}")


async def demo_streaming():
    """Demonstrate WorkflowAgent streaming capabilities."""
    print("\n=== WorkflowAgent Streaming Demo ===")

    agent = WorkflowAgent(
        thread_id=4,
        user_id="demo_user_stream",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=2000,
    )

    print("User: Tell me a story about a robot")
    print("Agent (streaming): ", end="")

    # Stream the response
    async for event in agent.stream_chat("Tell me a story about a robot"):
        if hasattr(event, "delta") and event.delta:
            print(event.delta, end="", flush=True)
        elif hasattr(event, "error"):
            print(f"\nError: {event['error']}")
            break

    print("\n")


async def demo_context_management():
    """Demonstrate WorkflowAgent context persistence."""
    print("\n=== WorkflowAgent Context Management Demo ===")

    agent = WorkflowAgent(
        thread_id=5,
        user_id="demo_user_context",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=2000,
    )

    # Have a conversation
    await agent.chat("My name is Alice")
    await agent.chat("I like programming")

    # Save context
    context_data = await agent.save_context()
    print(f"Saved context with {len(context_data)} keys")

    # Create new agent and load context
    new_agent = WorkflowAgent(
        thread_id=5,
        user_id="demo_user_context",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=2000,
    )

    await new_agent.load_context(context_data)

    # Test if context was loaded
    response = await new_agent.chat("What's my name and what do I like?")
    print("User: What's my name and what do I like?")
    print(f"Agent (with loaded context): {response}")


async def demo_programmatic_draft_tracking():
    """Demonstrate the new programmatic draft tracking system."""
    print("\n=== Programmatic Draft Tracking Demo ===")

    agent = WorkflowAgent(
        thread_id=999,
        user_id="demo_user_drafts",
        llm_model="fake-model",
        llm_provider="fake",
        max_tokens=2000,
    )

    print(f"📋 Initial drafts: {agent.has_drafts()}")  # Should be False
    print(f"📋 Current drafts: {agent.get_current_drafts()}")  # Should be empty

    # Create some drafts via chat
    await agent.chat("Draft an email to john@example.com about the project meeting")
    await agent.chat("Create a calendar event for the team meeting tomorrow at 2pm")

    # Check drafts programmatically (no LLM tracking needed!)
    print("\n📝 After creating drafts:")
    print(f"📋 Has drafts: {agent.has_drafts()}")  # Should be True
    drafts = agent.get_current_drafts()
    for draft_type, draft_data in drafts.items():
        print(
            f"  • {draft_type}: {draft_data.get('subject', draft_data.get('title', 'No title'))}"
        )

    # Extract draft data asynchronously (compatible with existing API)
    async_drafts = await agent.get_draft_data()
    print(f"📋 Async draft count: {len(async_drafts)}")

    # Clear drafts programmatically
    success = agent.clear_all_drafts()
    print(f"\n🗑️ Cleared drafts: {success}")
    print(f"📋 Has drafts after clear: {agent.has_drafts()}")  # Should be False


async def main():
    """Run all demos."""
    print("WorkflowAgent Demo Script")
    print("=" * 50)

    try:
        await demo_basic_workflow()
        await demo_with_tools()
        await demo_office_tools()
        await demo_streaming()
        await demo_context_management()
        await demo_programmatic_draft_tracking()

        print("\n" + "=" * 50)
        print("Demo completed successfully!")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
