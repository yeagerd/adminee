"""
Streaming Progress and Communication Layer for LlamaIndex Workflow-based chat agent.

This module implements real-time progress updates, bidirectional clarification routing,
and WebSocket/SSE connection management for the workflow system.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid


class MessageType(Enum):
    """Types of streaming messages."""
    PROGRESS_UPDATE = "progress_update"
    CLARIFICATION_REQUEST = "clarification_request"
    CLARIFICATION_RESPONSE = "clarification_response"
    DRAFT_PREVIEW = "draft_preview"
    ERROR_MESSAGE = "error_message"
    STATUS_UPDATE = "status_update"
    WORKFLOW_COMPLETE = "workflow_complete"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class StreamingMessage:
    """Message for streaming communication."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.STATUS_UPDATE
    priority: MessagePriority = MessagePriority.MEDIUM
    thread_id: str = ""
    user_id: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    timeout_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "requires_response": self.requires_response,
            "timeout_seconds": self.timeout_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamingMessage":
        """Create message from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MessageType(data.get("type", "status_update")),
            priority=MessagePriority(data.get("priority", "medium")),
            thread_id=data.get("thread_id", ""),
            user_id=data.get("user_id", ""),
            content=data.get("content", {}),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            requires_response=data.get("requires_response", False),
            timeout_seconds=data.get("timeout_seconds")
        )


@dataclass
class ProgressUpdate:
    """Progress update information."""
    step_name: str
    progress_percentage: float  # 0.0 to 1.0
    status_message: str
    estimated_remaining_seconds: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_streaming_message(self, thread_id: str, user_id: str) -> StreamingMessage:
        """Convert to streaming message."""
        return StreamingMessage(
            type=MessageType.PROGRESS_UPDATE,
            priority=MessagePriority.MEDIUM,
            thread_id=thread_id,
            user_id=user_id,
            content={
                "step_name": self.step_name,
                "progress_percentage": self.progress_percentage,
                "status_message": self.status_message,
                "estimated_remaining_seconds": self.estimated_remaining_seconds,
                "details": self.details
            }
        )


@dataclass
class ClarificationQuestion:
    """Clarification question for user."""
    question_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str = ""
    question_type: str = "text"  # text, choice, boolean
    options: List[str] = field(default_factory=list)  # For choice questions
    required: bool = True
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_streaming_message(self, thread_id: str, user_id: str, timeout: float = 300.0) -> StreamingMessage:
        """Convert to streaming message."""
        return StreamingMessage(
            type=MessageType.CLARIFICATION_REQUEST,
            priority=MessagePriority.HIGH,
            thread_id=thread_id,
            user_id=user_id,
            content={
                "question_id": self.question_id,
                "question_text": self.question_text,
                "question_type": self.question_type,
                "options": self.options,
                "required": self.required,
                "context": self.context
            },
            requires_response=True,
            timeout_seconds=timeout
        )


class ConnectionManager:
    """Manages WebSocket/SSE connections for streaming."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.logger = logging.getLogger(__name__)
        self._connections: Dict[str, Dict[str, Any]] = {}  # user_id -> connection info
        self._message_handlers: Dict[MessageType, List[Callable]] = {}
        self._connection_callbacks: List[Callable] = []
        self._disconnection_callbacks: List[Callable] = []
    
    def register_connection(
        self,
        user_id: str,
        connection_id: str,
        send_callback: Callable[[str], Awaitable[None]],
        connection_type: str = "websocket"
    ) -> None:
        """Register a new connection."""
        self._connections[user_id] = {
            "connection_id": connection_id,
            "send_callback": send_callback,
            "connection_type": connection_type,
            "connected_at": datetime.now(),
            "last_ping": datetime.now(),
            "message_queue": []
        }
        
        self.logger.info(f"Registered {connection_type} connection for user {user_id}")
        
        # Notify connection callbacks
        for callback in self._connection_callbacks:
            asyncio.create_task(callback(user_id, connection_id))
    
    def unregister_connection(self, user_id: str) -> None:
        """Unregister a connection."""
        if user_id in self._connections:
            connection_info = self._connections.pop(user_id)
            self.logger.info(f"Unregistered connection for user {user_id}")
            
            # Notify disconnection callbacks
            for callback in self._disconnection_callbacks:
                asyncio.create_task(callback(user_id, connection_info["connection_id"]))
    
    def is_connected(self, user_id: str) -> bool:
        """Check if user is connected."""
        return user_id in self._connections
    
    async def send_message(self, user_id: str, message: StreamingMessage) -> bool:
        """Send message to user if connected."""
        if not self.is_connected(user_id):
            self.logger.warning(f"User {user_id} not connected, queueing message")
            return False
        
        connection = self._connections[user_id]
        
        try:
            message_json = json.dumps(message.to_dict())
            await connection["send_callback"](message_json)
            
            self.logger.debug(f"Sent {message.type.value} message to user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message to user {user_id}: {e}")
            # Remove failed connection
            self.unregister_connection(user_id)
            return False
    
    async def broadcast_message(self, message: StreamingMessage, exclude_users: List[str] = None) -> int:
        """Broadcast message to all connected users."""
        exclude_users = exclude_users or []
        sent_count = 0
        
        for user_id in list(self._connections.keys()):
            if user_id not in exclude_users:
                if await self.send_message(user_id, message):
                    sent_count += 1
        
        return sent_count
    
    def add_message_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Add handler for specific message type."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        
        self._message_handlers[message_type].append(handler)
    
    async def handle_incoming_message(self, user_id: str, message_data: Dict[str, Any]) -> None:
        """Handle incoming message from user."""
        try:
            message = StreamingMessage.from_dict(message_data)
            
            # Update connection ping
            if user_id in self._connections:
                self._connections[user_id]["last_ping"] = datetime.now()
            
            # Route to appropriate handlers
            handlers = self._message_handlers.get(message.type, [])
            for handler in handlers:
                try:
                    await handler(user_id, message)
                except Exception as e:
                    self.logger.error(f"Message handler error: {e}", exc_info=True)
        
        except Exception as e:
            self.logger.error(f"Failed to handle incoming message: {e}", exc_info=True)


