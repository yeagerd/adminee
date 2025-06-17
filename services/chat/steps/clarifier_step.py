"""
ClarifierStep implementation for LlamaIndex Workflow-based chat agent.

This module implements user clarification handling with sophisticated routing,
context analysis, and intelligent decision-making about whether clarifications
resolve planning blockages or draft requirements.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from llama_index.core.workflow import Context, step
from llama_index.core.llms import LLM

from .base_step import BaseWorkflowStep
from services.chat.events import (
    ClarificationRequestedEvent,
    ClarificationReplanRequestedEvent,
    ClarificationPlannerUnblockedEvent,
    ClarificationDraftUnblockedEvent,
    ClarifierCompletedEvent,
    ClarificationRequest,
    WorkflowMetadata
)


class ClarifierStep(BaseWorkflowStep):
    """
    Workflow step that handles user clarifications with intelligent routing.
    
    The ClarifierStep is responsible for:
    - Presenting clarification questions to users
    - Analyzing user responses for intent and completeness
    - Determining sophisticated routing based on clarification type
    - Updating context with clarification insights
    - Deciding between re-planning, unblocking planning, or unblocking drafting
    - Learning from user clarification patterns
    """
    
    def __init__(self, llm: LLM, **kwargs):
        """Initialize the clarifier step with LLM."""
        super().__init__(llm=llm, **kwargs)
        self._clarification_history = {}  # Track user clarification patterns
        self._blocking_contexts = {}  # Track what each clarification blocks
    
    @step
    async def run(self, ctx: Context, **kwargs) -> None:
        """Execute clarification logic based on the incoming event."""
        if "clarification_request" in kwargs:
            await self._handle_clarification_request(ctx, kwargs["clarification_request"])
        else:
            self.logger.warning(f"Unexpected event types in ClarifierStep: {list(kwargs.keys())}")
    
    async def _handle_clarification_request(self, ctx: Context, event: ClarificationRequestedEvent) -> None:
        """Handle clarification request and manage user interaction."""
        self.validate_required_fields(
            event, 
            ["thread_id", "user_id", "clarification_requests"]
        )
        
        self.logger.info(f"Processing {len(event.clarification_requests)} clarification requests")
        
        # Store blocking context for later routing decisions
        self._blocking_contexts[event.thread_id] = {
            "blocks_planning": event.blocks_planning,
            "parent_plan_event_id": event.parent_plan_event_id,
            "original_requests": event.clarification_requests
        }
        
        # Update context with clarification initiation
        await self.emit_context_update(
            ctx,
            event.thread_id,
            event.user_id,
            {
                "clarification_initiated": True,
                "clarification_count": len(event.clarification_requests),
                "blocks_planning": event.blocks_planning,
                "clarification_timestamp": datetime.now().isoformat()
            },
            priority="high"
        )
        
        # For now, simulate user responses (in real implementation, this would be async user interaction)
        user_responses = await self._simulate_user_responses(event.clarification_requests)
        
        # Process user responses and determine routing
        await self._process_clarification_responses(
            ctx,
            event,
            user_responses
        )
    
    async def _simulate_user_responses(self, clarification_requests: List[ClarificationRequest]) -> Dict[str, str]:
        """Simulate user responses to clarification requests (for testing)."""
        # In real implementation, this would collect actual user responses
        responses = {}
        
        for i, request in enumerate(clarification_requests):
            if "details" in request.question.lower():
                responses[f"response_{i}"] = "I need help with scheduling a meeting for next week"
            elif "preferences" in request.question.lower():
                responses[f"response_{i}"] = "Please use a professional tone and include agenda items"
            else:
                responses[f"response_{i}"] = "Yes, please proceed with the suggested approach"
        
        return responses
    
    async def _process_clarification_responses(
        self,
        ctx: Context,
        original_event: ClarificationRequestedEvent,
        user_responses: Dict[str, str]
    ) -> None:
        """Process user responses and determine intelligent routing."""
        # Analyze responses for intent and completeness
        response_analysis = await self._analyze_clarification_responses(
            original_event.clarification_requests,
            user_responses
        )
        
        # Update context with response analysis
        await self.emit_context_update(
            ctx,
            original_event.thread_id,
            original_event.user_id,
            {
                "clarification_responses_received": True,
                "response_analysis": response_analysis,
                "response_count": len(user_responses),
                "analysis_timestamp": datetime.now().isoformat()
            }
        )
        
        # Determine routing based on analysis
        routing_decision = self._determine_clarification_routing(
            original_event,
            response_analysis,
            user_responses
        )
        
        # Execute routing decision
        await self._execute_clarification_routing(
            ctx,
            original_event,
            routing_decision,
            response_analysis,
            user_responses
        )
        
        # Emit completion event for collect pattern
        await self._emit_completion_event(
            ctx,
            original_event,
            routing_decision,
            response_analysis
        )
    
    async def _analyze_clarification_responses(
        self,
        original_requests: List[ClarificationRequest],
        user_responses: Dict[str, str]
    ) -> Dict[str, Any]:
        """Analyze user responses using LLM to understand intent and completeness."""
        # Build prompt for response analysis
        analysis_prompt = self._build_response_analysis_prompt(
            original_requests,
            user_responses
        )
        
        try:
            response = await self.safe_llm_call(
                analysis_prompt,
                max_tokens=800,
                temperature=0.1,
                operation_name="clarification_analysis"
            )
            
            # Parse LLM response as JSON
            analysis = json.loads(response)
            
            # Validate analysis structure
            required_keys = ["intent_changed", "planning_unblocked", "draft_ready", "confidence"]
            for key in required_keys:
                if key not in analysis:
                    analysis[key] = self._get_default_analysis_value(key)
            
            return analysis
            
        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"Failed to parse clarification analysis: {e}")
            return self._get_fallback_analysis(user_responses)
    
    def _build_response_analysis_prompt(
        self,
        original_requests: List[ClarificationRequest],
        user_responses: Dict[str, str]
    ) -> str:
        """Build prompt for analyzing clarification responses."""
        requests_text = "\\n".join([
            f"- {req.question}" for req in original_requests
        ])
        
        responses_text = "\\n".join([
            f"- {response}" for response in user_responses.values()
        ])
        
        return f"""
