"""
Unit tests for enhanced tool integration system.

Tests the EnhancedToolRegistry with workflow-specific features including
parallel execution, caching, timeout handling, and progress streaming.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from services.chat.tool_integration import (
    EnhancedToolRegistry,
    ToolMetadata,
    ToolResult,
    ExecutionHint,
    CacheEntry
)


class TestEnhancedToolRegistry:
    """Test the enhanced tool registry."""
    
    @pytest.fixture
    def registry(self):
        """Create a test registry."""
        return EnhancedToolRegistry()
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample tool metadata."""
        return ToolMetadata(
            name="test_tool",
            description="Test tool for unit tests",
            execution_hints={ExecutionHint.PARALLEL_SAFE, ExecutionHint.CACHE_FRIENDLY},
            estimated_duration=2.0,
            cache_ttl=300,
            timeout=30.0,
            retry_count=2
        )
    
    def test_register_tool_metadata(self, registry, sample_metadata):
        """Test registering tool metadata."""
        registry.register_tool_metadata(sample_metadata)
        
        retrieved = registry.get_tool_metadata("test_tool")
        assert retrieved is not None
        assert retrieved.name == "test_tool"
        assert retrieved.description == "Test tool for unit tests"
        assert ExecutionHint.PARALLEL_SAFE in retrieved.execution_hints
        assert retrieved.cache_ttl == 300
    
    def test_get_parallel_safe_tools(self, registry):
        """Test getting parallel safe tools."""
        # Register some tools
        parallel_tool = ToolMetadata(
            name="parallel_tool",
            description="Parallel safe tool",
            execution_hints={ExecutionHint.PARALLEL_SAFE}
        )
        sequential_tool = ToolMetadata(
            name="sequential_tool",
            description="Sequential only tool",
            execution_hints={ExecutionHint.SEQUENTIAL_ONLY}
        )
        
        registry.register_tool_metadata(parallel_tool)
        registry.register_tool_metadata(sequential_tool)
        
        parallel_tools = registry.get_parallel_safe_tools()
        assert "parallel_tool" in parallel_tools
        assert "sequential_tool" not in parallel_tools
    
    def test_get_tool_dependencies(self, registry):
        """Test getting tool dependencies."""
        dependent_tool = ToolMetadata(
            name="dependent_tool",
            description="Tool with dependencies",
            dependencies=["tool_a", "tool_b"]
        )
        
        registry.register_tool_metadata(dependent_tool)
        
        deps = registry.get_tool_dependencies("dependent_tool")
        assert deps == ["tool_a", "tool_b"]
        
        # Test tool with no dependencies
        empty_deps = registry.get_tool_dependencies("nonexistent_tool")
        assert empty_deps == []
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, registry):
        """Test successful tool execution."""
        # Mock a tool execution
        with patch.object(registry, '_call_real_tool', return_value={"result": "success"}):
            result = await registry.execute_tool("get_calendar_events", {"user_id": "test"})
            
            assert result.success is True
            assert result.tool_name == "get_calendar_events"
            assert result.data == {"result": "success"}
            assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_cache(self, registry):
        """Test tool execution with caching."""
        # First execution
        with patch.object(registry, '_call_real_tool', return_value={"result": "cached"}):
            result1 = await registry.execute_tool("get_calendar_events", {"user_id": "test"})
            assert result1.success is True
            assert result1.cached is True
            assert result1.cache_hit is False
        
        # Second execution should hit cache
        result2 = await registry.execute_tool("get_calendar_events", {"user_id": "test"})
        assert result2.success is True
        assert result2.cached is True
        assert result2.cache_hit is True
        assert result2.data == {"result": "cached"}
    
    @pytest.mark.asyncio
    async def test_execute_tool_error_handling(self, registry):
        """Test tool execution error handling."""
        # Mock a tool execution that raises an exception
        with patch.object(registry, '_call_real_tool', side_effect=Exception("Test error")):
            result = await registry.execute_tool("get_calendar_events", {"user_id": "test"})
            
            assert result.success is False
            assert result.error_message == "Test error"
            assert result.data is None
    
    @pytest.mark.asyncio
    async def test_execute_tools_parallel(self, registry):
        """Test parallel tool execution."""
        tool_configs = [
            {"tool_name": "get_calendar_events", "inputs": {"user_id": "test1"}},
            {"tool_name": "get_emails", "inputs": {"user_id": "test1"}},
            {"tool_name": "get_documents", "inputs": {"user_id": "test1"}}
        ]
        
        # Mock tool executions
        with patch.object(registry, '_call_real_tool', return_value={"result": "parallel"}):
            results = await registry.execute_tools_parallel(tool_configs)
            
            assert len(results) == 3
            assert "get_calendar_events" in results
            assert "get_emails" in results
            assert "get_documents" in results
            
            for result in results.values():
                assert result.success is True
                assert result.data == {"result": "parallel"}
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, registry):
        """Test progress callback functionality."""
        progress_updates = []
        
        async def progress_callback(message: str, progress: float):
            progress_updates.append((message, progress))
        
        with patch.object(registry, '_call_real_tool', return_value={"result": "with_progress"}):
            await registry.execute_tool(
                "get_calendar_events", 
                {"user_id": "test"}, 
                progress_callback=progress_callback
            )
        
        # Should have start and completion progress updates
        assert len(progress_updates) >= 2
        assert progress_updates[0][0] == "Starting get_calendar_events"
        assert progress_updates[0][1] == 0.0
        assert progress_updates[-1][0] == "Completed get_calendar_events"
        assert progress_updates[-1][1] == 1.0
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic."""
        # Create a cache entry with short TTL
        result = ToolResult(
            tool_name="test_tool",
            data={"test": "data"},
            execution_time=1.0,
            success=True
        )
        
        entry = CacheEntry(
            result=result,
            created_at=datetime.now() - timedelta(seconds=10),  # 10 seconds ago
            ttl=5  # 5 second TTL
        )
        
        assert entry.is_expired() is True
        
        # Create non-expired entry
        fresh_entry = CacheEntry(
            result=result,
            created_at=datetime.now(),
            ttl=300  # 5 minutes
        )
        
        assert fresh_entry.is_expired() is False
    
    def test_cache_entry_touch(self):
        """Test cache entry access tracking."""
        result = ToolResult(
            tool_name="test_tool",
            data={"test": "data"},
            execution_time=1.0,
            success=True
        )
        
        entry = CacheEntry(
            result=result,
            created_at=datetime.now(),
            ttl=300
        )
        
        initial_count = entry.access_count
        initial_time = entry.last_accessed
        
        entry.touch()
        
        assert entry.access_count == initial_count + 1
        assert entry.last_accessed > initial_time
    
    def test_cache_stats(self, registry):
        """Test cache statistics tracking."""
        initial_stats = registry.get_cache_stats()
        assert initial_stats["hits"] == 0
        assert initial_stats["misses"] == 0
        assert initial_stats["hit_rate"] == 0.0
    
    def test_execution_stats(self, registry):
        """Test execution statistics tracking."""
        initial_stats = registry.get_execution_stats()
        assert initial_stats == {}
        
        # Simulate updating stats
        result = ToolResult(
            tool_name="test_tool",
            data={"test": "data"},
            execution_time=2.5,
            success=True
        )
        
        registry._update_execution_stats("test_tool", result)
        
        stats = registry.get_execution_stats()
        assert "test_tool" in stats
        assert stats["test_tool"]["total_executions"] == 1
        assert stats["test_tool"]["successful_executions"] == 1
        assert stats["test_tool"]["failed_executions"] == 0
        assert stats["test_tool"]["average_duration"] == 2.5
    
    def test_clear_cache(self, registry):
        """Test cache clearing."""
        # Add something to cache
        registry._cache["test_key"] = CacheEntry(
            result=ToolResult("test", {}, 1.0, True),
            created_at=datetime.now(),
            ttl=300
        )
        
        assert len(registry._cache) == 1
        
        registry.clear_cache()
        
        assert len(registry._cache) == 0
    
    def test_prepare_tool_inputs(self, registry):
        """Test input preparation for tools."""
        # Test with minimal inputs
        inputs = {"user_id": "test"}
        prepared = registry._prepare_tool_inputs("get_calendar_events", inputs)
        
        assert "user_id" in prepared
        assert "start_date" in prepared
        assert "end_date" in prepared
        
        # Test with existing date inputs
        inputs_with_dates = {
            "user_id": "test",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
        prepared = registry._prepare_tool_inputs("get_calendar_events", inputs_with_dates)
        
        assert prepared["start_date"] == "2024-01-01"
        assert prepared["end_date"] == "2024-01-31"
    
    def test_default_metadata_initialization(self, registry):
        """Test that default tool metadata is properly initialized."""
        # Check that common tools have metadata
        calendar_metadata = registry.get_tool_metadata("get_calendar_events")
        assert calendar_metadata is not None
        assert ExecutionHint.PARALLEL_SAFE in calendar_metadata.execution_hints
        assert ExecutionHint.CACHE_FRIENDLY in calendar_metadata.execution_hints
        assert calendar_metadata.cache_ttl == 300
        
        email_metadata = registry.get_tool_metadata("get_emails")
        assert email_metadata is not None
        assert email_metadata.cache_ttl == 60
        
        # Check draft creation tools
        draft_metadata = registry.get_tool_metadata("create_draft_email")
        assert draft_metadata is not None
        assert ExecutionHint.SEQUENTIAL_ONLY in draft_metadata.execution_hints
        assert draft_metadata.cache_ttl is None  # Drafts shouldn't be cached
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, registry):
        """Test retry logic for failed tool executions."""
        call_count = 0
        
        async def failing_tool(tool_name, inputs, progress_callback=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise ConnectionError("Network error")
            return {"result": "success_after_retry"}
        
        with patch.object(registry, '_call_real_tool', side_effect=failing_tool):
            result = await registry.execute_tool("get_calendar_events", {"user_id": "test"})
            
            # Should succeed after retries
            assert result.success is True
            assert result.data == {"result": "success_after_retry"}
            assert call_count == 3  # Initial attempt + 2 retries
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, registry):
        """Test timeout handling for slow tools."""
        async def slow_tool(**kwargs):
            await asyncio.sleep(10)  # Simulate slow operation
            return {"result": "slow"}
        
        # Register tool with short timeout
        short_timeout_metadata = ToolMetadata(
            name="slow_tool",
            description="Slow tool",
            timeout=0.1  # 100ms timeout
        )
        registry.register_tool_metadata(short_timeout_metadata)
        
        with patch.object(registry, '_call_real_tool', side_effect=slow_tool):
            result = await registry.execute_tool("slow_tool", {"user_id": "test"})
            
            # Should fail due to timeout
            assert result.success is False
            assert "timeout" in result.error_message.lower() or "cancelled" in result.error_message.lower() 