class ProgressTracker:
    """Tracks and aggregates progress across workflow steps."""
    
    def __init__(self, connection_manager: ConnectionManager):
        """Initialize progress tracker."""
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
        
        # Progress tracking
        self._step_progress: Dict[str, Dict[str, Any]] = {}  # thread_id -> step progress
        self._overall_progress: Dict[str, float] = {}  # thread_id -> overall progress
        self._step_weights: Dict[str, float] = {
            "PlannerStep": 0.1,
            "ToolExecutorStep": 0.6,
            "ClarifierStep": 0.1,
            "DraftBuilderStep": 0.2
        }
    
    async def update_step_progress(
        self,
        thread_id: str,
        user_id: str,
        step_name: str,
        progress: float,
        status_message: str,
        estimated_remaining: Optional[float] = None
    ) -> None:
        """Update progress for a specific step."""
        # Initialize thread progress if needed
        if thread_id not in self._step_progress:
            self._step_progress[thread_id] = {}
        
        # Update step progress
        self._step_progress[thread_id][step_name] = {
            "progress": progress,
            "status_message": status_message,
            "estimated_remaining": estimated_remaining,
            "last_updated": datetime.now()
        }
        
        # Calculate overall progress
        overall_progress = self._calculate_overall_progress(thread_id)
        self._overall_progress[thread_id] = overall_progress
        
        # Create progress update
        progress_update = ProgressUpdate(
            step_name=step_name,
            progress_percentage=progress,
            status_message=status_message,
            estimated_remaining_seconds=estimated_remaining,
            details={
                "overall_progress": overall_progress,
                "active_step": step_name
            }
        )
        
        # Send progress update
        message = progress_update.to_streaming_message(thread_id, user_id)
        await self.connection_manager.send_message(user_id, message)
        
        self.logger.debug(f"Updated progress for {step_name}: {progress:.1%}")
    
    def _calculate_overall_progress(self, thread_id: str) -> float:
        """Calculate overall workflow progress."""
        if thread_id not in self._step_progress:
            return 0.0
        
        step_progress = self._step_progress[thread_id]
        total_weighted_progress = 0.0
        total_weight = 0.0
        
        for step_name, weight in self._step_weights.items():
            if step_name in step_progress:
                progress = step_progress[step_name]["progress"]
                total_weighted_progress += progress * weight
                total_weight += weight
        
        return total_weighted_progress / total_weight if total_weight > 0 else 0.0
    
    def get_thread_progress(self, thread_id: str) -> Dict[str, Any]:
        """Get current progress for a thread."""
        return {
            "thread_id": thread_id,
            "overall_progress": self._overall_progress.get(thread_id, 0.0),
            "step_progress": self._step_progress.get(thread_id, {}),
            "last_updated": max(
                [step["last_updated"] for step in self._step_progress.get(thread_id, {}).values()],
                default=datetime.now()
            )
        }