Analyze the user's responses to clarification requests and determine routing.

Original Clarification Questions:
{requests_text}

User Responses:
{responses_text}

Analyze and respond with a JSON object containing:
- "intent_changed": Boolean - did user fundamentally change their request?
- "planning_unblocked": Boolean - do responses unblock planning process?
- "draft_ready": Boolean - do responses provide enough info for drafting?
- "confidence": Float 0.0-1.0 - confidence in the analysis
- "key_insights": Dict of key information extracted from responses
- "routing_recommendation": "replan", "unblock_planning", or "unblock_drafting"
- "context_updates": Dict of context information to preserve

Respond only with valid JSON.
"""
    
    def _determine_clarification_routing(
        self,
        original_event: ClarificationRequestedEvent,
        response_analysis: Dict[str, Any],
        user_responses: Dict[str, str]
    ) -> Dict[str, Any]:
        """Determine sophisticated routing based on analysis."""
        routing = {
            "action": "unblock_planning",  # Default
            "reasoning": "Default routing to unblock planning",
            "confidence": response_analysis.get("confidence", 0.5)
        }
        
        # Check if user fundamentally changed their request
        if response_analysis.get("intent_changed", False):
            routing.update({
                "action": "replan",
                "reasoning": "User request fundamentally changed, need complete re-planning",
                "updated_request": self._extract_updated_request(user_responses)
            })
        
        # Check if responses indicate planning should be unblocked
        elif response_analysis.get("planning_unblocked", False):
            routing.update({
                "action": "unblock_planning",
                "reasoning": "Clarification resolved planning blockage",
                "planning_context": response_analysis.get("key_insights", {})
            })
        
        # Check if responses indicate drafting can proceed
        elif response_analysis.get("draft_ready", False) and not original_event.blocks_planning:
            routing.update({
                "action": "unblock_drafting",
                "reasoning": "Clarification provided sufficient context for drafting",
                "draft_context": response_analysis.get("key_insights", {})
            })
        
        # Use LLM recommendation if available
        llm_recommendation = response_analysis.get("routing_recommendation")
        if llm_recommendation in ["replan", "unblock_planning", "unblock_drafting"]:
            routing["action"] = llm_recommendation
            routing["reasoning"] = f"LLM recommended {llm_recommendation} routing"
        
        self.logger.info(f"Determined clarification routing: {routing['action']} - {routing['reasoning']}")
        
        return routing
    
    async def _execute_clarification_routing(
        self,
        ctx: Context,
        original_event: ClarificationRequestedEvent,
        routing_decision: Dict[str, Any],
        response_analysis: Dict[str, Any],
        user_responses: Dict[str, str]
    ) -> None:
        """Execute the determined routing action."""
        action = routing_decision["action"]
        
        if action == "replan":
            await self._emit_replan_request(
                ctx,
                original_event,
                routing_decision,
                response_analysis
            )
        
        elif action == "unblock_planning":
            await self._emit_planning_unblocked(
                ctx,
                original_event,
                routing_decision,
                response_analysis
            )
        
        elif action == "unblock_drafting":
            await self._emit_drafting_unblocked(
                ctx,
                original_event,
                routing_decision,
                response_analysis
            )
        
        else:
            self.logger.warning(f"Unknown routing action: {action}")
    
    async def _emit_replan_request(
        self,
        ctx: Context,
        original_event: ClarificationRequestedEvent,
        routing_decision: Dict[str, Any],
        response_analysis: Dict[str, Any]
    ) -> None:
        """Emit event requesting complete re-planning."""
        updated_request = routing_decision.get("updated_request", "Updated user request")
        original_request = "Original user request"  # Would extract from context in real implementation
        
        event = ClarificationReplanRequestedEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=original_event.parent_plan_event_id,
            updated_request=updated_request,
            original_request=original_request,
            clarification_insights=response_analysis.get("key_insights", {}),
            confidence_boost=routing_decision["confidence"],
            context_updates=response_analysis.get("context_updates", {}),
            metadata=self.create_metadata(
                confidence=routing_decision["confidence"],
                priority="high"
            )
        )
        
        ctx.send_event(event)
        self.logger.info("Emitted clarification replan request")
    
    async def _emit_planning_unblocked(
        self,
        ctx: Context,
        original_event: ClarificationRequestedEvent,
        routing_decision: Dict[str, Any],
        response_analysis: Dict[str, Any]
    ) -> None:
        """Emit event indicating planning can continue."""
        planning_context = routing_decision.get("planning_context", {})
        
        event = ClarificationPlannerUnblockedEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=original_event.parent_plan_event_id,
            planning_context=planning_context,
            clarification_insights=response_analysis.get("key_insights", {}),
            confidence_boost=routing_decision["confidence"],
            context_updates=response_analysis.get("context_updates", {}),
            metadata=self.create_metadata(
                confidence=routing_decision["confidence"],
                priority="high"
            )
        )
        
        ctx.send_event(event)
        self.logger.info("Emitted planning unblocked event")
    
    async def _emit_drafting_unblocked(
        self,
        ctx: Context,
        original_event: ClarificationRequestedEvent,
        routing_decision: Dict[str, Any],
        response_analysis: Dict[str, Any]
    ) -> None:
        """Emit event indicating drafting can proceed."""
        draft_context = routing_decision.get("draft_context", {})
        
        event = ClarificationDraftUnblockedEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=original_event.parent_plan_event_id,
            draft_context=draft_context,
            clarification_insights=response_analysis.get("key_insights", {}),
            confidence_boost=routing_decision["confidence"],
            context_updates=response_analysis.get("context_updates", {}),
            metadata=self.create_metadata(
                confidence=routing_decision["confidence"],
                priority="medium"
            )
        )
        
        ctx.send_event(event)
        self.logger.info("Emitted draft unblocked event")
    
    async def _emit_completion_event(
        self,
        ctx: Context,
        original_event: ClarificationRequestedEvent,
        routing_decision: Dict[str, Any],
        response_analysis: Dict[str, Any]
    ) -> None:
        """Emit completion event for collect pattern."""
        event = ClarifierCompletedEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=original_event.parent_plan_event_id,
            routing_action=routing_decision["action"],
            clarification_success=True,
            insights_extracted=response_analysis.get("key_insights", {}),
            context_updates=response_analysis.get("context_updates", {}),
            metadata=self.create_metadata(
                confidence=routing_decision["confidence"]
            )
        )
        
        ctx.send_event(event)
        self.logger.info("Emitted clarifier completion event")
    
    def _extract_updated_request(self, user_responses: Dict[str, str]) -> str:
        """Extract updated user request from responses."""
        # Combine all responses to form updated request
        combined_responses = " ".join(user_responses.values())
        
        # In real implementation, this would be more sophisticated
        if len(combined_responses) > 100:
            return combined_responses[:100] + "..."
        return combined_responses
    
    def _get_default_analysis_value(self, key: str) -> Any:
        """Get default value for missing analysis keys."""
        defaults = {
            "intent_changed": False,
            "planning_unblocked": True,
            "draft_ready": False,
            "confidence": 0.7,
            "key_insights": {},
            "routing_recommendation": "unblock_planning",
            "context_updates": {}
        }
        return defaults.get(key)
    
    def _get_fallback_analysis(self, user_responses: Dict[str, str]) -> Dict[str, Any]:
        """Get fallback analysis when LLM parsing fails."""
        return {
            "intent_changed": False,
            "planning_unblocked": True,
            "draft_ready": len(user_responses) >= 2,  # If user provided multiple responses
            "confidence": 0.5,
            "key_insights": {"user_provided_responses": len(user_responses)},
            "routing_recommendation": "unblock_planning",
            "context_updates": {"fallback_analysis": True}
        } 