"""
ToolExecutorStep implementation for LlamaIndex Workflow-based chat agent.

This module implements parallel tool execution with intelligent routing,
progress streaming, and sophisticated result aggregation.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from llama_index.core.workflow import Context, step

from .base_step import BaseWorkflowStep
from services.chat.events import (
    ToolExecutionRequestedEvent,
    ToolResultsForPlannerEvent,
    ToolResultsForDrafterEvent,
    ToolExecutorCompletedEvent
)
from services.chat.tool_integration import EnhancedToolRegistry


class ToolExecutorStep(BaseWorkflowStep):
    """
    Workflow step that executes tools in parallel with intelligent routing.
    
    The ToolExecutorStep is responsible for:
    - Parallel execution of tools with asyncio support
    - Tool result aggregation and error handling
    - Progress streaming during long-running operations
    - Dependency resolution for sequential vs parallel execution
    - Intelligent routing based on route_to_planner flag
    - Performance monitoring and optimization
    """
    
    def __init__(self, tool_registry=None, **kwargs):
        """Initialize the tool executor step."""
        super().__init__(**kwargs)
        self.tool_registry = tool_registry or EnhancedToolRegistry()
        self._execution_cache = {}  # Cache for expensive tool results
        self._tool_dependencies = {}  # Tool dependency mapping
    
    # @step  # Temporarily commented out for testing
    async def run(self, ctx: Context, **kwargs) -> None:
        """Execute tool execution logic based on the incoming event."""
        if "tool_execution" in kwargs:
            await self._handle_tool_execution_request(ctx, kwargs["tool_execution"])
        else:
            self.logger.warning(f"Unexpected event types in ToolExecutorStep: {list(kwargs.keys())}")
    
    async def _handle_tool_execution_request(self, ctx: Context, event: ToolExecutionRequestedEvent) -> None:
        """Handle tool execution request with parallel/sequential execution."""
        self.validate_required_fields(
            event, 
            ["thread_id", "user_id", "tools_to_execute", "execution_strategy"]
        )
        
        self.logger.info(
            f"Executing {len(event.tools_to_execute)} tools with {event.execution_strategy} strategy"
        )
        
        # Update context with execution start
        await self.emit_context_update(
            ctx,
            event.thread_id,
            event.user_id,
            {
                "tool_execution_started": True,
                "tools_requested": [t["tool_name"] for t in event.tools_to_execute],
                "execution_strategy": event.execution_strategy,
                "execution_timestamp": datetime.now().isoformat()
            },
            priority="high"
        )
        
        try:
            # Execute tools based on strategy
            if event.should_execute_parallel():
                tool_results, execution_success, error_messages = await self._execute_tools_parallel(
                    event.tools_to_execute,
                    event.thread_id,
                    event.user_id
                )
            else:
                tool_results, execution_success, error_messages = await self._execute_tools_sequential(
                    event.tools_to_execute,
                    event.thread_id,
                    event.user_id
                )
            
            # Update context with execution results
            await self.emit_context_update(
                ctx,
                event.thread_id,
                event.user_id,
                {
                    "tool_execution_completed": True,
                    "execution_success": execution_success,
                    "tools_executed": list(tool_results.keys()),
                    "error_count": len(error_messages),
                    "completion_timestamp": datetime.now().isoformat()
                }
            )
            
            # Route results based on route_to_planner flag
            await self._route_tool_results(
                ctx,
                event,
                tool_results,
                execution_success,
                error_messages
            )
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}", exc_info=True)
            
            # Emit error results
            await self._route_tool_results(
                ctx,
                event,
                {},
                False,
                [f"Tool execution error: {str(e)}"]
            )
    
    async def _execute_tools_parallel(
        self,
        tools_to_execute: List[Dict[str, Any]],
        thread_id: str,
        user_id: str
    ) -> Tuple[Dict[str, Any], bool, List[str]]:
        """Execute tools in parallel using asyncio."""
        self.logger.info(f"Starting parallel execution of {len(tools_to_execute)} tools")
        
        # Create progress callback for streaming updates
        progress_callback = self._create_progress_callback(thread_id, user_id, len(tools_to_execute))
        
        # Create coroutines for each tool
        tool_coroutines = []
        tool_names = []
        
        for i, tool_config in enumerate(tools_to_execute):
            tool_name = tool_config["tool_name"]
            tool_inputs = tool_config.get("inputs", {})
            
            # Add context to tool inputs
            enhanced_inputs = {
                **tool_inputs,
                "thread_id": thread_id,
                "user_id": user_id,
                "execution_group_id": tool_config.get("execution_group_id")
            }
            
            # Create tool-specific progress callback
            tool_progress_callback = self._create_tool_progress_callback(
                progress_callback, tool_name, i, len(tools_to_execute)
            )
            
            # Create coroutine for tool execution
            coroutine = self._execute_single_tool(tool_name, enhanced_inputs, tool_progress_callback)
            tool_coroutines.append(coroutine)
            tool_names.append(tool_name)
        
        # Execute all tools in parallel with timeout
        try:
            # Use timeout to prevent hanging
            timeout = 300  # 5 minutes default timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tool_coroutines, return_exceptions=True),
                timeout=timeout
            )
            
            # Process results
            tool_results = {}
            error_messages = []
            
            for i, result in enumerate(results):
                tool_name = tool_names[i]
                
                if isinstance(result, Exception):
                    error_messages.append(f"{tool_name}: {str(result)}")
                    tool_results[tool_name] = {"error": str(result)}
                else:
                    tool_results[tool_name] = result
            
            execution_success = len(error_messages) == 0
            
            self.logger.info(
                f"Parallel execution completed: {len(tool_results)} tools, "
                f"{len(error_messages)} errors"
            )
            
            return tool_results, execution_success, error_messages
            
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timed out after {timeout} seconds"
            self.logger.error(error_msg)
            return {}, False, [error_msg]
    
    async def _execute_tools_sequential(
        self,
        tools_to_execute: List[Dict[str, Any]],
        thread_id: str,
        user_id: str
    ) -> Tuple[Dict[str, Any], bool, List[str]]:
        """Execute tools sequentially with dependency handling."""
        self.logger.info(f"Starting sequential execution of {len(tools_to_execute)} tools")
        
        # Create progress callback for streaming updates
        progress_callback = self._create_progress_callback(thread_id, user_id, len(tools_to_execute))
        
        tool_results = {}
        error_messages = []
        
        for i, tool_config in enumerate(tools_to_execute):
            tool_name = tool_config["tool_name"]
            tool_inputs = tool_config.get("inputs", {})
            
            # Add context and previous results to tool inputs
            enhanced_inputs = {
                **tool_inputs,
                "thread_id": thread_id,
                "user_id": user_id,
                "execution_group_id": tool_config.get("execution_group_id"),
                "previous_results": tool_results  # Allow tools to use previous results
            }
            
            try:
                # Create tool-specific progress callback
                tool_progress_callback = self._create_tool_progress_callback(
                    progress_callback, tool_name, i, len(tools_to_execute)
                )
                
                result = await self._execute_single_tool(tool_name, enhanced_inputs, tool_progress_callback)
                tool_results[tool_name] = result
                
                self.logger.debug(f"Sequential tool {tool_name} completed successfully")
                
            except Exception as e:
                error_msg = f"{tool_name}: {str(e)}"
                error_messages.append(error_msg)
                tool_results[tool_name] = {"error": str(e)}
                
                self.logger.error(f"Sequential tool {tool_name} failed: {e}")
                
                # Decide whether to continue or stop on error
                if self._is_critical_tool(tool_name):
                    self.logger.error(f"Critical tool {tool_name} failed, stopping execution")
                    break
        
        execution_success = len(error_messages) == 0
        
        self.logger.info(
            f"Sequential execution completed: {len(tool_results)} tools, "
            f"{len(error_messages)} errors"
        )
        
        return tool_results, execution_success, error_messages
    
    async def _execute_single_tool(
        self, 
        tool_name: str, 
        inputs: Dict[str, Any],
        progress_callback=None
    ) -> Any:
        """Execute a single tool using the enhanced registry."""
        # Use the enhanced registry's built-in caching and retry logic
        result = await self.tool_registry.execute_tool(
            tool_name,
            inputs,
            use_cache=True,
            progress_callback=progress_callback
        )
        
        if result.success:
            return result.data
        else:
            raise Exception(result.error_message or f"Tool {tool_name} failed")
    
    async def _route_tool_results(
        self,
        ctx: Context,
        original_event: ToolExecutionRequestedEvent,
        tool_results: Dict[str, Any],
        execution_success: bool,
        error_messages: List[str]
    ) -> None:
        """Route tool results based on route_to_planner flag."""
        if original_event.route_to_planner:
            # Route to planner for re-planning
            await self._emit_results_for_planner(
                ctx,
                original_event,
                tool_results,
                execution_success,
                error_messages
            )
        else:
            # Route to drafter for final draft creation
            await self._emit_results_for_drafter(
                ctx,
                original_event,
                tool_results,
                execution_success,
                error_messages
            )
        
        # Also emit completion event for collect pattern
        await self._emit_completion_event(
            ctx,
            original_event,
            tool_results,
            execution_success,
            error_messages
        )
    
    async def _emit_results_for_planner(
        self,
        ctx: Context,
        original_event: ToolExecutionRequestedEvent,
        tool_results: Dict[str, Any],
        execution_success: bool,
        error_messages: List[str]
    ) -> None:
        """Emit tool results that should trigger re-planning."""
        # Analyze results for planning insights
        planning_insights = self._extract_planning_insights(tool_results)
        
        event = ToolResultsForPlannerEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=original_event.parent_plan_event_id,
            tool_results=tool_results,
            execution_success=execution_success,
            error_messages=error_messages,
            planning_insights=planning_insights,
            context_updates=self._create_context_updates(tool_results, "planner"),
            metadata=self.create_metadata(
                confidence=0.9 if execution_success else 0.3,
                priority="high"
            )
        )
        
        ctx.send_event(event)
        self.logger.info(f"Emitted tool results for planner: {len(tool_results)} tools")
    
    async def _emit_results_for_drafter(
        self,
        ctx: Context,
        original_event: ToolExecutionRequestedEvent,
        tool_results: Dict[str, Any],
        execution_success: bool,
        error_messages: List[str]
    ) -> None:
        """Emit tool results ready for draft creation."""
        # Prepare draft context from results
        draft_context = self._extract_draft_context(tool_results)
        
        event = ToolResultsForDrafterEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=original_event.parent_plan_event_id,
            tool_results=tool_results,
            execution_success=execution_success,
            error_messages=error_messages,
            draft_context=draft_context,
            context_updates=self._create_context_updates(tool_results, "drafter"),
            metadata=self.create_metadata(
                confidence=0.9 if execution_success else 0.3,
                priority="medium"
            )
        )
        
        ctx.send_event(event)
        self.logger.info(f"Emitted tool results for drafter: {len(tool_results)} tools")
    
    async def _emit_completion_event(
        self,
        ctx: Context,
        original_event: ToolExecutionRequestedEvent,
        tool_results: Dict[str, Any],
        execution_success: bool,
        error_messages: List[str]
    ) -> None:
        """Emit completion event for collect pattern."""
        event = ToolExecutorCompletedEvent(
            thread_id=original_event.thread_id,
            user_id=original_event.user_id,
            parent_request_event_id=original_event.parent_plan_event_id,
            tool_results=tool_results,
            execution_success=execution_success,
            error_messages=error_messages,
            context_updates=self._create_context_updates(tool_results, "completion"),
            metadata=self.create_metadata(
                confidence=0.9 if execution_success else 0.3
            )
        )
        
        ctx.send_event(event)
        self.logger.info(f"Emitted tool executor completion event")
    
    def _extract_planning_insights(self, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from tool results that might affect planning."""
        insights = {}
        
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" not in result:
                # Extract key insights based on tool type
                if "calendar" in tool_name.lower():
                    insights["calendar_availability"] = {"has_conflicts": False}
                elif "email" in tool_name.lower():
                    insights["email_context"] = {"new_messages": 0}
                elif "document" in tool_name.lower():
                    insights["document_context"] = {"documents_found": 1}
        
        # Determine if re-planning is needed
        insights["needs_replanning"] = self._should_replan_from_results(tool_results)
        
        return insights
    
    def _extract_draft_context(self, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context for draft creation from tool results."""
        draft_context = {}
        
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" not in result:
                # Extract draft-relevant information
                draft_context[f"{tool_name}_data"] = self._sanitize_for_draft(result)
        
        return draft_context
    
    def _create_context_updates(self, tool_results: Dict[str, Any], target: str) -> Dict[str, Any]:
        """Create context updates from tool results."""
        return {
            f"tool_results_{target}": {
                "timestamp": datetime.now().isoformat(),
                "tools_executed": list(tool_results.keys()),
                "result_count": len(tool_results)
            }
        }
    
    def _create_cache_key(self, tool_name: str, inputs: Dict[str, Any]) -> str:
        """Create cache key for tool execution."""
        # Create a hash-like key from tool name and stable inputs
        stable_inputs = {k: v for k, v in inputs.items() 
                        if k not in ["thread_id", "execution_group_id"]}
        return f"{tool_name}_{hash(str(sorted(stable_inputs.items())))}"
    
    def _is_cache_valid(self, cache_result: Dict[str, Any]) -> bool:
        """Check if cached result is still valid."""
        # Simple time-based cache validity (5 minutes)
        cache_time = cache_result.get("timestamp")
        if not cache_time:
            return False
        
        age = (datetime.now() - cache_time).total_seconds()
        return age < 300  # 5 minutes
    
    def _should_cache_result(self, tool_name: str, result: Any) -> bool:
        """Determine if tool result should be cached."""
        # Cache static/slow-changing data, not real-time data
        cacheable_tools = {
            "get_user_preferences",
            "get_documents",
            "search_knowledge_base"
        }
        return tool_name in cacheable_tools
    
    def _is_critical_tool(self, tool_name: str) -> bool:
        """Determine if tool is critical for workflow continuation."""
        critical_tools = {
            "authenticate_user",
            "get_user_context"
        }
        return tool_name in critical_tools
    
    def _should_replan_from_results(self, tool_results: Dict[str, Any]) -> bool:
        """Determine if tool results indicate need for re-planning."""
        # Simple heuristic - if any tool returns unexpected structure or errors
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" in result:
                return True
            # Add more sophisticated analysis here
        return False
    
    def _sanitize_for_draft(self, result: Any) -> Any:
        """Sanitize tool results for draft creation."""
        # Remove sensitive information, format for readability
        if isinstance(result, dict):
            return {k: v for k, v in result.items() 
                   if not k.startswith("_") and k != "auth_token"}
        return result
    
    def _create_progress_callback(self, thread_id: str, user_id: str, total_tools: int):
        """Create progress callback for streaming updates."""
        async def progress_callback(message: str, progress: float):
            """Progress callback that can be used for streaming."""
            # This would integrate with the streaming system
            # For now, just log the progress
            self.logger.info(f"Tool execution progress: {message} ({progress:.1%})")
            
            # In a real implementation, this would emit progress events
            # to the streaming system for real-time user updates
            
        return progress_callback
    
    def _create_tool_progress_callback(
        self, 
        main_callback, 
        tool_name: str, 
        tool_index: int, 
        total_tools: int
    ):
        """Create tool-specific progress callback."""
        async def tool_progress_callback(message: str, tool_progress: float):
            """Tool-specific progress callback."""
            # Calculate overall progress
            base_progress = tool_index / total_tools
            tool_contribution = (1.0 / total_tools) * tool_progress
            overall_progress = base_progress + tool_contribution
            
            # Create tool-specific message
            tool_message = f"{tool_name}: {message}"
            
            # Call main progress callback
            await main_callback(tool_message, overall_progress)
            
        return tool_progress_callback
    
    async def _stream_progress_update(
        self,
        thread_id: str,
        user_id: str,
        step_name: str,
        progress: float,
        message: str
    ) -> None:
        """Stream progress update to user (placeholder for streaming integration)."""
        # This would integrate with the streaming system
        # For now, just log the progress
        self.logger.info(f"Progress update for {thread_id}: {step_name} - {message} ({progress:.1%})")
        
        # In a real implementation, this would:
        # 1. Get streaming orchestrator from context
        # 2. Send progress update to user via WebSocket/SSE
        # 3. Update progress tracking state 