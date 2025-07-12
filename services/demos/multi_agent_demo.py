#!/usr/bin/env python3
"""
Multi-Agent Workflow Demo for the chat service.

This script demonstrates the multi-agent workflow system with specialized agents:
- CoordinatorAgent: Main orchestrator
- CalendarAgent: Calendar operations
- EmailAgent: Email operations
- DocumentAgent: Document and note operations
- DraftAgent: Creating drafts

Usage:
    python services/demos/multi_agent_demo.py
"""

import asyncio
import logging
import os
import sys

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chat.agents.workflow_agent import WorkflowAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demo_multi_agent_coordination():
    """Demonstrate multi-agent coordination for complex requests."""
    print("=== Multi-Agent Coordination Demo ===")

    # Create a multi-agent workflow
    agent = WorkflowAgent(
        thread_id=1,
        user_id="demo_user",
        llm_model="fake-model",  # Using fake model for demo
        llm_provider="fake",
        max_tokens=2000,
    )

    print(f"Created multi-agent WorkflowAgent for user: {agent.user_id}")
    print("Multi-agent mode: Enabled (default)")
    print(
        f"Available agents: {list(agent.specialized_agents.keys()) if agent.specialized_agents else 'None yet (built on first use)'}"
    )

    # Test a complex request that requires coordination
    print("\n--- Testing Complex Multi-Agent Request ---")
    request = (
        "I need to prepare for a meeting tomorrow. Can you find my calendar events for tomorrow, "
        "check if I have any related emails about the project, find any relevant documents, "
        "and help me draft a follow-up email to send after the meeting?"
    )

    print(f"User: {request}")
    response = await agent.chat(request)
    print(f"Multi-Agent System: {response}")

    return agent


async def demo_calendar_agent():
    """Demonstrate CalendarAgent specialization."""
    print("\n=== CalendarAgent Specialization Demo ===")

    agent = WorkflowAgent(
        thread_id=2,
        user_id="demo_calendar_user",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Calendar-focused request
    response = await agent.chat("What meetings do I have scheduled for this week?")
    print("User: What meetings do I have scheduled for this week?")
    print(f"CalendarAgent (via Coordinator): {response}")


async def demo_email_agent():
    """Demonstrate EmailAgent specialization."""
    print("\n=== EmailAgent Specialization Demo ===")

    agent = WorkflowAgent(
        thread_id=3,
        user_id="demo_email_user",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Email-focused request
    response = await agent.chat("Show me my unread emails from today")
    print("User: Show me my unread emails from today")
    print(f"EmailAgent (via Coordinator): {response}")


async def demo_document_agent():
    """Demonstrate DocumentAgent specialization."""
    print("\n=== DocumentAgent Specialization Demo ===")

    agent = WorkflowAgent(
        thread_id=4,
        user_id="demo_document_user",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Document-focused request
    response = await agent.chat("Find my notes about the quarterly planning project")
    print("User: Find my notes about the quarterly planning project")
    print(f"DocumentAgent (via Coordinator): {response}")


async def demo_draft_agent():
    """Demonstrate DraftAgent specialization."""
    print("\n=== DraftAgent Specialization Demo ===")

    agent = WorkflowAgent(
        thread_id=5,
        user_id="demo_draft_user",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Drafting-focused request
    response = await agent.chat(
        "Draft an email to john@example.com with subject 'Meeting Follow-up' "
        "about the action items we discussed in today's planning meeting"
    )
    print("User: Draft an email to john@example.com...")
    print(f"DraftAgent (via Coordinator): {response}")


async def demo_agent_handoffs():
    """Demonstrate how agents hand off to each other."""
    print("\n=== Agent Handoff Demo ===")

    agent = WorkflowAgent(
        thread_id=6,
        user_id="demo_handoff_user",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Request that requires multiple agents
    response = await agent.chat(
        "Look up my meeting with Sarah tomorrow, find any emails about the budget proposal, "
        "and then draft a calendar change to extend the meeting by 30 minutes"
    )

    print("User: Look up my meeting with Sarah tomorrow...")
    print(f"Multi-Agent Handoff Result: {response}")


async def demo_state_sharing():
    """Demonstrate how agents share state and information."""
    print("\n=== State Sharing Demo ===")

    agent = WorkflowAgent(
        thread_id=7,
        user_id="demo_state_user",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # First, have agents gather information
    await agent.chat("Find my calendar events for today and any related emails")

    # Then use that information in a follow-up request
    response = await agent.chat(
        "Based on the calendar and email information you found, "
        "draft a summary email to my manager about today's activities"
    )

    print("User: Based on the calendar and email information you found...")
    print(f"State-Aware Response: {response}")


async def demo_single_vs_multi_agent():
    """Compare single-agent vs multi-agent responses."""
    print("\n=== Single vs Multi-Agent Comparison ===")

    request = "Help me organize my day by checking my calendar, emails, and creating a task list"

    # Single-agent mode
    single_agent = WorkflowAgent(
        thread_id=8,
        user_id="demo_single",
        llm_model="fake-model",
        llm_provider="fake",
    )

    single_response = await single_agent.chat(request)

    # Multi-agent mode
    multi_agent = WorkflowAgent(
        thread_id=9,
        user_id="demo_multi",
        llm_model="fake-model",
        llm_provider="fake",
    )

    multi_response = await multi_agent.chat(request)

    print(f"Request: {request}")
    print(f"\nSingle-Agent Response: {single_response}")
    print(f"\nMulti-Agent Response: {multi_response}")


async def demo_context_persistence():
    """Demonstrate context persistence in multi-agent mode."""
    print("\n=== Multi-Agent Context Persistence Demo ===")

    agent = WorkflowAgent(
        thread_id=10,
        user_id="demo_context",
        llm_model="fake-model",
        llm_provider="fake",
    )

    # Build up context across multiple interactions
    await agent.chat("Find my calendar events for tomorrow")
    await agent.chat("What emails do I have about the project planning?")

    # Save and reload context
    context_data = await agent.save_context()
    print(f"Saved context with {len(context_data)} keys")

    # Create new agent and load context
    new_agent = WorkflowAgent(
        thread_id=10,
        user_id="demo_context",
        llm_model="fake-model",
        llm_provider="fake",
    )

    await new_agent.load_context(context_data)

    # Use the loaded context
    response = await new_agent.chat(
        "Based on the calendar and email information from before, "
        "what should I prioritize tomorrow?"
    )

    print("User: Based on the calendar and email information from before...")
    print(f"Agent (with loaded context): {response}")


async def main():
    """Run all multi-agent demos."""
    print("Multi-Agent Workflow Demo Script")
    print("=" * 60)

    try:
        # Core multi-agent functionality
        await demo_multi_agent_coordination()

        # Individual agent specializations
        await demo_calendar_agent()
        await demo_email_agent()
        await demo_document_agent()
        await demo_draft_agent()

        # Advanced multi-agent features
        await demo_agent_handoffs()
        await demo_state_sharing()
        await demo_single_vs_multi_agent()
        await demo_context_persistence()

        print("\n" + "=" * 60)
        print("Multi-Agent Demo completed successfully!")
        print("\nKey Benefits Demonstrated:")
        print("- Specialized agents for different domains")
        print("- Intelligent agent handoffs and coordination")
        print("- Shared state and information between agents")
        print("- Context persistence across interactions")
        print("- Improved task decomposition and execution")

    except Exception as e:
        logger.error(f"Multi-agent demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