class ClarificationManager:
    """Manages bidirectional clarification communication."""
    
    def __init__(self, connection_manager: ConnectionManager):
        """Initialize clarification manager."""
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
        
        # Pending clarifications
        self._pending_clarifications: Dict[str, Dict[str, Any]] = {}  # question_id -> clarification info
        self._response_futures: Dict[str, asyncio.Future] = {}  # question_id -> future
        
        # Register message handler for clarification responses
        connection_manager.add_message_handler(
            MessageType.CLARIFICATION_RESPONSE,
            self._handle_clarification_response
        )
    
    async def request_clarification(
        self,
        thread_id: str,
        user_id: str,
        questions: List[ClarificationQuestion],
        timeout: float = 300.0
    ) -> Dict[str, Any]:
        """Request clarification from user and wait for response."""
        clarification_id = str(uuid.uuid4())
        
        # Create futures for responses
        question_futures = {}
        for question in questions:
            future = asyncio.Future()
            self._response_futures[question.question_id] = future
            question_futures[question.question_id] = future
            
            # Track pending clarification
            self._pending_clarifications[question.question_id] = {
                "clarification_id": clarification_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "question": question,
                "created_at": datetime.now(),
                "timeout": timeout
            }
        
        # Send clarification requests
        for question in questions:
            message = question.to_streaming_message(thread_id, user_id, timeout)
            await self.connection_manager.send_message(user_id, message)
        
        self.logger.info(f"Sent {len(questions)} clarification questions to user {user_id}")
        
        # Wait for all responses with timeout
        try:
            responses = await asyncio.wait_for(
                asyncio.gather(*question_futures.values()),
                timeout=timeout
            )
            
            # Map responses to question IDs
            response_map = {}
            for i, question in enumerate(questions):
                response_map[question.question_id] = responses[i]
            
            return response_map
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Clarification request timed out for user {user_id}")
            
            # Clean up pending clarifications
            for question in questions:
                self._cleanup_clarification(question.question_id)
            
            raise TimeoutError("Clarification request timed out")
    
    async def _handle_clarification_response(self, user_id: str, message: StreamingMessage) -> None:
        """Handle clarification response from user."""
        content = message.content
        question_id = content.get("question_id")
        response_data = content.get("response")
        
        if not question_id or question_id not in self._pending_clarifications:
            self.logger.warning(f"Received response for unknown question: {question_id}")
            return
        
        # Get the future for this question
        future = self._response_futures.get(question_id)
        if future and not future.done():
            future.set_result(response_data)
            self.logger.debug(f"Received clarification response for question {question_id}")
        
        # Clean up
        self._cleanup_clarification(question_id)
    
    def _cleanup_clarification(self, question_id: str) -> None:
        """Clean up clarification tracking."""
        self._pending_clarifications.pop(question_id, None)
        
        future = self._response_futures.pop(question_id, None)
        if future and not future.done():
            future.cancel()


class StreamingOrchestrator:
    """Main orchestrator for streaming functionality."""
    
    def __init__(self):
        """Initialize streaming orchestrator."""
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.connection_manager = ConnectionManager()
        self.progress_tracker = ProgressTracker(self.connection_manager)
        self.clarification_manager = ClarificationManager(self.connection_manager)
        
        # Message routing
        self._setup_message_routing()
    
    def _setup_message_routing(self) -> None:
        """Set up message routing between components."""
        # Add any additional message handlers here
        pass
    
    async def send_status_update(
        self,
        user_id: str,
        thread_id: str,
        status: str,
        priority: MessagePriority = MessagePriority.MEDIUM
    ) -> None:
        """Send status update to user."""
        message = StreamingMessage(
            type=MessageType.STATUS_UPDATE,
            priority=priority,
            thread_id=thread_id,
            user_id=user_id,
            content={"status": status}
        )
        
        await self.connection_manager.send_message(user_id, message)
    
    async def send_error_message(
        self,
        user_id: str,
        thread_id: str,
        error: str,
        error_code: Optional[str] = None
    ) -> None:
        """Send error message to user."""
        message = StreamingMessage(
            type=MessageType.ERROR_MESSAGE,
            priority=MessagePriority.HIGH,
            thread_id=thread_id,
            user_id=user_id,
            content={
                "error": error,
                "error_code": error_code
            }
        )
        
        await self.connection_manager.send_message(user_id, message)
    
    async def send_workflow_complete(
        self,
        user_id: str,
        thread_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Send workflow completion notification."""
        message = StreamingMessage(
            type=MessageType.WORKFLOW_COMPLETE,
            priority=MessagePriority.HIGH,
            thread_id=thread_id,
            user_id=user_id,
            content={"result": result}
        )
        
        await self.connection_manager.send_message(user_id, message)
    
    def get_connection_manager(self) -> ConnectionManager:
        """Get connection manager instance."""
        return self.connection_manager
    
    def get_progress_tracker(self) -> ProgressTracker:
        """Get progress tracker instance."""
        return self.progress_tracker
    
    def get_clarification_manager(self) -> ClarificationManager:
        """Get clarification manager instance."""
        return self.clarification_manager 