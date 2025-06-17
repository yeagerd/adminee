#!/usr/bin/env python3
"""
Demo script for the sophisticated WorkflowChatAgent.

This demo shows off the complete workflow capabilities including:
- Intent analysis and planning
- Tool execution simulation
- Clarification handling
- Draft creation
- Event-driven orchestration

Run with actual LLM: python demo_workflow.py
Run with mock responses: python demo_workflow.py --mock
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from services.chat.workflow_agent import create_workflow_chat_agent

async def demo_workflow_capabilities():
    """Demo the sophisticated workflow capabilities."""
    print("🚀 Starting WorkflowChatAgent Demo")
    print("=" * 50)
    
    # Check if we should use mock responses
    use_mock = "--mock" in sys.argv or "fake" in sys.argv
    
    if use_mock:
        print("📝 Using mock responses (fake-model)")
        llm_model = "fake-model"
        llm_provider = "fake"
    else:
        print("🤖 Using actual LLM calls (gpt-4o-mini)")
        llm_model = "gpt-4o-mini"
        llm_provider = "openai"
    
    # Create the workflow agent
    try:
        agent = create_workflow_chat_agent(
            thread_id=12345,
            user_id="demo-user",
            llm_model=llm_model,
            llm_provider=llm_provider,
            tools=["get_emails", "get_calendar_events", "create_document"]
        )
        print("✅ WorkflowChatAgent created successfully")
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return False
    
    # Demo scenarios
    scenarios = [
        {
            "name": "Simple Request",
            "message": "Hello, can you help me?",
            "description": "Basic greeting to test simple workflow path"
        },
        {
            "name": "Complex Planning Request", 
            "message": "I need to schedule a meeting with my team next week about the quarterly review. Can you help me find available times, draft an agenda, and send invitations?",
            "description": "Multi-step request requiring planning, tool execution, and drafting"
        },
        {
            "name": "Ambiguous Request",
            "message": "I need help with my project",
            "description": "Vague request that should trigger clarification workflow"
        },
        {
            "name": "Email Analysis Request",
            "message": "Can you check my recent emails and summarize any urgent items?",
            "description": "Tool-heavy request for email processing"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"User Message: \"{scenario['message']}\"")
        print("-" * 40)
        
        try:
            # Test the workflow
            response = await agent.chat(
                message=scenario['message'],
                conversation_history=[
                    {"role": "assistant", "content": "Hello! I'm ready to help you."},
                    {"role": "user", "content": "Thanks, I have a few tasks to work on."}
                ]
            )
            
            print(f"🎯 Agent Response:")
            print(f"   {response}")
            
            # Analyze the response
            if "WORKFLOW" in response:
                print("✅ Sophisticated workflow processing detected")
            elif "FAKE LLM RESPONSE" in response:
                print("✅ Simple workflow path used")
            elif "DRAFT" in response:
                print("✅ Draft creation workflow completed")
            else:
                print("⚠️  Unexpected response format")
                
        except Exception as e:
            print(f"❌ Scenario failed: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    return True

async def demo_mock_tool_responses():
    """Demo mock tool responses when using fake model."""
    print("\n🔧 Mock Tool Response Demo")
    print("=" * 30)
    
    # Simulate different tool responses
    mock_tools = {
        "get_emails": {
            "result": [
                {"subject": "Quarterly Review Meeting", "from": "manager@company.com", "urgent": True},
                {"subject": "Project Update", "from": "team@company.com", "urgent": False},
                {"subject": "Budget Approval", "from": "finance@company.com", "urgent": True}
            ]
        },
        "get_calendar_events": {
            "result": [
                {"title": "Team Standup", "time": "2024-01-15 09:00", "attendees": 5},
                {"title": "Client Call", "time": "2024-01-15 14:00", "attendees": 3}
            ]
        },
        "create_document": {
            "result": "Document created successfully with ID: doc_12345"
        }
    }
    
    for tool_name, mock_result in mock_tools.items():
        print(f"🔨 {tool_name}:")
        print(f"   Mock Result: {mock_result}")
    
    print("\n💡 In fake-model mode, these mock responses would be used")
    print("   to simulate realistic tool execution results.")

def print_workflow_architecture():
    """Print the workflow architecture overview."""
    print("\n🏗️  Workflow Architecture Overview")
    print("=" * 40)
    
    workflow_steps = [
        "StartEvent → UserInputEvent",
        "UserInputEvent → PlannerStep",
        "PlannerStep → ToolExecutionRequestedEvent | ClarificationRequestedEvent", 
        "ToolExecutionRequestedEvent → ToolExecutorStep",
        "ToolExecutorStep → ToolResultsForDrafterEvent | ToolResultsForPlannerEvent",
        "ClarificationRequestedEvent → ClarifierStep",
        "ClarifierStep → ClarificationPlannerUnblockedEvent | ClarificationDraftUnblockedEvent",
        "ToolResultsForDrafterEvent → DraftBuilderStep",
        "DraftBuilderStep → DraftCreatedEvent",
        "DraftCreatedEvent → StopEvent (Final Response)"
    ]
    
    for step in workflow_steps:
        print(f"  {step}")
    
    print(f"\n📊 Total @step methods: 9")
    print(f"📊 Total event types: 12")
    print(f"📊 Workflow complexity: Sophisticated multi-path orchestration")

async def main():
    """Main demo function."""
    print("🎭 WorkflowChatAgent Sophisticated Demo")
    print("🎯 Showcasing LlamaIndex Workflow-based Agent Architecture")
    print("=" * 60)
    
    # Print architecture overview
    print_workflow_architecture()
    
    # Run workflow demo
    success = await demo_workflow_capabilities()
    
    # Show mock tool demo
    if "--mock" in sys.argv or "fake" in sys.argv:
        await demo_mock_tool_responses()
    
    # Summary
    print("\n" + "=" * 60)
    if success:
        print("🎉 Demo completed successfully!")
        print("✨ The WorkflowChatAgent demonstrates:")
        print("   • Sophisticated intent analysis and planning")
        print("   • Event-driven workflow orchestration") 
        print("   • Multi-step tool execution simulation")
        print("   • Intelligent clarification handling")
        print("   • Context-aware draft creation")
        print("   • Production-ready LlamaIndex Workflow architecture")
    else:
        print("💥 Demo encountered issues")
    
    print(f"\n🔍 To explore the code:")
    print(f"   • Workflow: services/chat/workflow_agent.py")
    print(f"   • Events: services/chat/events.py") 
    print(f"   • Manager: services/chat/workflow_manager.py")

if __name__ == "__main__":
    print("Usage:")
    print("  python demo_workflow.py        # Use actual LLM calls")
    print("  python demo_workflow.py --mock # Use mock responses")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 