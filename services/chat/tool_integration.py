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

from services.chat.llm_tools import ToolRegistry as BaseToolRegistry


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
        """Execute a single tool using the base registry."""
        # Report progress start
        if progress_callback:
            await progress_callback(f"Starting {tool_name}", 0.0)
        
        # Execute using base registry or mock for testing
        result = await self._mock_tool_execution(tool_name, inputs)
        
        # Report progress completion
        if progress_callback:
            await progress_callback(f"Completed {tool_name}", 1.0)
        
        return result
    
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
        """Update execution statistics."""
        if tool_name not in self._execution_stats:
            self._execution_stats[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_duration": 0.0,
                "average_duration": 0.0,
                "cache_hits": 0
            }
        
        stats = self._execution_stats[tool_name]
        stats["total_executions"] += 1
        stats["total_duration"] += result.execution_time
        
        if result.success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
        
        if result.cache_hit:
            stats["cache_hits"] += 1
        
        # Update average
        stats["average_duration"] = stats["total_duration"] / stats["total_executions"]
    
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
                name="create_draft_calendar_event",
                description="Create calendar event draft",
                execution_hints={ExecutionHint.SEQUENTIAL_ONLY, ExecutionHint.FAST},
                estimated_duration=2.0,
                cache_ttl=None  # Don't cache drafts
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