"""
LlamaIndex Workflow-based chat agent implementation.

This module provides a sophisticated chat agent built on LlamaIndex Workflow
for event-driven orchestration of planning, tool execution, and draft creation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from llama_index.core.workflow import Workflow, Context, StartEvent, StopEvent, step
from llama_index.core.llms import LLM

from .events import (
    UserInputEvent,
    ToolExecutionRequestedEvent,
    ToolResultsForPlannerEvent,
    ToolResultsForDrafterEvent,
    DraftCreatedEvent,
    WorkflowMetadata,
    ExecutionPlan
)
from .llm_manager import get_llm_manager

logger = logging.getLogger(__name__)


class WorkflowChatAgent(Workflow):
    """
    LlamaIndex Workflow-based chat agent with sophisticated event-driven orchestration.
    
    This workflow implements a complete chat agent system with:
    - Intelligent planning based on user input (with direct clarification handling)
    - Parallel/sequential tool execution
    - Context-aware draft creation
    - Event-driven step coordination
    """
    
    def __init__(
        self,
        thread_id: int,
        user_id: str,
        llm_model: str = "gpt-4o-mini",
        llm_provider: str = "openai",
        tools: Optional[List] = None,
        **kwargs
    ):
        """Initialize the workflow chat agent."""
        super().__init__(**kwargs)
        
        # Core agent properties
        self.thread_id = thread_id
        self.user_id = user_id
        self.llm_model = llm_model
        self.llm_provider = llm_provider
        
        # Initialize LLM
        llm_manager = get_llm_manager()
        self.llm = llm_manager.get_llm(llm_model, llm_provider)
        
        # Initialize tools and caches
        self.tools = tools or []
        self._planning_cache = {}
        self._user_preferences = {}
        self._execution_cache = {}
        self._draft_templates = {}
        self._user_style_preferences = {}
        
        logger.info(f"Initialized WorkflowChatAgent for thread {thread_id}, user {user_id}")

    async def chat(self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Main chat interface that starts the workflow.
        
        Args:
            message: User's message
            conversation_history: Previous conversation context
            
        Returns:
            Generated response string
        """
        try:
            # Create UserInputEvent to start the workflow
            user_input_event = UserInputEvent(
                thread_id=str(self.thread_id),
                user_id=self.user_id,
                message=message,
                conversation_history=conversation_history or [],
                metadata=WorkflowMetadata(priority="high")
            )
            
            # Run the workflow with the StartEvent
            result = await self.run(user_input=user_input_event)
            
            # Extract response from result
            if hasattr(result, 'result'):
                return result.result
            elif isinstance(result, str):
                return result
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"Chat workflow failed: {e}", exc_info=True)
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"

    @step
    async def start_workflow(self, ctx: Context, ev: StartEvent) -> None:
        """Handle the initial StartEvent and emit UserInputEvent."""
        logger.info("Starting workflow execution")
        
        # Extract user input from StartEvent
        user_input = getattr(ev, 'user_input', None)
        
        if user_input and isinstance(user_input, UserInputEvent):
            # Emit UserInputEvent to trigger the workflow
            ctx.send_event(user_input)
        else:
            # Create a simple UserInputEvent for backward compatibility
            simple_input = UserInputEvent(
                thread_id=str(self.thread_id),
                user_id=self.user_id,
                message="Simple request",
                conversation_history=[],
                metadata=WorkflowMetadata(priority="low")
            )
            ctx.send_event(simple_input)

    @step
    async def handle_user_input(self, ctx: Context, ev: UserInputEvent) -> None:
        """
        Handle initial user input and create execution plan.
        
        This is the main planning step that analyzes user intent, handles clarifications
        directly, and determines the appropriate workflow path.
        """
        logger.info(f"Processing user input: {ev.message[:50]}...")
        
        # Load user preferences for this user
        user_prefs = self._get_user_preferences(ev.user_id)
        
        # Analyze user intent and create execution plan
        analysis = await self._analyze_user_intent(
            ev.message,
            ev.conversation_history,
            user_prefs
        )
        
        # Learn user preferences from this interaction
        await self._learn_user_preferences(
            ev.user_id,
            ev.conversation_history,
            ev.message,
            analysis
        )
        
        # Create execution plan
        execution_plan = self._create_execution_plan(analysis)
        
        # Check if we need clarification - if so, ask user directly
        if analysis.get("confidence", 1.0) < 0.5 or analysis.get("clarification_points"):
            # Need clarification - create a simple response asking for clarification
            clarification_question = await self._generate_clarification_question(analysis, ev.message)
            
            # Create a simple draft with the clarification question
            draft_content = {
                "content": clarification_question,
                "type": "clarification",
                "requires_user_response": True
            }
            
            await self._emit_draft_created(ctx, ev, draft_content, "clarification")
        else:
            # Proceed with tool execution
            await self._emit_tool_execution_requests(ctx, ev, execution_plan)

    @step
    async def handle_tool_execution_request(self, ctx: Context, ev: ToolExecutionRequestedEvent) -> None:
        """
        Handle tool execution requests with parallel/sequential execution.
        
        This step executes the requested tools and routes results appropriately
        based on the execution strategy and routing flags.
        """
        logger.info(f"Executing {len(ev.tools_to_execute)} tools with {ev.execution_strategy} strategy")
        
        try:
            # Execute tools based on strategy
            if ev.should_execute_parallel():
                tool_results, execution_success, error_messages = await self._execute_tools_parallel(
                    ev.tools_to_execute, ev.thread_id, ev.user_id
                )
            else:
                tool_results, execution_success, error_messages = await self._execute_tools_sequential(
                    ev.tools_to_execute, ev.thread_id, ev.user_id
                )
            
            # Route results based on route_to_planner flag
            await self._route_tool_results(ctx, ev, tool_results, execution_success, error_messages)
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            await self._route_tool_results(ctx, ev, {}, False, [f"Tool execution error: {str(e)}"])

    @step
    async def handle_tool_results_for_planner(self, ctx: Context, ev: ToolResultsForPlannerEvent) -> None:
        """
        Handle tool results that require re-planning.
        
        This step processes tool results that may change the planning strategy
        and creates updated execution plans based on new information. Can also
        ask for clarification directly if needed.
        """
        logger.info("Processing tool results for re-planning")
        
        # Analyze tool results for planning insights
        analysis = await self._analyze_tool_results(
            ev.tool_results,
            ev.planning_insights.get("conversation_history", [])
        )
        
        # Get user preferences
        user_prefs = self._get_user_preferences(ev.user_id)
        
        # Create updated execution plan
        execution_plan = self._create_execution_plan_from_tool_results(analysis, user_prefs)
        
        # Check if we need clarification from tool results
        if analysis.get("confidence", 1.0) < 0.5 or analysis.get("clarification_points"):
            # Need clarification - create a simple response asking for clarification
            clarification_question = await self._generate_clarification_question_from_tools(analysis, ev.tool_results)
            
            # Create a simple draft with the clarification question
            draft_content = {
                "content": clarification_question,
                "type": "clarification",
                "requires_user_response": True
            }
            
            await self._emit_draft_created(ctx, ev, draft_content, "tool_clarification")
        else:
            # Proceed with additional tool execution or drafting
            await self._emit_tool_execution_requests_from_results(ctx, ev, execution_plan)

    @step
    async def handle_tool_results_for_draft(self, ctx: Context, ev: ToolResultsForDrafterEvent) -> None:
        """
        Handle tool results ready for draft creation.
        
        This step creates drafts from tool results without requiring
        additional planning.
        """
        logger.info(f"Creating draft from {len(ev.tool_results)} tool results")
        
        try:
            # Create draft from tool results
            draft_content = await self._create_draft_from_tools(
                ev.tool_results,
                ev.draft_context,
                ev.user_id
            )
            
            # Emit draft created event
            await self._emit_draft_created(ctx, ev, draft_content, "tool_results")
            
        except Exception as e:
            logger.error(f"Draft creation from tools failed: {e}", exc_info=True)
            await self._emit_error_draft(ctx, ev, f"Failed to create draft: {str(e)}")

    @step
    async def handle_draft_created(self, ctx: Context, ev: DraftCreatedEvent) -> StopEvent:
        """
        Handle draft created event and return final response.
        
        This is the terminal step that receives DraftCreatedEvent and returns
        the final StopEvent with the draft content.
        """
        logger.info(f"Draft created: {ev.draft_type} with confidence {ev.confidence_score}")
        
        # Format the final response
        response = f"[DRAFT] {ev.draft_content}"
        return StopEvent(result=response)

    # Helper methods for workflow logic
    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for planning."""
        return self._user_preferences.get(user_id, {
            "communication_style": "professional",
            "urgency_preference": "medium",
            "detail_level": "standard",
            "preferred_tools": ["get_emails", "get_calendar_events"],
            "automation_level": "medium",
            "confirmation_required": True
        })

    async def _learn_user_preferences(
        self,
        user_id: str,
        conversation_history: List[Dict[str, str]],
        user_message: str,
        analysis: Dict[str, Any]
    ) -> None:
        """Learn user preferences from conversation patterns."""
        # Initialize user preferences if not exists
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = self._get_user_preferences(user_id)
        
        user_prefs = self._user_preferences[user_id]
        
        # Learn communication style from message patterns
        message_length = len(user_message.split())
        if message_length < 10:
            user_prefs["communication_style"] = "brief"
        elif message_length > 50:
            user_prefs["communication_style"] = "detailed"
        
        # Learn urgency patterns
        urgency_keywords = ["urgent", "asap", "immediately", "quickly", "rush"]
        if any(keyword in user_message.lower() for keyword in urgency_keywords):
            user_prefs["urgency_preference"] = "high"
        
        # Store updated preferences
        self._user_preferences[user_id] = user_prefs

    async def _analyze_user_intent(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        user_prefs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze user intent using LLM."""
        # Build context from conversation history
        context = "\n".join([
            f"{turn.get('role', 'user')}: {turn.get('content', '')}"
            for turn in conversation_history[-5:]  # Last 5 turns
        ])
        
        # Create analysis prompt
        prompt = f"""Analyze the user's intent and requirements from their message.
        
Context from recent conversation:
{context}

User Message: "{message}"

User Preferences:
- Communication Style: {user_prefs.get('communication_style', 'professional')}
- Urgency Preference: {user_prefs.get('urgency_preference', 'medium')}
- Detail Level: {user_prefs.get('detail_level', 'standard')}

Analyze and provide:
- "intent": Main user intention (email, calendar, document, etc.)
- "confidence": Confidence level 0.0-1.0 in understanding the request
- "required_tools": List of tools needed ["get_emails", "get_calendar", etc.]
- "execution_strategy": "parallel" or "sequential"
- "clarification_points": List of things that need clarification
- "urgency": "low", "medium", or "high"
- "scope": Brief description of what needs to be done

Respond in JSON format only."""

        try:
            response = await self._safe_llm_call(prompt, max_tokens=300)
            # Try to parse JSON response
            import json
            analysis = json.loads(response.strip())
            
            # Validate and provide defaults
            analysis["confidence"] = analysis.get("confidence", 0.8)
            analysis["required_tools"] = analysis.get("required_tools", [])
            analysis["execution_strategy"] = analysis.get("execution_strategy", "parallel")
            analysis["clarification_points"] = analysis.get("clarification_points", [])
            analysis["urgency"] = analysis.get("urgency", "medium")
            analysis["scope"] = analysis.get("scope", "Process user request")
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Intent analysis failed, using fallback: {e}")
            return self._get_fallback_analysis(message)

    def _get_fallback_analysis(self, message: str) -> Dict[str, Any]:
        """Provide fallback analysis when LLM analysis fails."""
        # Simple keyword-based analysis
        message_lower = message.lower()
        
        if "email" in message_lower:
            intent = "email_management"
            tools = ["get_emails", "search_emails"]
        elif "calendar" in message_lower or "meeting" in message_lower:
            intent = "calendar_management"
            tools = ["get_calendar_events", "search_calendar"]
        elif "document" in message_lower or "file" in message_lower:
            intent = "document_management"
            tools = ["get_documents", "search_documents"]
        else:
            intent = "general_assistance"
            tools = ["get_emails", "get_calendar_events"]
        
        return {
            "intent": intent,
            "confidence": 0.6,
            "required_tools": tools,
            "execution_strategy": "parallel",
            "clarification_points": [],
            "urgency": "medium",
            "scope": f"Handle {intent} request"
        }

    def _create_execution_plan(self, analysis: Dict[str, Any]) -> ExecutionPlan:
        """Create execution plan from analysis."""
        plan = ExecutionPlan(
            goal=analysis.get("scope", "Process user request"),
            confidence=analysis.get("confidence", 0.8),
            execution_strategy=analysis.get("execution_strategy", "parallel"),
            assumptions=[f"User intent: {analysis.get('intent', 'general')}"]
        )
        
        # Add task groups based on required tools
        required_tools = analysis.get("required_tools", [])
        if required_tools:
            plan.add_task_group(
                tasks=required_tools,
                can_run_parallel=(analysis.get("execution_strategy") == "parallel"),
                estimated_duration="30-60 seconds"
            )
        
        return plan

    async def _generate_clarification_question(self, analysis: Dict[str, Any], original_message: str) -> str:
        """Generate a clarification question based on analysis."""
        clarification_points = analysis.get("clarification_points", [])
        
        if clarification_points:
            questions = []
            for i, point in enumerate(clarification_points[:3], 1):  # Limit to 3 questions
                questions.append(f"{i}. {point}")
            
            question_list = "\n".join(questions)
            return f"I need some clarification to help you better:\n\n{question_list}\n\nCould you provide more details on these points?"
        else:
            # Generic clarification based on low confidence
            return f"I want to make sure I understand your request correctly. You mentioned: '{original_message}'\n\nCould you provide a bit more detail about what specifically you'd like me to help you with?"

    async def _generate_clarification_question_from_tools(self, analysis: Dict[str, Any], tool_results: Dict[str, Any]) -> str:
        """Generate clarification question based on tool results analysis."""
        clarification_points = analysis.get("clarification_points", [])
        
        if clarification_points:
            questions = []
            for i, point in enumerate(clarification_points[:3], 1):
                questions.append(f"{i}. {point}")
            
            question_list = "\n".join(questions)
            return f"Based on the information I found, I need some clarification:\n\n{question_list}\n\nCould you help me with these details?"
        else:
            # Generic clarification for tool results
            available_info = ", ".join(tool_results.keys()) if tool_results else "limited information"
            return f"I found {available_info}, but I need a bit more guidance on how you'd like me to proceed. Could you provide more specific direction?"

    async def _emit_tool_execution_requests(
        self,
        ctx: Context,
        original_event: UserInputEvent,
        execution_plan: ExecutionPlan
    ) -> None:
        """Emit tool execution requests based on execution plan."""
        if not execution_plan.task_groups:
            # No tools to execute, go straight to draft creation
            draft_content = {
                "content": "I understand your request, but I don't have specific tools to help with this. Could you provide more details or try a different request?",
                "type": "response"
            }
            await self._emit_draft_created(ctx, original_event, draft_content, "no_tools")
            return
        
        # Emit tool execution request
        for i, task_group in enumerate(execution_plan.task_groups):
            tools_to_execute = [
                {
                    "tool_name": tool,
                    "inputs": {"user_id": original_event.user_id, "thread_id": original_event.thread_id},
                    "execution_group_id": f"group_{i}"
                }
                for tool in task_group["tasks"]
            ]
            
            tool_event = ToolExecutionRequestedEvent(
                thread_id=original_event.thread_id,
                user_id=original_event.user_id,
                tools_to_execute=tools_to_execute,
                execution_strategy="parallel" if task_group.get("can_run_parallel", True) else "sequential",
                parent_plan_event_id=str(uuid4()),
                route_to_planner=False,  # Default to drafting
                metadata=WorkflowMetadata(priority="high")
            )
            
            ctx.send_event(tool_event)

    async def _execute_tools_parallel(
        self,
        tools_to_execute: List[Dict[str, Any]],
        thread_id: str,
        user_id: str
    ) -> Tuple[Dict[str, Any], bool, List[str]]:
        """Execute tools in parallel."""
        logger.info(f"Executing {len(tools_to_execute)} tools in parallel")
        
        # Mock implementation - replace with actual tool execution
        results = {}
        errors = []
        
        for tool_config in tools_to_execute:
            tool_name = tool_config.get("tool_name", "unknown")
            
            # Simulate tool execution with realistic mock data
            if "email" in tool_name.lower():
                results[tool_name] = {
                    "emails": [
                        {
                            "id": f"email_{i}",
                            "from": f"sender{i}@example.com",
                            "subject": f"Important Email {i}",
                            "body": f"This is email content {i}",
                            "date": "2024-01-15",
                            "urgent": i == 1
                        }
                        for i in range(1, 4)
                    ],
                    "total_count": 3
                }
            elif "calendar" in tool_name.lower():
                results[tool_name] = {
                    "events": [
                        {
                            "id": f"event_{i}",
                            "title": f"Meeting {i}",
                            "start_time": f"2024-01-1{5+i} 10:00:00",
                            "end_time": f"2024-01-1{5+i} 11:00:00",
                            "attendees": [f"attendee{i}@example.com"],
                            "location": f"Conference Room {i}"
                        }
                        for i in range(1, 3)
                    ],
                    "total_count": 2
                }
            else:
                results[tool_name] = {
                    "status": "success",
                    "data": f"Mock result for {tool_name}",
                    "timestamp": datetime.now().isoformat()
                }
        
        return results, True, errors

    async def _execute_tools_sequential(
        self,
        tools_to_execute: List[Dict[str, Any]],
        thread_id: str,
        user_id: str
    ) -> Tuple[Dict[str, Any], bool, List[str]]:
        """Execute tools sequentially."""
        logger.info(f"Executing {len(tools_to_execute)} tools sequentially")
        
        # For simplicity, use the same mock as parallel execution
        return await self._execute_tools_parallel(tools_to_execute, thread_id, user_id)

    async def _route_tool_results(
        self,
        ctx: Context,
        original_event: ToolExecutionRequestedEvent,
        tool_results: Dict[str, Any],
        execution_success: bool,
        error_messages: List[str]
    ) -> None:
        """Route tool results based on the route_to_planner flag."""
        if original_event.route_to_planner:
            # Route to planner for re-planning
            event = ToolResultsForPlannerEvent(
                thread_id=original_event.thread_id,
                user_id=original_event.user_id,
                parent_request_event_id=original_event.parent_plan_event_id,
                tool_results=tool_results,
                execution_success=execution_success,
                error_messages=error_messages,
                planning_insights={"needs_replanning": not execution_success},
                metadata=WorkflowMetadata(priority="high")
            )
        else:
            # Route to drafter for draft creation
            event = ToolResultsForDrafterEvent(
                thread_id=original_event.thread_id,
                user_id=original_event.user_id,
                parent_request_event_id=original_event.parent_plan_event_id,
                tool_results=tool_results,
                execution_success=execution_success,
                error_messages=error_messages,
                draft_context={"ready_for_draft": execution_success},
                metadata=WorkflowMetadata(priority="high")
            )
        
        ctx.send_event(event)

    async def _create_draft_from_tools(
        self,
        tool_results: Dict[str, Any],
        draft_context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Create draft from tool results."""
        logger.info("Creating draft from tool results")
        
        # Analyze tool results to create coherent draft
        content_parts = []
        
        for tool_name, result in tool_results.items():
            if "email" in tool_name.lower() and "emails" in result:
                emails = result["emails"]
                urgent_emails = [e for e in emails if e.get("urgent", False)]
                
                if urgent_emails:
                    content_parts.append("🚨 **Urgent Emails:**")
                    for email in urgent_emails:
                        content_parts.append(f"• **{email['subject']}** from {email['from']}")
                
                if len(emails) > len(urgent_emails):
                    regular_emails = [e for e in emails if not e.get("urgent", False)]
                    content_parts.append(f"\n📧 **Other Emails ({len(regular_emails)}):**")
                    for email in regular_emails[:3]:  # Show first 3
                        content_parts.append(f"• {email['subject']} from {email['from']}")
                        
            elif "calendar" in tool_name.lower() and "events" in result:
                events = result["events"]
                content_parts.append(f"\n📅 **Upcoming Events ({len(events)}):**")
                for event in events:
                    content_parts.append(f"• **{event['title']}** - {event['start_time']}")
                    if event.get('location'):
                        content_parts.append(f"  📍 {event['location']}")
        
        if not content_parts:
            content_parts = ["I found some information, but need clarification on how to proceed."]
        
        draft_content = "\n".join(content_parts)
        
        return {
            "content": draft_content,
            "type": "summary",
            "word_count": len(draft_content.split()),
            "confidence": 0.9
        }

    async def _emit_draft_created(
        self,
        ctx: Context,
        original_event,
        draft_content: Dict[str, Any],
        source: str
    ) -> None:
        """Emit draft created event."""
        event = DraftCreatedEvent(
            thread_id=getattr(original_event, 'thread_id', str(self.thread_id)),
            user_id=getattr(original_event, 'user_id', self.user_id),
            draft_content=draft_content.get("content", ""),
            draft_type=draft_content.get("type", "response"),
            confidence_score=draft_content.get("confidence", 0.8),
            word_count=draft_content.get("word_count"),
            source_events=[source],
            metadata=WorkflowMetadata(priority="high")
        )
        
        ctx.send_event(event)

    async def _emit_error_draft(
        self,
        ctx: Context,
        original_event,
        error_message: str
    ) -> None:
        """Emit error draft when something goes wrong."""
        draft_content = f"I apologize, but I encountered an issue: {error_message}"
        
        event = DraftCreatedEvent(
            thread_id=getattr(original_event, 'thread_id', str(self.thread_id)),
            user_id=getattr(original_event, 'user_id', self.user_id),
            draft_content=draft_content,
            draft_type="error",
            confidence_score=0.1,
            word_count=len(draft_content.split()),
            metadata=WorkflowMetadata(priority="high")
        )
        
        ctx.send_event(event)

    async def _safe_llm_call(self, prompt: str, max_tokens: int = 500, temperature: float = 0.1) -> str:
        """Make a safe LLM call with error handling."""
        try:
            response = await self.llm.acomplete(prompt, max_tokens=max_tokens, temperature=temperature)
            return response.text if hasattr(response, 'text') else str(response)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return "[FAKE LLM RESPONSE]"  # Fallback for testing

    async def _analyze_tool_results(
        self,
        tool_results: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Analyze tool results to determine next steps."""
        # Simple analysis for now
        has_results = bool(tool_results)
        confidence = 0.9 if has_results else 0.3
        
        return {
            "confidence": confidence,
            "has_results": has_results,
            "clarification_points": [] if has_results else ["The tools didn't return expected results. What would you like me to focus on?"]
        }

    def _create_execution_plan_from_tool_results(
        self,
        analysis: Dict[str, Any],
        user_prefs: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create execution plan from tool results analysis."""
        return ExecutionPlan(
            goal="Process tool results and continue workflow",
            confidence=analysis.get("confidence", 0.8),
            execution_strategy="sequential",
            assumptions=["Tool results available for processing"]
        )

    async def _emit_tool_execution_requests_from_results(
        self,
        ctx: Context,
        original_event,
        execution_plan: ExecutionPlan
    ) -> None:
        """Emit tool execution requests from results analysis."""
        # For simplicity, just create a draft saying we processed the results
        draft_content = {
            "content": "I've processed the available information. Is there anything specific you'd like me to focus on or help you with next?",
            "type": "follow_up"
        }
        
        await self._emit_draft_created(ctx, original_event, draft_content, "follow_up")


def create_workflow_chat_agent(
    thread_id: int,
    user_id: str,
    llm_model: str = "gpt-4o-mini",
    llm_provider: str = "openai",
    tools: Optional[List] = None,
    **kwargs
) -> WorkflowChatAgent:
    """
    Factory function to create a WorkflowChatAgent.
    
    Args:
        thread_id: Thread identifier
        user_id: User identifier
        llm_model: LLM model to use
        llm_provider: LLM provider to use
        tools: Optional list of tools
        **kwargs: Additional arguments for the workflow
        
    Returns:
        Configured WorkflowChatAgent instance
    """
    return WorkflowChatAgent(
        thread_id=thread_id,
        user_id=user_id,
        llm_model=llm_model,
        llm_provider=llm_provider,
        tools=tools,
        **kwargs
    )