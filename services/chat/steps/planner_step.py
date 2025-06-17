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
    ClarificationReplanRequestedEvent,
    ToolResultsForPlannerEvent,
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
        elif "clarification_replan_requested" in kwargs:
            await self._handle_clarification_replan(ctx, kwargs["clarification_replan_requested"])
        elif "tool_results_for_planner" in kwargs:
            await self._handle_tool_results_for_planner(ctx, kwargs["tool_results_for_planner"])
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
        
        # Learn user preferences from this interaction
        await self._learn_user_preferences(
            event.user_id,
            event.conversation_history,
            event.message,
            analysis
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
            # User prefers brief communication
            if user_prefs.get("communication_style") != "brief":
                user_prefs["communication_style"] = "brief"
                self.logger.debug(f"Learned preference: user {user_id} prefers brief communication")
        elif message_length > 50:
            # User provides detailed requests
            if user_prefs.get("communication_style") != "detailed":
                user_prefs["communication_style"] = "detailed"
                self.logger.debug(f"Learned preference: user {user_id} prefers detailed communication")
        
        # Learn urgency patterns
        urgency_keywords = ["urgent", "asap", "immediately", "quickly", "rush"]
        if any(keyword in user_message.lower() for keyword in urgency_keywords):
            user_prefs["urgency_preference"] = "high"
            self.logger.debug(f"Learned preference: user {user_id} has high urgency preference")
        
        # Learn tool preferences from successful interactions
        suggested_tools = analysis.get("suggested_tools", [])
        if suggested_tools:
            current_preferred = set(user_prefs.get("preferred_tools", []))
            new_preferred = current_preferred.union(set(suggested_tools))
            user_prefs["preferred_tools"] = list(new_preferred)
        
        # Learn automation level from interaction patterns
        confirmation_keywords = ["please confirm", "check with me", "let me know"]
        if any(keyword in user_message.lower() for keyword in confirmation_keywords):
            user_prefs["confirmation_required"] = True
            user_prefs["automation_level"] = "low"
        elif "just do it" in user_message.lower() or "go ahead" in user_message.lower():
            user_prefs["confirmation_required"] = False
            user_prefs["automation_level"] = "high"
        
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
    
    async def _handle_clarification_replan(self, ctx: Context, event: ClarificationReplanRequestedEvent) -> None:
        """Handle re-planning request from clarification step."""
        self.validate_required_fields(event, ["thread_id", "user_id", "clarification_context"])
        
        self.logger.info(f"Re-planning due to clarification for thread {event.thread_id}")
        
        # Extract new information from clarification
        clarification_context = event.clarification_context
        updated_request = clarification_context.get("updated_request", "")
        clarification_responses = clarification_context.get("responses", {})
        
        # Update context with clarification information
        await self.emit_context_update(
            ctx,
            event.thread_id,
            event.user_id,
            {
                "replan_trigger": "clarification",
                "clarification_responses": clarification_responses,
                "updated_request": updated_request,
                "replan_timestamp": datetime.now().isoformat()
            },
            priority="high"
        )
        
        # Load user preferences
        user_prefs = self._get_user_preferences(event.user_id)
        
        # Re-analyze intent with new information
        combined_message = f"{updated_request}\n\nAdditional context: {json.dumps(clarification_responses)}"
        analysis = await self._analyze_user_intent(
            combined_message,
            event.conversation_history,
            user_prefs
        )
        
        # Boost confidence since we have clarification
        analysis["confidence"] = min(analysis.get("confidence", 0.5) + 0.3, 1.0)
        
        # Create new execution plan
        execution_plan = self._create_execution_plan(analysis)
        
        # Check if we need more clarification
        clarification_requests = self._identify_clarification_needs(analysis, execution_plan)
        
        if clarification_requests:
            # Still need clarification
            await self._emit_clarification_request(
                ctx, event, clarification_requests, execution_plan
            )
        else:
            # Proceed with tool execution
            await self._emit_tool_execution_requests(
                ctx, event, execution_plan, event.parent_plan_event_id
            )
    
    async def _handle_tool_results_for_planner(self, ctx: Context, event: ToolResultsForPlannerEvent) -> None:
        """Handle tool results that require re-planning."""
        self.validate_required_fields(event, ["thread_id", "user_id", "tool_results"])
        
        self.logger.info(f"Re-planning based on tool results for thread {event.thread_id}")
        
        # Update context with tool results
        await self.emit_context_update(
            ctx,
            event.thread_id,
            event.user_id,
            {
                "replan_trigger": "tool_results",
                "tool_results": event.tool_results,
                "replan_timestamp": datetime.now().isoformat()
            },
            priority="high"
        )
        
        # Analyze tool results to determine next steps
        analysis = await self._analyze_tool_results(event.tool_results, event.conversation_history)
        
        # Load user preferences
        user_prefs = self._get_user_preferences(event.user_id)
        
        # Create execution plan based on tool results
        execution_plan = self._create_execution_plan_from_tool_results(analysis, user_prefs)
        
        # Check if we need clarification based on tool results
        clarification_requests = self._identify_clarification_needs_from_tools(analysis, execution_plan)
        
        if clarification_requests:
            # Need clarification about tool results
            await self._emit_clarification_request(
                ctx, event, clarification_requests, execution_plan
            )
        else:
            # Proceed with next tool execution or drafting
            if execution_plan.task_groups:
                # More tools needed
                await self._emit_tool_execution_requests(
                    ctx, event, execution_plan, event.parent_plan_event_id
                )
            else:
                # Ready for drafting - emit event to indicate planning complete
                await self.emit_context_update(
                    ctx,
                    event.thread_id,
                    event.user_id,
                    {
                        "planning_complete": True,
                        "ready_for_drafting": True,
                        "final_execution_plan": execution_plan.to_dict()
                    },
                    priority="high"
                )
    
    async def _analyze_tool_results(
        self, 
        tool_results: Dict[str, Any], 
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Analyze tool results to determine next planning steps."""
        # Build context from conversation history
        context = "\\n".join([
            f"{turn.get('role', 'user')}: {turn.get('content', '')}"
            for turn in conversation_history[-3:]  # Last 3 turns
        ])
        
        # Format tool results for analysis
        results_summary = []
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and result.get("success"):
                results_summary.append(f"{tool_name}: {result.get('summary', 'completed successfully')}")
            else:
                results_summary.append(f"{tool_name}: failed or incomplete")
        
        prompt = f"""
Analyze the tool execution results and determine next planning steps.

Conversation Context:
{context}

Tool Results:
{chr(10).join(results_summary)}

Detailed Results:
{json.dumps(tool_results, indent=2)}

Analyze and respond with a JSON object containing:
- "next_steps": List of next actions needed
- "confidence": Float between 0.0-1.0 for analysis confidence
- "requires_more_tools": Boolean if more tools are needed
- "suggested_tools": List of additional tool names needed
- "ready_for_drafting": Boolean if we have enough info to create drafts
- "clarification_points": List of things that need clarification
- "summary": Brief summary of what was accomplished

Respond only with valid JSON.
"""
        
        try:
            response = await self.safe_llm_call(
                prompt,
                max_tokens=800,
                temperature=0.1,
                operation_name="tool_results_analysis"
            )
            
            analysis = json.loads(response)
            
            # Validate analysis structure
            required_keys = ["next_steps", "confidence", "requires_more_tools", "ready_for_drafting"]
            for key in required_keys:
                if key not in analysis:
                    analysis[key] = self._get_default_tool_analysis_value(key)
            
            return analysis
            
        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"Failed to parse tool results analysis: {e}")
            return self._get_fallback_tool_analysis()
    
    def _get_default_tool_analysis_value(self, key: str) -> Any:
        """Get default value for missing tool analysis keys."""
        defaults = {
            "next_steps": ["Review results and proceed"],
            "confidence": 0.7,
            "requires_more_tools": False,
            "suggested_tools": [],
            "ready_for_drafting": True,
            "clarification_points": [],
            "summary": "Tool execution completed"
        }
        return defaults.get(key)
    
    def _get_fallback_tool_analysis(self) -> Dict[str, Any]:
        """Get fallback analysis when tool results parsing fails."""
        return {
            "next_steps": ["Review results and proceed to drafting"],
            "confidence": 0.6,
            "requires_more_tools": False,
            "suggested_tools": [],
            "ready_for_drafting": True,
            "clarification_points": [],
            "summary": "Tool execution completed, ready for next step"
        }
    
    def _create_execution_plan_from_tool_results(
        self, 
        analysis: Dict[str, Any], 
        user_prefs: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create execution plan based on tool results analysis."""
        plan = ExecutionPlan(
            goal="Process tool results and continue workflow",
            confidence=analysis.get("confidence", 0.7),
            execution_strategy="parallel_preferred",
            assumptions=["Tool results provide sufficient context"]
        )
        
        # Add additional tools if needed
        if analysis.get("requires_more_tools", False):
            suggested_tools = analysis.get("suggested_tools", [])
            if suggested_tools:
                plan.add_task_group(
                    suggested_tools,
                    can_run_parallel=True
                )
        
        return plan
    
    def _identify_clarification_needs_from_tools(
        self,
        analysis: Dict[str, Any],
        execution_plan: ExecutionPlan
    ) -> List[ClarificationRequest]:
        """Identify clarification needs based on tool results."""
        clarifications = []
        
        # Check clarification points from analysis
        clarification_points = analysis.get("clarification_points", [])
        for point in clarification_points:
            clarifications.append(ClarificationRequest(
                question=point,
                blocking=False,  # Tool result clarifications are usually non-blocking
                confidence_impact=0.1,
                context={"reason": "tool_results_analysis"}
            ))
        
        return clarifications 