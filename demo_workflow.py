#!/usr/bin/env python3
"""
Demo script for the simplified LlamaIndex Workflow-based chat agent.

This script demonstrates the workflow capabilities with realistic scenarios.
No longer includes separate clarification steps - the planner handles clarifications directly.
"""

import asyncio
import argparse
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_architecture_overview():
    """Display the simplified workflow architecture."""
    print("""
🏗️  SIMPLIFIED WORKFLOW ARCHITECTURE
=====================================

Workflow Steps:
1️⃣  start_workflow() → UserInputEvent
2️⃣  handle_user_input() → Planning + Direct Clarification OR ToolExecutionRequestedEvent  
3️⃣  handle_tool_execution_request() → ToolResultsForDrafterEvent OR ToolResultsForPlannerEvent
4️⃣  handle_tool_results_for_planner() → ToolExecutionRequestedEvent OR DraftCreatedEvent (clarification)
5️⃣  handle_tool_results_for_draft() → DraftCreatedEvent
6️⃣  handle_draft_created() → StopEvent (final response)

Key Simplifications:
✅ Planner handles clarifications directly (no separate clarification step)
✅ Cleaner event flow without clarification events
✅ Tool results route to planner when route_to_planner=True
✅ Direct path from planning to tools to drafting

Event Flow:
StartEvent → UserInputEvent → [Planning] → ToolExecutionRequestedEvent → ToolResultsForDrafterEvent → DraftCreatedEvent → StopEvent
""")

async def run_workflow_demo(use_mock: bool = True):
    """Run comprehensive workflow demo scenarios."""
    try:
        # Import here to avoid issues if modules aren't available
        from services.chat.workflow_agent import WorkflowChatAgent
        from services.chat.events import UserInputEvent, WorkflowMetadata
        
        print("🚀 Starting Simplified Workflow Demo\n")
        show_architecture_overview()
        
        # Initialize the workflow agent
        agent = WorkflowChatAgent(
            thread_id=12345,
            user_id="demo_user",
            llm_model="fake-model" if use_mock else "gpt-4o-mini",
            llm_provider="openai"
        )
        
        print(f"Agent initialized with LLM model: {'fake-model (mock)' if use_mock else 'gpt-4o-mini'}")
        print("=" * 60)
        
        # Demo scenarios
        scenarios = [
            {
                "name": "📧 Email Management Request",
                "message": "Show me my urgent emails and recent important messages",
                "description": "Tests email tool execution and intelligent draft creation"
            },
            {
                "name": "📅 Calendar Coordination",
                "message": "What meetings do I have today and when am I free for a call?",
                "description": "Tests calendar tools and availability analysis"
            },
            {
                "name": "🤔 Low Confidence Request (Triggers Clarification)",
                "message": "Help me with that thing",
                "description": "Tests direct clarification handling by planner"
            },
            {
                "name": "⚡ Mixed Request",
                "message": "Check my emails and calendar, then help me prepare for the team meeting",
                "description": "Tests multi-tool execution and complex draft creation"
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n🎬 SCENARIO {i}: {scenario['name']}")
            print(f"Description: {scenario['description']}")
            print(f"Input: \"{scenario['message']}\"")
            print("-" * 60)
            
            try:
                # Run the chat workflow
                result = await agent.chat(
                    message=scenario['message'],
                    conversation_history=[
                        {"role": "user", "content": "Hi there"},
                        {"role": "assistant", "content": "Hello! I'm here to help you manage your work."}
                    ]
                )
                
                # Check for error conditions
                error_indicators = [
                    "I apologize, but I encountered an error",
                    "events are consumed but never produced",
                    "workflow failed",
                    "error while processing your request",
                    "encountered an issue"
                ]
                
                is_error = any(indicator in result.lower() for indicator in error_indicators)
                
                if is_error:
                    print(f"❌ ERROR DETECTED in result: {result}")
                    print(f"💥 Scenario '{scenario['name']}' FAILED!")
                    logger.error(f"Workflow error detected: {result}")
                    # Exit with error code
                    import sys
                    sys.exit(1)
                else:
                    print(f"✅ Result: {result}")
                    
                    # Add some analysis of the result
                    if "[DRAFT]" in result:
                        draft_content = result.replace("[DRAFT] ", "")
                        print(f"📄 Draft Analysis:")
                        print(f"   • Length: {len(draft_content)} characters")
                        print(f"   • Contains emails: {'email' in draft_content.lower()}")
                        print(f"   • Contains calendar: {'calendar' in draft_content.lower() or 'meeting' in draft_content.lower()}")
                        print(f"   • Asks for clarification: {'clarification' in draft_content.lower() or '?' in draft_content}")
                
            except Exception as e:
                print(f"❌ EXCEPTION in scenario: {e}")
                logger.error(f"Scenario failed: {e}", exc_info=True)
                # Exit with error code for exceptions too
                import sys
                sys.exit(1)
            
            print("-" * 60)
            
            # Add a small delay between scenarios for readability
            await asyncio.sleep(0.5)
        
        print("\n🎉 ALL SCENARIOS PASSED! Simplified Workflow Demo Complete!")
        print("""
Key Achievements:
✅ Removed complex clarification subsystem
✅ Planner handles clarifications directly  
✅ Cleaner event-driven architecture
✅ Maintains sophisticated tool execution
✅ Intelligent draft creation from tool results
✅ Realistic mock responses for testing
✅ All scenarios completed without errors
        """)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the repository root and have installed dependencies.")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logger.error(f"Demo failed with error: {e}", exc_info=True)

def main():
    """Main entry point for the demo."""
    parser = argparse.ArgumentParser(description="Simplified LlamaIndex Workflow Chat Agent Demo")
    parser.add_argument(
        "--mock", 
        action="store_true", 
        help="Use mock LLM responses instead of real API calls"
    )
    
    args = parser.parse_args()
    
    print("🤖 Simplified LlamaIndex Workflow Chat Agent Demo")
    print("=" * 50)
    
    if args.mock:
        print("Using mock LLM responses (no API calls)")
    else:
        print("Using real LLM API calls (requires API key)")
    
    print()
    
    # Run the demo
    asyncio.run(run_workflow_demo(use_mock=args.mock))

if __name__ == "__main__":
    main() 