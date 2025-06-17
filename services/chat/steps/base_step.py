"""
Base workflow step class with common functionality and error handling.

This module defines the BaseWorkflowStep class that all workflow steps inherit from,
providing consistent error handling, logging, context management, and event emission.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from llama_index.core.workflow import Event, Context
from llama_index.core.llms import LLM

from services.chat.events import (
    WorkflowMetadata,
    ContextUpdatedEvent
)


class BaseWorkflowStep(ABC):
    """
    Base class for all workflow steps with common functionality.
    
    Provides:
    - Consistent error handling and logging
    - Context management and updates
    - Event emission utilities
    - Performance monitoring
    - Retry logic for transient failures
    - LLM integration helpers
    """
    
    def __init__(self, llm: Optional[LLM] = None, **kwargs):
        """Initialize base workflow step."""
        super().__init__()
        self.llm = llm
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.step_name = self.__class__.__name__
        self._execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_duration": 0.0
        }
    
    async def emit_context_update(
        self,
        ctx: Context,
        thread_id: str,
        user_id: str,
        context_updates: Dict[str, Any],
        update_type: str = "merge",
        priority: str = "medium"
    ) -> None:
        """Emit a context update event."""
        event = ContextUpdatedEvent(
            thread_id=thread_id,
            user_id=user_id,
            context_updates=context_updates,
            update_source=self.step_name,
            update_type=update_type,
            priority=priority
        )
        ctx.send_event(event)
        self.logger.debug(f"Emitted context update: {len(context_updates)} keys")
    
    def create_metadata(
        self,
        confidence: Optional[float] = None,
        priority: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowMetadata:
        """Create workflow metadata with step information."""
        return WorkflowMetadata(
            confidence=confidence,
            priority=priority,
            parent_event_id=parent_event_id,
            context=context or {}
        )
    
    def log_step_start(self, event_type: str, event_data: Dict[str, Any]) -> str:
        """Log step execution start and return execution ID."""
        execution_id = f"{self.step_name}_{datetime.now().isoformat()}"
        self.logger.info(
            f"Starting {self.step_name} execution",
            extra={
                "execution_id": execution_id,
                "event_type": event_type,
                "thread_id": event_data.get("thread_id"),
                "user_id": event_data.get("user_id")
            }
        )
        return execution_id
    
    def log_step_success(self, execution_id: str, duration: float, result_summary: str) -> None:
        """Log successful step execution."""
        self._execution_stats["successful_executions"] += 1
        self._execution_stats["total_duration"] += duration
        
        self.logger.info(
            f"Completed {self.step_name} execution successfully",
            extra={
                "execution_id": execution_id,
                "duration_seconds": duration,
                "result_summary": result_summary
            }
        )
    
    def log_step_error(self, execution_id: str, duration: float, error: Exception) -> None:
        """Log failed step execution."""
        self._execution_stats["failed_executions"] += 1
        self._execution_stats["total_duration"] += duration
        
        self.logger.error(
            f"Failed {self.step_name} execution",
            extra={
                "execution_id": execution_id,
                "duration_seconds": duration,
                "error_type": type(error).__name__,
                "error_message": str(error)
            },
            exc_info=True
        )
    
    async def execute_with_retry(
        self,
        operation: callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        operation_name: str = "operation"
    ) -> Any:
        """Execute operation with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    self.logger.warning(
                        f"Retrying {operation_name} (attempt {attempt + 1}/{max_retries + 1}) "
                        f"after {delay}s delay"
                    )
                    await asyncio.sleep(delay)
                
                return await operation()
                
            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    self.logger.error(
                        f"All retry attempts failed for {operation_name}",
                        exc_info=True
                    )
                    break
                
                if not self._is_retryable_error(e):
                    self.logger.error(
                        f"Non-retryable error in {operation_name}, not retrying",
                        exc_info=True
                    )
                    break
        
        raise last_exception
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        # Network/API errors that might be transient
        retryable_patterns = [
            "timeout",
            "connection",
            "network",
            "503",
            "502",
            "429",  # Rate limiting
            "ConnectionError",
            "TimeoutError"
        ]
        
        error_str = str(error).lower()
        return any(pattern in error_str for pattern in retryable_patterns)
    
    async def safe_llm_call(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.1,
        operation_name: str = "LLM call"
    ) -> str:
        """Make a safe LLM call with error handling and retry."""
        if not self.llm:
            raise ValueError(f"LLM not configured for {self.step_name}")
        
        async def make_call():
            response = await self.llm.acomplete(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.text.strip()
        
        return await self.execute_with_retry(
            make_call,
            operation_name=operation_name
        )
    
    def validate_required_fields(self, event: Event, required_fields: List[str]) -> None:
        """Validate that required fields are present in the event."""
        missing_fields = []
        for field in required_fields:
            if not hasattr(event, field) or getattr(event, field) in [None, "", []]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(
                f"Missing required fields in {type(event).__name__}: {missing_fields}"
            )
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics for this step."""
        total = self._execution_stats["total_executions"]
        return {
            "step_name": self.step_name,
            "total_executions": total,
            "successful_executions": self._execution_stats["successful_executions"],
            "failed_executions": self._execution_stats["failed_executions"],
            "success_rate": (
                self._execution_stats["successful_executions"] / total
                if total > 0 else 0.0
            ),
            "average_duration": (
                self._execution_stats["total_duration"] / total
                if total > 0 else 0.0
            )
        }
    
    @abstractmethod
    async def run(self, ctx: Context, **kwargs) -> Any:
        """
        Abstract method for step execution.
        
        All concrete workflow steps must implement this method with their
        specific business logic. The base class handles timing, error logging,
        and statistics tracking.
        """
        pass
    
    async def __call__(self, ctx: Context, **kwargs) -> Any:
        """
        Execute the workflow step with timing and statistics tracking.
        
        This method wraps the concrete run() implementation with common
        functionality like timing, error handling, and statistics.
        """
        start_time = datetime.now()
        execution_id = None
        
        try:
            self._execution_stats["total_executions"] += 1
            
            # Extract event info for logging
            event_data = {}
            if kwargs:
                event = next(iter(kwargs.values()))  # Get first event
                if hasattr(event, 'thread_id'):
                    event_data['thread_id'] = event.thread_id
                if hasattr(event, 'user_id'):
                    event_data['user_id'] = event.user_id
            
            execution_id = self.log_step_start(
                type(next(iter(kwargs.values()), "unknown")).__name__,
                event_data
            )
            
            # Execute the concrete step implementation
            result = await self.run(ctx, **kwargs)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.log_step_success(
                execution_id,
                duration,
                f"Step completed with result type: {type(result).__name__}"
            )
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            if execution_id:
                self.log_step_error(execution_id, duration, e)
            raise 