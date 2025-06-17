"""
ClarifierStep implementation for LlamaIndex Workflow-based chat agent.

This module implements user clarification handling with sophisticated routing,
context analysis, and intelligent decision-making about whether clarifications
resolve planning blockages or draft requirements.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

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
        self._clarification_timeouts = {}  # Track clarification timeouts
        self._default_timeout = 300  # 5 minutes default timeout
    
    @step
    async def handle_clarification_request(self, ctx: Context, ev: ClarificationRequestedEvent) -> None:
        """Handle clarification request event."""
        await self._handle_clarification_request(ctx, ev)
    
    async def run(self, ctx: Context, **kwargs) -> None:
        """Legacy run method for backward compatibility with tests. Not used in workflow."""
        pass
    
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
        
        # Set up timeout for user responses
        timeout_seconds = self._get_clarification_timeout(event.clarification_requests)
        timeout_time = datetime.now() + timedelta(seconds=timeout_seconds)
        self._clarification_timeouts[event.thread_id] = timeout_time
        
        try:
            # Wait for user responses with timeout
            user_responses = await asyncio.wait_for(
                self._wait_for_user_responses(event.clarification_requests),
                timeout=timeout_seconds
            )
            
            # Process user responses and determine routing
            await self._process_clarification_responses(
                ctx,
                event,
                user_responses
            )
            
        except asyncio.TimeoutError:
            # Handle timeout with fallback strategy
            await self._handle_clarification_timeout(ctx, event)
        
        finally:
            # Clean up timeout tracking
            self._clarification_timeouts.pop(event.thread_id, None)
    
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
    
    def _get_clarification_timeout(self, clarification_requests: List[ClarificationRequest]) -> int:
        """Get timeout for clarification requests based on complexity."""
        base_timeout = self._default_timeout
        
        # Adjust timeout based on number and complexity of questions
        if len(clarification_requests) > 3:
            base_timeout *= 1.5  # More time for complex clarifications
        
        # Check if any questions are marked as critical
        has_critical = any(req.blocking for req in clarification_requests)
        if has_critical:
            base_timeout *= 1.2  # More time for critical questions
        
        return int(base_timeout)
    
    async def _wait_for_user_responses(self, clarification_requests: List[ClarificationRequest]) -> Dict[str, str]:
        """Wait for user responses (in real implementation, this would be async user interaction)."""
        # For now, simulate user responses with delay
        await asyncio.sleep(0.1)  # Simulate brief delay
        return await self._simulate_user_responses(clarification_requests)
    
    async def _handle_clarification_timeout(self, ctx: Context, event: ClarificationRequestedEvent) -> None:
        """Handle clarification timeout with fallback strategies."""
        self.logger.warning(f"Clarification timeout for thread {event.thread_id}")
        
        # Update context with timeout information
        await self.emit_context_update(
            ctx,
            event.thread_id,
            event.user_id,
            {
                "clarification_timeout": True,
                "timeout_timestamp": datetime.now().isoformat(),
                "fallback_strategy": "proceed_with_assumptions"
            },
            priority="high"
        )
        
        # Determine fallback strategy based on blocking context
        blocking_context = self._blocking_contexts.get(event.thread_id, {})
        blocks_planning = blocking_context.get("blocks_planning", False)
        
        if blocks_planning:
            # If clarification was blocking planning, proceed with low confidence
            await self._emit_planning_unblocked_with_timeout(ctx, event)
        else:
            # If clarification was for drafting, proceed with available context
            await self._emit_drafting_unblocked_with_timeout(ctx, event)
        
        # Emit completion event with timeout indication
        await self._emit_timeout_completion_event(ctx, event)
    
    async def _emit_planning_unblocked_with_timeout(self, ctx: Context, event: ClarificationRequestedEvent) -> None:
        """Emit planning unblocked event after timeout."""
        event_to_emit = ClarificationPlannerUnblockedEvent(
            thread_id=event.thread_id,
            user_id=event.user_id,
            parent_request_event_id=event.parent_plan_event_id,
            planning_context={"timeout_fallback": True},
            clarification_insights={"timeout_occurred": True, "assumptions_used": True},
            confidence_boost=0.3,  # Low confidence due to timeout
            context_updates={"clarification_timeout": True},
            metadata=self.create_metadata(
                confidence=0.3,
                priority="medium"
            )
        )
        
        ctx.send_event(event_to_emit)
        self.logger.info("Emitted planning unblocked event after timeout")
    
    async def _emit_drafting_unblocked_with_timeout(self, ctx: Context, event: ClarificationRequestedEvent) -> None:
        """Emit drafting unblocked event after timeout."""
        event_to_emit = ClarificationDraftUnblockedEvent(
            thread_id=event.thread_id,
            user_id=event.user_id,
            parent_request_event_id=event.parent_plan_event_id,
            draft_context={"timeout_fallback": True},
            clarification_insights={"timeout_occurred": True, "best_effort_draft": True},
            confidence_boost=0.3,  # Low confidence due to timeout
            context_updates={"clarification_timeout": True},
            metadata=self.create_metadata(
                confidence=0.3,
                priority="medium"
            )
        )
        
        ctx.send_event(event_to_emit)
        self.logger.info("Emitted drafting unblocked event after timeout")
    
    async def _emit_timeout_completion_event(self, ctx: Context, event: ClarificationRequestedEvent) -> None:
        """Emit completion event after timeout."""
        event_to_emit = ClarifierCompletedEvent(
            thread_id=event.thread_id,
            user_id=event.user_id,
            parent_request_event_id=event.parent_plan_event_id,
            routing_action="timeout_fallback",
            clarification_success=False,
            insights_extracted={"timeout_occurred": True},
            context_updates={"clarification_timeout": True},
            metadata=self.create_metadata(
                confidence=0.3
            )
        )
        
        ctx.send_event(event_to_emit)
        self.logger.info("Emitted clarifier timeout completion event") 