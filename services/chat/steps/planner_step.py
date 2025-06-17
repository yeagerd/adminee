"""
PlannerStep implementation for LlamaIndex Workflow-based chat agent.

This module implements the core planning logic that converts user intent into
structured execution plans, determines routing strategies, and handles re-planning
based on new information.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from llama_index.core.workflow import Context, step
from llama_index.core.llms import LLM

from .base_step import BaseWorkflowStep
from services.chat.events import (
    UserInputEvent,
    ToolExecutionRequestedEvent,
    ClarificationRequestedEvent,
    ExecutionPlan,
    ClarificationRequest,
    WorkflowMetadata
)


class PlannerStep(BaseWorkflowStep):
    """
    Workflow step that analyzes user intent and creates execution plans.
    
    The PlannerStep is responsible for:
    - Converting user messages into structured execution plans
    - Determining confidence levels and clarification needs
    - Setting routing flags for sophisticated event routing
    - Handling re-planning based on clarification or tool results
    - Learning from user preferences and conversation history
    """
    
    def __init__(self, llm: LLM, **kwargs):
        """Initialize the planner step with LLM."""
        super().__init__(llm=llm, **kwargs)
        self._planning_cache = {}  # Cache for similar requests
        self._user_preferences = {}  # Learned user preferences
    
    @step
    async def run(self, ctx: Context, **kwargs) -> None:
        """Execute planning logic based on the incoming event."""
        if "user_input" in kwargs:
            await self._handle_user_input(ctx, kwargs["user_input"])
        else:
            self.logger.warning(f"Unexpected event types in PlannerStep: {list(kwargs.keys())}")
    
    async def _handle_user_input(self, ctx: Context, event: UserInputEvent) -> None:
        """Handle initial user input and create execution plan."""
        self.validate_required_fields(event, ["thread_id", "user_id", "message"])
        
        # Load user preferences for this user
        user_prefs = self._get_user_preferences(event.user_id)
        
        # Analyze user intent and create execution plan
        analysis = await self._analyze_user_intent(
            event.message,
            event.conversation_history,
            user_prefs
        )
        
        # Update context with user request analysis
        await self.emit_context_update(
            ctx,
            event.thread_id,
            event.user_id,
            {
                "user_request": event.message,
                "intent_analysis": analysis,
                "planning_timestamp": datetime.now().isoformat()
            },
            priority="high"
        )
        
        # Create execution plan
        execution_plan = self._create_execution_plan(analysis)
        
        # Determine if clarification is needed
        clarification_requests = self._identify_clarification_needs(analysis, execution_plan)
        
        if clarification_requests:
            # Emit clarification request with routing flags
            await self._emit_clarification_request(
                ctx, event, clarification_requests, execution_plan
            )
        else:
            # Proceed with tool execution
            await self._emit_tool_execution_requests(
                ctx, event, execution_plan
            )

    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for planning."""
        return self._user_preferences.get(user_id, {
            "communication_style": "professional",
            "urgency_preference": "medium",
            "detail_level": "standard"
        })

    async def _analyze_user_intent(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        user_prefs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze user intent using LLM."""
        # Build context from conversation history
        context = "\\n".join([
            f"{turn.get('role', 'user')}: {turn.get('content', '')}"
            for turn in conversation_history[-5:]  # Last 5 turns
        ])
        
        prompt = f"""
Analyze the user's intent and provide a structured response.

User Message: "{message}"

Conversation Context:
{context}

User Preferences:
{json.dumps(user_prefs, indent=2)}

Analyze and respond with a JSON object containing:
- "intent": Brief description of what the user wants
- "confidence": Float between 0.0-1.0 for analysis confidence  
- "entities": Dict of extracted entities (names, dates, topics, etc.)
- "requires_tools": Boolean if external tools are needed
- "complexity": "low", "medium", or "high"
- "suggested_tools": List of tool names that might be needed
- "assumptions": List of assumptions made about the request
- "clarification_points": List of things that need clarification

Respond only with valid JSON.
"""
        
        try:
            response = await self.safe_llm_call(
                prompt,
                max_tokens=1000,
                temperature=0.1,
                operation_name="intent_analysis"
            )
            
            # Parse LLM response as JSON
            analysis = json.loads(response)
            
            # Validate analysis structure
            required_keys = ["intent", "confidence", "entities", "requires_tools"]
            for key in required_keys:
                if key not in analysis:
                    analysis[key] = self._get_default_analysis_value(key)
            
            return analysis
            
        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"Failed to parse intent analysis: {e}")
            return self._get_fallback_analysis(message)

    def _get_default_analysis_value(self, key: str) -> Any:
        """Get default value for missing analysis keys."""
        defaults = {
            "intent": "unknown_request",
            "confidence": 0.5,
            "entities": {},
            "requires_tools": False,
            "complexity": "medium",
            "suggested_tools": [],
            "assumptions": [],
            "clarification_points": []
        }
        return defaults.get(key)
    
    def _get_fallback_analysis(self, message: str) -> Dict[str, Any]:
        """Get fallback analysis when LLM parsing fails."""
        return {
            "intent": f"Process request: {message[:50]}...",
            "confidence": 0.3,
            "entities": {},
            "requires_tools": True,
            "complexity": "medium",
            "suggested_tools": ["get_emails", "get_calendar_events"],
            "assumptions": ["User needs assistance with productivity task"],
            "clarification_points": ["Could you provide more specific details?"]
        }

    def _create_execution_plan(self, analysis: Dict[str, Any]) -> ExecutionPlan:
        """Create structured execution plan from analysis."""
        # Determine execution strategy based on complexity
        strategy = "parallel_preferred"
        if analysis.get("complexity") == "high" or len(analysis.get("suggested_tools", [])) > 3:
            strategy = "sequential_required"
        
        plan = ExecutionPlan(
            goal=analysis.get("intent", "Process user request"),
            confidence=analysis.get("confidence", 0.5),
            execution_strategy=strategy,
            assumptions=analysis.get("assumptions", [])
        )
        
        # Group tools into execution groups
        suggested_tools = analysis.get("suggested_tools", [])
        if suggested_tools:
            # For now, simple grouping - parallel if strategy allows
            can_parallel = strategy == "parallel_preferred"
            plan.add_task_group(
                suggested_tools,
                can_run_parallel=can_parallel
            )
        
        return plan

    def _identify_clarification_needs(
        self,
        analysis: Dict[str, Any],
        execution_plan: ExecutionPlan
    ) -> List[ClarificationRequest]:
        """Identify what clarifications are needed."""
        clarifications = []
        
        # Check if confidence is too low
        if analysis.get("confidence", 1.0) < 0.7:
            clarifications.append(ClarificationRequest(
                question="Could you provide more details about what you'd like me to do?",
                blocking=True,
                confidence_impact=0.3,
                context={"reason": "low_confidence"}
            ))
        
        # Check clarification points from analysis
        clarification_points = analysis.get("clarification_points", [])
        for point in clarification_points:
            clarifications.append(ClarificationRequest(
                question=point,
                blocking=True,
                confidence_impact=0.2,
                context={"reason": "analysis_identified"}
            ))
        
        return clarifications

    async def _emit_clarification_request(
        self,
        ctx: Context,
        original_event,
        clarification_requests: List[ClarificationRequest],
        execution_plan: ExecutionPlan
    ) -> None:
        """Emit clarification request with routing flags."""
        # Determine if this blocks planning or drafting
        blocks_planning = any(req.blocking for req in clarification_requests)
        
        event = ClarificationRequestedEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            clarification_requests=clarification_requests,
            parent_plan_event_id=f"plan_{datetime.now().isoformat()}",
            can_proceed_without=False,
            blocks_planning=blocks_planning,
            metadata=self.create_metadata(
                confidence=execution_plan.confidence,
                priority="high" if blocks_planning else "medium"
            )
        )
        
        ctx.send_event(event)
        self.logger.info(f"Emitted clarification request with {len(clarification_requests)} questions")

    async def _emit_tool_execution_requests(
        self,
        ctx: Context,
        original_event,
        execution_plan: ExecutionPlan,
        parent_event_id: Optional[str] = None
    ) -> None:
        """Emit tool execution requests with routing flags."""
        for task_group in execution_plan.task_groups:
            tools_to_execute = []
            
            for tool_name in task_group["tasks"]:
                tool_config = {
                    "tool_name": tool_name,
                    "inputs": {"goal": execution_plan.goal},
                    "execution_group_id": f"group_{datetime.now().isoformat()}"
                }
                tools_to_execute.append(tool_config)
            
            if tools_to_execute:
                # Determine routing: send to planner if confidence is low
                route_to_planner = execution_plan.confidence < 0.8
                
                execution_strategy = "parallel" if task_group["can_run_parallel"] else "sequential"
                
                event = ToolExecutionRequestedEvent(
                    thread_id=original_event.thread_id,
                    user_id=original_event.user_id,
                    tools_to_execute=tools_to_execute,
                    execution_strategy=execution_strategy,
                    parent_plan_event_id=parent_event_id or f"plan_{datetime.now().isoformat()}",
                    route_to_planner=route_to_planner,
                    priority="high" if route_to_planner else "medium",
                    metadata=self.create_metadata(
                        confidence=execution_plan.confidence,
                        priority="high"
                    )
                )
                
                ctx.send_event(event)
                self.logger.info(f"Emitted tool execution request: {len(tools_to_execute)} tools") 