"""
Enhanced ToolRegistry for LlamaIndex Workflow-based chat agent.

This module extends the existing ToolRegistry from llm_tools.py with workflow-specific
features including parallel execution hints, result caching, timeout handling,
and progress streaming integration.
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from services.chat.llm_tools import (
    ToolRegistry as BaseToolRegistry,
    get_calendar_events,
    get_emails,
    get_notes,
    get_documents,
    create_draft_email,
    delete_draft_email,
    create_draft_calendar_event,
    delete_draft_calendar_event,
    create_draft_calendar_change,
    delete_draft_calendar_change
)


class ExecutionHint(Enum):
    """Hints for tool execution optimization."""
    PARALLEL_SAFE = "parallel_safe"  # Can run in parallel with other tools
    SEQUENTIAL_ONLY = "sequential_only"  # Must run sequentially
    FAST = "fast"  # Expected to complete quickly (< 5 seconds)
    SLOW = "slow"  # Expected to take longer (> 30 seconds)
    CACHE_FRIENDLY = "cache_friendly"  # Results can be cached
    REAL_TIME = "real_time"  # Results change frequently, don't cache


@dataclass
class ToolMetadata:
    """Metadata for workflow-enhanced tools."""
    name: str
    description: str
    execution_hints: Set[ExecutionHint] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)  # Tools that must run first
    estimated_duration: float = 10.0  # Seconds
    cache_ttl: Optional[int] = None  # Cache time-to-live in seconds
    timeout: float = 300.0  # Execution timeout in seconds
    retry_count: int = 2  # Number of retries on failure
    progress_callback: Optional[Callable[[str, float], Awaitable[None]]] = None


@dataclass
class ToolResult:
    """Enhanced tool result with metadata."""
    tool_name: str
    data: Any
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    cached: bool = False
    cache_hit: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheEntry:
    """Tool result cache entry."""
    result: ToolResult
    created_at: datetime
    ttl: int  # Time to live in seconds
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    def touch(self) -> None:
        """Update access information."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class EnhancedToolRegistry:
    """
    Enhanced ToolRegistry with workflow-specific features.
    
    Extends the base ToolRegistry with:
    - Tool metadata and execution hints
    - Result caching with TTL and invalidation
    - Timeout and retry logic
    - Progress streaming hooks
    - Parallel execution optimization
    - Performance monitoring
    """
    
    def __init__(self, base_registry: Optional[BaseToolRegistry] = None):
        """Initialize enhanced tool registry."""
        self.base_registry = base_registry or BaseToolRegistry()
        self.logger = logging.getLogger(__name__)
        
        # Tool metadata registry
        self._tool_metadata: Dict[str, ToolMetadata] = {}
        
        # Result caching
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        
        # Execution tracking
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
        self._active_executions: Dict[str, asyncio.Task] = {}
        
        # Monitoring and metrics
        self._performance_metrics: Dict[str, Dict[str, Any]] = {}
        self._error_tracking: Dict[str, List[Dict[str, Any]]] = {}
        self._usage_analytics: Dict[str, Dict[str, Any]] = {}
        self._alert_thresholds = {
            "error_rate": 0.1,  # 10% error rate threshold
            "avg_duration": 30.0,  # 30 second average duration threshold
            "timeout_rate": 0.05  # 5% timeout rate threshold
        }
        
        # Initialize default tool metadata
        self._initialize_default_metadata()
    
    def register_tool_metadata(self, metadata: ToolMetadata) -> None:
        """Register metadata for a tool."""
        self._tool_metadata[metadata.name] = metadata
        self.logger.debug(f"Registered metadata for tool: {metadata.name}")
    
    def get_tool_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool."""
        return self._tool_metadata.get(tool_name)
    
    def get_parallel_safe_tools(self) -> List[str]:
        """Get list of tools that can be executed in parallel."""
        return [
            name for name, metadata in self._tool_metadata.items()
            if ExecutionHint.PARALLEL_SAFE in metadata.execution_hints
        ]
    
    def get_tool_dependencies(self, tool_name: str) -> List[str]:
        """Get dependencies for a tool."""
        metadata = self.get_tool_metadata(tool_name)
        return metadata.dependencies if metadata else []
    
    async def execute_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        use_cache: bool = True,
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]] = None
    ) -> ToolResult:
        """Execute a tool with enhanced features."""
        execution_id = f"{tool_name}_{int(time.time() * 1000)}"
        
        try:
            # Check cache first
            if use_cache:
                cache_result = await self._check_cache(tool_name, inputs)
                if cache_result:
                    return cache_result
            
            # Get tool metadata
            metadata = self.get_tool_metadata(tool_name)
            if not metadata:
                # Create default metadata for unknown tools
                metadata = ToolMetadata(
                    name=tool_name,
                    description=f"Tool: {tool_name}",
                    execution_hints={ExecutionHint.PARALLEL_SAFE}
                )
                self.register_tool_metadata(metadata)
            
            # Set up progress callback
            effective_callback = progress_callback or metadata.progress_callback
            
            # Execute with timeout and retry
            result = await self._execute_with_timeout_and_retry(
                tool_name,
                inputs,
                metadata,
                effective_callback,
                execution_id
            )
            
            # Cache result if appropriate
            if use_cache and self._should_cache_result(metadata, result):
                await self._cache_result(tool_name, inputs, result, metadata)
            
            # Update execution stats
            self._update_execution_stats(tool_name, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
            
            # Return error result
            error_result = ToolResult(
                tool_name=tool_name,
                data=None,
                execution_time=0.0,
                success=False,
                error_message=str(e)
            )
            
            self._update_execution_stats(tool_name, error_result)
            return error_result
        
        finally:
            # Clean up active execution tracking
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]
    
    async def execute_tools_parallel(
        self,
        tool_configs: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]] = None
    ) -> Dict[str, ToolResult]:
        """Execute multiple tools in parallel where possible."""
        # Separate parallel-safe and sequential tools
        parallel_tools = []
        sequential_tools = []
        
        for config in tool_configs:
            tool_name = config["tool_name"]
            metadata = self.get_tool_metadata(tool_name)
            
            if metadata and ExecutionHint.PARALLEL_SAFE in metadata.execution_hints:
                parallel_tools.append(config)
            else:
                sequential_tools.append(config)
        
        results = {}
        
        # Execute parallel tools
        if parallel_tools:
            parallel_results = await self._execute_parallel_batch(
                parallel_tools,
                progress_callback
            )
            results.update(parallel_results)
        
        # Execute sequential tools
        for config in sequential_tools:
            tool_name = config["tool_name"]
            inputs = config.get("inputs", {})
            
            result = await self.execute_tool(
                tool_name,
                inputs,
                progress_callback=progress_callback
            )
            results[tool_name] = result
        
        return results
    
    async def _execute_parallel_batch(
        self,
        tool_configs: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]] = None
    ) -> Dict[str, ToolResult]:
        """Execute a batch of tools in parallel."""
        # Create coroutines for each tool
        coroutines = []
        tool_names = []
        
        for config in tool_configs:
            tool_name = config["tool_name"]
            inputs = config.get("inputs", {})
            
            coroutine = self.execute_tool(
                tool_name,
                inputs,
                progress_callback=progress_callback
            )
            coroutines.append(coroutine)
            tool_names.append(tool_name)
        
        # Execute all tools in parallel
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Process results
        tool_results = {}
        for i, result in enumerate(results):
            tool_name = tool_names[i]
            
            if isinstance(result, Exception):
                # Handle exception as error result
                tool_results[tool_name] = ToolResult(
                    tool_name=tool_name,
                    data=None,
                    execution_time=0.0,
                    success=False,
                    error_message=str(result)
                )
            else:
                tool_results[tool_name] = result
        
        return tool_results
    
    async def _execute_with_timeout_and_retry(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        metadata: ToolMetadata,
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]],
        execution_id: str
    ) -> ToolResult:
        """Execute tool with timeout and retry logic."""
        last_exception = None
        execution_time = 0.0
        
        for attempt in range(metadata.retry_count + 1):
            try:
                if attempt > 0:
                    delay = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                    self.logger.warning(
                        f"Retrying {tool_name} (attempt {attempt + 1}/{metadata.retry_count + 1}) "
                        f"after {delay}s delay"
                    )
                    await asyncio.sleep(delay)
                
                # Execute with timeout
                start_time = time.time()
                
                # Create execution task
                execution_task = asyncio.create_task(
                    self._execute_single_tool(
                        tool_name,
                        inputs,
                        progress_callback
                    )
                )
                
                # Track active execution
                self._active_executions[execution_id] = execution_task
                
                # Wait with timeout
                try:
                    data = await asyncio.wait_for(execution_task, timeout=metadata.timeout)
                    execution_time = time.time() - start_time
                    
                    return ToolResult(
                        tool_name=tool_name,
                        data=data,
                        execution_time=execution_time,
                        success=True
                    )
                
                except asyncio.TimeoutError:
                    execution_task.cancel()
                    raise TimeoutError(f"Tool {tool_name} timed out after {metadata.timeout}s")
                
            except Exception as e:
                last_exception = e
                execution_time = time.time() - start_time
                
                if attempt == metadata.retry_count:
                    self.logger.error(f"All retry attempts failed for {tool_name}")
                    break
                
                if not self._is_retryable_error(e):
                    self.logger.error(f"Non-retryable error in {tool_name}, not retrying")
                    break
        
        # Return error result
        return ToolResult(
            tool_name=tool_name,
            data=None,
            execution_time=execution_time,
            success=False,
            error_message=str(last_exception)
        )
    
    async def _execute_single_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]]
    ) -> Any:
        """Execute a single tool using real implementations."""
        # Report progress start
        if progress_callback:
            await progress_callback(f"Starting {tool_name}", 0.0)
        
        # Execute real tool
        result = await self._call_real_tool(tool_name, inputs, progress_callback)
        
        # Report progress completion
        if progress_callback:
            await progress_callback(f"Completed {tool_name}", 1.0)
        
        return result
    
    async def _call_real_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]]
    ) -> Any:
        """Call the actual tool implementation."""
        # Map tool names to functions
        tool_functions = {
            "get_calendar_events": get_calendar_events,
            "get_emails": get_emails,
            "get_notes": get_notes,
            "get_documents": get_documents,
            "create_draft_email": create_draft_email,
            "delete_draft_email": delete_draft_email,
            "create_draft_calendar_event": create_draft_calendar_event,
            "delete_draft_calendar_event": delete_draft_calendar_event,
            "create_draft_calendar_change": create_draft_calendar_change,
            "delete_draft_calendar_change": delete_draft_calendar_change
        }
        
        if tool_name not in tool_functions:
            # Fall back to base registry for unknown tools
            try:
                tool_func = self.base_registry.get_tool(tool_name)
                if tool_func:
                    # Execute tool function with inputs
                    if asyncio.iscoroutinefunction(tool_func):
                        return await tool_func(**inputs)
                    else:
                        # Run sync function in executor to avoid blocking
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, lambda: tool_func(**inputs))
                else:
                    # Fall back to mock for completely unknown tools
                    return await self._mock_tool_execution(tool_name, inputs)
            except Exception as e:
                self.logger.warning(f"Base registry execution failed for {tool_name}: {e}")
                return await self._mock_tool_execution(tool_name, inputs)
        
        # Execute known tool
        tool_func = tool_functions[tool_name]
        
        # Add progress updates for longer-running tools
        if progress_callback and tool_name in ["get_calendar_events", "get_emails", "get_documents"]:
            await progress_callback(f"Retrieving {tool_name.replace('get_', '').replace('_', ' ')}", 0.5)
        
        # Prepare inputs with authentication and defaults
        prepared_inputs = self._prepare_tool_inputs(tool_name, inputs)
        
        # Execute tool function
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**prepared_inputs)
        else:
            # Run sync function in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: tool_func(**prepared_inputs))
        
        return result
    
    def _prepare_tool_inputs(self, tool_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare inputs for tool execution, adding authentication if needed."""
        prepared_inputs = inputs.copy()
        
        # Add user authentication context if available
        if "user_id" in inputs and "access_token" not in inputs:
            # In a real implementation, this would fetch the user's access token
            # For now, we pass through the inputs as-is
            pass
        
        # Ensure required parameters are present for specific tools
        if tool_name in ["get_calendar_events", "get_emails", "get_documents", "get_notes"]:
            # These tools typically need date ranges or filters
            if "start_date" not in prepared_inputs:
                prepared_inputs["start_date"] = datetime.now().strftime("%Y-%m-%d")
            if "end_date" not in prepared_inputs:
                # Default to 30 days from now
                end_date = datetime.now() + timedelta(days=30)
                prepared_inputs["end_date"] = end_date.strftime("%Y-%m-%d")
        
        return prepared_inputs
    
    async def _mock_tool_execution(self, tool_name: str, inputs: Dict[str, Any]) -> Any:
        """Mock tool execution for testing - replace with real implementation."""
        # Simulate tool execution time
        metadata = self.get_tool_metadata(tool_name)
        duration = metadata.estimated_duration if metadata else 1.0
        
        # Simulate realistic execution time with some variance
        actual_duration = duration * (0.5 + 0.5 * (time.time() % 1))
        await asyncio.sleep(min(actual_duration, 0.1))  # Cap at 0.1s for testing
        
        return {
            "tool": tool_name,
            "inputs": inputs,
            "result": f"Mock result from {tool_name}",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _check_cache(self, tool_name: str, inputs: Dict[str, Any]) -> Optional[ToolResult]:
        """Check if tool result is cached."""
        cache_key = self._create_cache_key(tool_name, inputs)
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            
            if not entry.is_expired():
                entry.touch()
                self._cache_stats["hits"] += 1
                
                # Create cache hit result
                cached_result = ToolResult(
                    tool_name=entry.result.tool_name,
                    data=entry.result.data,
                    execution_time=entry.result.execution_time,
                    success=entry.result.success,
                    error_message=entry.result.error_message,
                    cached=True,
                    cache_hit=True,
                    timestamp=entry.result.timestamp,
                    metadata=entry.result.metadata
                )
                
                self.logger.debug(f"Cache hit for {tool_name}")
                return cached_result
            else:
                # Remove expired entry
                del self._cache[cache_key]
                self._cache_stats["evictions"] += 1
        
        self._cache_stats["misses"] += 1
        return None
    
    async def _cache_result(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        result: ToolResult,
        metadata: ToolMetadata
    ) -> None:
        """Cache tool result."""
        if not metadata.cache_ttl:
            return
        
        cache_key = self._create_cache_key(tool_name, inputs)
        
        # Mark result as cached
        result.cached = True
        
        # Create cache entry
        entry = CacheEntry(
            result=result,
            created_at=datetime.now(),
            ttl=metadata.cache_ttl
        )
        
        self._cache[cache_key] = entry
        self.logger.debug(f"Cached result for {tool_name} (TTL: {metadata.cache_ttl}s)")
    
    def _create_cache_key(self, tool_name: str, inputs: Dict[str, Any]) -> str:
        """Create cache key for tool execution."""
        # Create a stable hash from tool name and inputs
        stable_inputs = {k: v for k, v in inputs.items() 
                        if k not in ["thread_id", "execution_id", "timestamp"]}
        return f"{tool_name}_{hash(str(sorted(stable_inputs.items())))}"
    
    def _should_cache_result(self, metadata: ToolMetadata, result: ToolResult) -> bool:
        """Determine if result should be cached."""
        return (
            result.success and
            metadata.cache_ttl is not None and
            ExecutionHint.CACHE_FRIENDLY in metadata.execution_hints and
            ExecutionHint.REAL_TIME not in metadata.execution_hints
        )
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if error is retryable."""
        retryable_patterns = [
            "timeout", "connection", "network", "503", "502", "429",
            "ConnectionError", "TimeoutError", "TemporaryFailure"
        ]
        
        error_str = str(error).lower()
        return any(pattern.lower() in error_str for pattern in retryable_patterns)
    
    def _update_execution_stats(self, tool_name: str, result: ToolResult) -> None:
        """Update execution statistics and monitoring metrics."""
        if tool_name not in self._execution_stats:
            self._execution_stats[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "timeout_executions": 0,
                "total_duration": 0.0,
                "average_duration": 0.0,
                "cache_hits": 0,
                "last_execution": None,
                "error_rate": 0.0,
                "timeout_rate": 0.0
            }
        
        stats = self._execution_stats[tool_name]
        stats["total_executions"] += 1
        stats["total_duration"] += result.execution_time
        stats["last_execution"] = result.timestamp.isoformat()
        
        if result.success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
            
            # Track error details
            self._track_error(tool_name, result)
        
        # Check for timeout errors
        if result.error_message and "timeout" in result.error_message.lower():
            stats["timeout_executions"] += 1
        
        if result.cache_hit:
            stats["cache_hits"] += 1
        
        # Update calculated metrics
        stats["average_duration"] = stats["total_duration"] / stats["total_executions"]
        stats["error_rate"] = stats["failed_executions"] / stats["total_executions"]
        stats["timeout_rate"] = stats["timeout_executions"] / stats["total_executions"]
        
        # Update performance metrics
        self._update_performance_metrics(tool_name, result)
        
        # Update usage analytics
        self._update_usage_analytics(tool_name, result)
        
        # Check for alerts
        self._check_alert_thresholds(tool_name, stats)
    
    def _initialize_default_metadata(self) -> None:
        """Initialize default metadata for common tools."""
        default_tools = [
            ToolMetadata(
                name="get_calendar_events",
                description="Retrieve calendar events",
                execution_hints={ExecutionHint.PARALLEL_SAFE, ExecutionHint.CACHE_FRIENDLY},
                estimated_duration=3.0,
                cache_ttl=300  # 5 minutes
            ),
            ToolMetadata(
                name="get_emails",
                description="Retrieve emails",
                execution_hints={ExecutionHint.PARALLEL_SAFE, ExecutionHint.CACHE_FRIENDLY},
                estimated_duration=5.0,
                cache_ttl=60  # 1 minute
            ),
            ToolMetadata(
                name="get_notes",
                description="Retrieve notes",
                execution_hints={ExecutionHint.PARALLEL_SAFE, ExecutionHint.CACHE_FRIENDLY},
                estimated_duration=2.0,
                cache_ttl=300  # 5 minutes
            ),
            ToolMetadata(
                name="get_documents",
                description="Retrieve documents",
                execution_hints={ExecutionHint.PARALLEL_SAFE, ExecutionHint.CACHE_FRIENDLY},
                estimated_duration=4.0,
                cache_ttl=600  # 10 minutes
            ),
            ToolMetadata(
                name="create_draft_email",
                description="Create email draft",
                execution_hints={ExecutionHint.SEQUENTIAL_ONLY, ExecutionHint.FAST},
                estimated_duration=2.0,
                cache_ttl=None  # Don't cache drafts
            ),
            ToolMetadata(
                name="delete_draft_email",
                description="Delete email draft",
                execution_hints={ExecutionHint.SEQUENTIAL_ONLY, ExecutionHint.FAST},
                estimated_duration=1.0,
                cache_ttl=None  # Don't cache deletions
            ),
            ToolMetadata(
                name="create_draft_calendar_event",
                description="Create calendar event draft",
                execution_hints={ExecutionHint.SEQUENTIAL_ONLY, ExecutionHint.FAST},
                estimated_duration=2.0,
                cache_ttl=None  # Don't cache drafts
            ),
            ToolMetadata(
                name="delete_draft_calendar_event",
                description="Delete calendar event draft",
                execution_hints={ExecutionHint.SEQUENTIAL_ONLY, ExecutionHint.FAST},
                estimated_duration=1.0,
                cache_ttl=None  # Don't cache deletions
            ),
            ToolMetadata(
                name="create_draft_calendar_change",
                description="Create calendar change draft",
                execution_hints={ExecutionHint.SEQUENTIAL_ONLY, ExecutionHint.FAST},
                estimated_duration=2.0,
                cache_ttl=None  # Don't cache drafts
            ),
            ToolMetadata(
                name="delete_draft_calendar_change",
                description="Delete calendar change draft",
                execution_hints={ExecutionHint.SEQUENTIAL_ONLY, ExecutionHint.FAST},
                estimated_duration=1.0,
                cache_ttl=None  # Don't cache deletions
            )
        ]
        
        for metadata in default_tools:
            self.register_tool_metadata(metadata)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = self._cache_stats["hits"] / total_requests if total_requests > 0 else 0.0
        
        return {
            **self._cache_stats,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache),
            "total_requests": total_requests
        }
    
    def get_execution_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get execution statistics for all tools."""
        return self._execution_stats.copy()
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        self.logger.info("Tool result cache cleared")
    
    def cancel_active_executions(self) -> None:
        """Cancel all active tool executions."""
        for execution_id, task in self._active_executions.items():
            if not task.done():
                task.cancel()
                self.logger.info(f"Cancelled active execution: {execution_id}")
        
        self._active_executions.clear()
    
    def _track_error(self, tool_name: str, result: ToolResult) -> None:
        """Track error details for monitoring."""
        if tool_name not in self._error_tracking:
            self._error_tracking[tool_name] = []
        
        error_entry = {
            "timestamp": result.timestamp.isoformat(),
            "error_message": result.error_message,
            "execution_time": result.execution_time,
            "metadata": result.metadata
        }
        
        # Keep only last 100 errors per tool
        self._error_tracking[tool_name].append(error_entry)
        if len(self._error_tracking[tool_name]) > 100:
            self._error_tracking[tool_name] = self._error_tracking[tool_name][-100:]
    
    def _update_performance_metrics(self, tool_name: str, result: ToolResult) -> None:
        """Update performance metrics for monitoring."""
        if tool_name not in self._performance_metrics:
            self._performance_metrics[tool_name] = {
                "min_duration": float('inf'),
                "max_duration": 0.0,
                "p95_duration": 0.0,
                "p99_duration": 0.0,
                "recent_durations": [],
                "success_streak": 0,
                "failure_streak": 0,
                "last_success": None,
                "last_failure": None
            }
        
        metrics = self._performance_metrics[tool_name]
        
        # Update duration metrics
        metrics["min_duration"] = min(metrics["min_duration"], result.execution_time)
        metrics["max_duration"] = max(metrics["max_duration"], result.execution_time)
        
        # Track recent durations for percentile calculation
        metrics["recent_durations"].append(result.execution_time)
        if len(metrics["recent_durations"]) > 1000:  # Keep last 1000 executions
            metrics["recent_durations"] = metrics["recent_durations"][-1000:]
        
        # Calculate percentiles
        if len(metrics["recent_durations"]) >= 20:  # Need sufficient data
            sorted_durations = sorted(metrics["recent_durations"])
            p95_idx = int(0.95 * len(sorted_durations))
            p99_idx = int(0.99 * len(sorted_durations))
            metrics["p95_duration"] = sorted_durations[p95_idx]
            metrics["p99_duration"] = sorted_durations[p99_idx]
        
        # Update success/failure streaks
        if result.success:
            metrics["success_streak"] += 1
            metrics["failure_streak"] = 0
            metrics["last_success"] = result.timestamp.isoformat()
        else:
            metrics["failure_streak"] += 1
            metrics["success_streak"] = 0
            metrics["last_failure"] = result.timestamp.isoformat()
    
    def _update_usage_analytics(self, tool_name: str, result: ToolResult) -> None:
        """Update usage analytics for optimization insights."""
        if tool_name not in self._usage_analytics:
            self._usage_analytics[tool_name] = {
                "hourly_usage": {},
                "daily_usage": {},
                "cache_effectiveness": 0.0,
                "parallel_usage_count": 0,
                "sequential_usage_count": 0,
                "avg_inputs_size": 0,
                "total_inputs_processed": 0
            }
        
        analytics = self._usage_analytics[tool_name]
        
        # Track hourly usage
        hour_key = result.timestamp.strftime("%Y-%m-%d-%H")
        analytics["hourly_usage"][hour_key] = analytics["hourly_usage"].get(hour_key, 0) + 1
        
        # Track daily usage
        day_key = result.timestamp.strftime("%Y-%m-%d")
        analytics["daily_usage"][day_key] = analytics["daily_usage"].get(day_key, 0) + 1
        
        # Update cache effectiveness
        if result.cache_hit:
            cache_hits = sum(1 for r in [result] if r.cache_hit)
            total_executions = 1  # This execution
            analytics["cache_effectiveness"] = cache_hits / total_executions
        
        # Track input size (if available)
        if "input_size" in result.metadata:
            input_size = result.metadata["input_size"]
            analytics["total_inputs_processed"] += input_size
            analytics["avg_inputs_size"] = analytics["total_inputs_processed"] / analytics.get("executions", 1)
    
    def _check_alert_thresholds(self, tool_name: str, stats: Dict[str, Any]) -> None:
        """Check if any alert thresholds are exceeded."""
        alerts = []
        
        # Check error rate
        if stats["error_rate"] > self._alert_thresholds["error_rate"]:
            alerts.append(f"High error rate: {stats['error_rate']:.2%}")
        
        # Check average duration
        if stats["average_duration"] > self._alert_thresholds["avg_duration"]:
            alerts.append(f"High average duration: {stats['average_duration']:.2f}s")
        
        # Check timeout rate
        if stats["timeout_rate"] > self._alert_thresholds["timeout_rate"]:
            alerts.append(f"High timeout rate: {stats['timeout_rate']:.2%}")
        
        # Log alerts
        if alerts:
            self.logger.warning(f"Tool {tool_name} alerts: {', '.join(alerts)}")
    
    def get_performance_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        if tool_name:
            return self._performance_metrics.get(tool_name, {})
        return self._performance_metrics
    
    def get_error_tracking(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get error tracking information."""
        if tool_name:
            return self._error_tracking.get(tool_name, [])
        return self._error_tracking
    
    def get_usage_analytics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get usage analytics for optimization."""
        if tool_name:
            return self._usage_analytics.get(tool_name, {})
        return self._usage_analytics
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary."""
        total_executions = sum(stats["total_executions"] for stats in self._execution_stats.values())
        total_failures = sum(stats["failed_executions"] for stats in self._execution_stats.values())
        
        # Find tools with highest error rates
        high_error_tools = [
            {"tool": tool, "error_rate": stats["error_rate"]}
            for tool, stats in self._execution_stats.items()
            if stats["error_rate"] > self._alert_thresholds["error_rate"]
        ]
        
        # Find slowest tools
        slow_tools = [
            {"tool": tool, "avg_duration": stats["average_duration"]}
            for tool, stats in self._execution_stats.items()
            if stats["average_duration"] > self._alert_thresholds["avg_duration"]
        ]
        
        return {
            "total_executions": total_executions,
            "total_failures": total_failures,
            "overall_error_rate": total_failures / total_executions if total_executions > 0 else 0.0,
            "active_executions": len(self._active_executions),
            "cache_stats": self.get_cache_stats(),
            "high_error_tools": high_error_tools,
            "slow_tools": slow_tools,
            "tools_monitored": len(self._execution_stats)
        }
    
    def set_alert_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Update alert thresholds for monitoring."""
        self._alert_thresholds.update(thresholds)
        self.logger.info(f"Updated alert thresholds: {self._alert_thresholds}")
    
    def reset_metrics(self, tool_name: Optional[str] = None) -> None:
        """Reset metrics for a specific tool or all tools."""
        if tool_name:
            if tool_name in self._execution_stats:
                del self._execution_stats[tool_name]
            if tool_name in self._performance_metrics:
                del self._performance_metrics[tool_name]
            if tool_name in self._error_tracking:
                del self._error_tracking[tool_name]
            if tool_name in self._usage_analytics:
                del self._usage_analytics[tool_name]
            self.logger.info(f"Reset metrics for tool: {tool_name}")
        else:
            self._execution_stats.clear()
            self._performance_metrics.clear()
            self._error_tracking.clear()
            self._usage_analytics.clear()
            self.logger.info("Reset all tool metrics") 