"""
Context Manager for LlamaIndex Workflow-based chat agent.

This module implements conversation context accumulation, user preference learning,
context persistence, and memory management across workflow steps.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid


class ContextType(Enum):
    """Types of context information."""
    USER_INPUT = "user_input"
    TOOL_RESULT = "tool_result"
    PLAN_GENERATED = "plan_generated"
    CLARIFICATION = "clarification"
    DRAFT_CREATED = "draft_created"
    USER_PREFERENCE = "user_preference"
    ERROR_CONTEXT = "error_context"
    SYSTEM_STATE = "system_state"


class PreferenceType(Enum):
    """Types of user preferences."""
    COMMUNICATION_STYLE = "communication_style"  # formal, casual, brief, detailed
    EMAIL_PREFERENCES = "email_preferences"  # signature, tone, format
    CALENDAR_PREFERENCES = "calendar_preferences"  # meeting duration, scheduling
    NOTIFICATION_PREFERENCES = "notification_preferences"  # frequency, channels
    WORKFLOW_PREFERENCES = "workflow_preferences"  # automation level, confirmation
    TOOL_PREFERENCES = "tool_preferences"  # preferred tools, settings


@dataclass
class ContextEntry:
    """Single context entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ContextType = ContextType.USER_INPUT
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    thread_id: str = ""
    user_id: str = ""
    step_name: Optional[str] = None
    confidence: float = 1.0  # Confidence in the information (0.0 to 1.0)
    expiry: Optional[datetime] = None  # When this context expires
    tags: Set[str] = field(default_factory=set)
    
    def is_expired(self) -> bool:
        """Check if context entry is expired."""
        return self.expiry is not None and datetime.now() > self.expiry
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "step_name": self.step_name,
            "confidence": self.confidence,
            "expiry": self.expiry.isoformat() if self.expiry else None,
            "tags": list(self.tags)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=ContextType(data.get("type", "user_input")),
            content=data.get("content", {}),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            thread_id=data.get("thread_id", ""),
            user_id=data.get("user_id", ""),
            step_name=data.get("step_name"),
            confidence=data.get("confidence", 1.0),
            expiry=datetime.fromisoformat(data["expiry"]) if data.get("expiry") else None,
            tags=set(data.get("tags", []))
        )


@dataclass
class UserPreference:
    """User preference entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    preference_type: PreferenceType = PreferenceType.COMMUNICATION_STYLE
    key: str = ""  # Specific preference key
    value: Any = None  # Preference value
    confidence: float = 1.0  # How confident we are in this preference
    learned: bool = False  # Whether this was learned from behavior
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0  # How often this preference has been applied
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "preference_type": self.preference_type.value,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "learned": self.learned,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreference":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            preference_type=PreferenceType(data.get("preference_type", "communication_style")),
            key=data.get("key", ""),
            value=data.get("value"),
            confidence=data.get("confidence", 1.0),
            learned=data.get("learned", False),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            usage_count=data.get("usage_count", 0)
        )


class ContextManager:
    """
    Manages conversation context and user preferences across workflow steps.
    
    Features:
    - Context accumulation across workflow steps
    - User preference learning and tracking
    - Context persistence and recovery
    - Memory management and cleanup
    - Context querying and retrieval
    """
    
    def __init__(self, max_context_entries: int = 1000, max_context_age_hours: int = 24):
        """Initialize context manager."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.max_context_entries = max_context_entries
        self.max_context_age = timedelta(hours=max_context_age_hours)
        
        # Context storage
        self._context_entries: Dict[str, List[ContextEntry]] = {}  # thread_id -> entries
        self._user_preferences: Dict[str, List[UserPreference]] = {}  # user_id -> preferences
        
        # Indexing for fast lookup
        self._entries_by_type: Dict[ContextType, List[ContextEntry]] = {}
        self._entries_by_tag: Dict[str, List[ContextEntry]] = {}
        
        # Statistics
        self._stats = {
            "total_entries": 0,
            "total_preferences": 0,
            "cleanup_runs": 0,
            "entries_cleaned": 0
        }
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired context entries."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.cleanup_expired_context()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Context cleanup error: {e}", exc_info=True)
    
    async def add_context(self, entry: ContextEntry) -> None:
        """Add context entry."""
        # Initialize thread context if needed
        if entry.thread_id not in self._context_entries:
            self._context_entries[entry.thread_id] = []
        
        # Add to main storage
        self._context_entries[entry.thread_id].append(entry)
        
        # Update indexes
        if entry.type not in self._entries_by_type:
            self._entries_by_type[entry.type] = []
        self._entries_by_type[entry.type].append(entry)
        
        for tag in entry.tags:
            if tag not in self._entries_by_tag:
                self._entries_by_tag[tag] = []
            self._entries_by_tag[tag].append(entry)
        
        # Update stats
        self._stats["total_entries"] += 1
        
        # Enforce size limits
        await self._enforce_size_limits(entry.thread_id)
        
        self.logger.debug(f"Added context entry: {entry.type.value} for thread {entry.thread_id}")
    
    async def add_user_input_context(
        self,
        thread_id: str,
        user_id: str,
        user_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContextEntry:
        """Add user input context."""
        entry = ContextEntry(
            type=ContextType.USER_INPUT,
            content={
                "message": user_message,
                "metadata": metadata or {}
            },
            thread_id=thread_id,
            user_id=user_id,
            tags={"user_input", "conversation"}
        )
        
        await self.add_context(entry)
        return entry
    
    async def add_tool_result_context(
        self,
        thread_id: str,
        user_id: str,
        tool_name: str,
        tool_result: Any,
        step_name: Optional[str] = None,
        confidence: float = 1.0
    ) -> ContextEntry:
        """Add tool result context."""
        entry = ContextEntry(
            type=ContextType.TOOL_RESULT,
            content={
                "tool_name": tool_name,
                "result": tool_result,
                "execution_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "step_name": step_name
                }
            },
            thread_id=thread_id,
            user_id=user_id,
            step_name=step_name,
            confidence=confidence,
            tags={"tool_result", tool_name, step_name} if step_name else {"tool_result", tool_name}
        )
        
        await self.add_context(entry)
        return entry
    
    async def add_clarification_context(
        self,
        thread_id: str,
        user_id: str,
        question: str,
        response: str,
        step_name: Optional[str] = None
    ) -> ContextEntry:
        """Add clarification context."""
        entry = ContextEntry(
            type=ContextType.CLARIFICATION,
            content={
                "question": question,
                "response": response,
                "clarification_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "step_name": step_name
                }
            },
            thread_id=thread_id,
            user_id=user_id,
            step_name=step_name,
            tags={"clarification", "conversation"}
        )
        
        await self.add_context(entry)
        return entry
    
    async def add_draft_context(
        self,
        thread_id: str,
        user_id: str,
        draft_type: str,
        draft_content: Dict[str, Any],
        step_name: Optional[str] = None
    ) -> ContextEntry:
        """Add draft creation context."""
        entry = ContextEntry(
            type=ContextType.DRAFT_CREATED,
            content={
                "draft_type": draft_type,
                "draft_content": draft_content,
                "draft_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "step_name": step_name
                }
            },
            thread_id=thread_id,
            user_id=user_id,
            step_name=step_name,
            tags={"draft", draft_type}
        )
        
        await self.add_context(entry)
        return entry
    
    def get_thread_context(
        self,
        thread_id: str,
        context_types: Optional[List[ContextType]] = None,
        max_entries: Optional[int] = None,
        include_expired: bool = False
    ) -> List[ContextEntry]:
        """Get context entries for a thread."""
        if thread_id not in self._context_entries:
            return []
        
        entries = self._context_entries[thread_id]
        
        # Filter by type if specified
        if context_types:
            entries = [e for e in entries if e.type in context_types]
        
        # Filter expired entries unless requested
        if not include_expired:
            entries = [e for e in entries if not e.is_expired()]
        
        # Sort by timestamp (newest first)
        entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
        
        # Limit results if specified
        if max_entries:
            entries = entries[:max_entries]
        
        return entries
    
    def get_context_by_tags(
        self,
        tags: List[str],
        thread_id: Optional[str] = None,
        max_entries: Optional[int] = None
    ) -> List[ContextEntry]:
        """Get context entries by tags."""
        # Find entries that have all specified tags
        matching_entries = []
        
        for tag in tags:
            if tag in self._entries_by_tag:
                tag_entries = self._entries_by_tag[tag]
                
                if not matching_entries:
                    matching_entries = tag_entries.copy()
                else:
                    # Intersection with previous results
                    matching_entries = [e for e in matching_entries if e in tag_entries]
        
        # Filter by thread if specified
        if thread_id:
            matching_entries = [e for e in matching_entries if e.thread_id == thread_id]
        
        # Filter expired entries
        matching_entries = [e for e in matching_entries if not e.is_expired()]
        
        # Sort by timestamp (newest first)
        matching_entries = sorted(matching_entries, key=lambda e: e.timestamp, reverse=True)
        
        # Limit results if specified
        if max_entries:
            matching_entries = matching_entries[:max_entries]
        
        return matching_entries
    
    def get_recent_context_summary(self, thread_id: str, max_entries: int = 10) -> Dict[str, Any]:
        """Get a summary of recent context for a thread."""
        entries = self.get_thread_context(thread_id, max_entries=max_entries)
        
        summary = {
            "thread_id": thread_id,
            "total_entries": len(entries),
            "context_types": {},
            "recent_activity": [],
            "key_information": {}
        }
        
        # Count by type
        for entry in entries:
            entry_type = entry.type.value
            if entry_type not in summary["context_types"]:
                summary["context_types"][entry_type] = 0
            summary["context_types"][entry_type] += 1
        
        # Recent activity (last 5 entries)
        for entry in entries[:5]:
            summary["recent_activity"].append({
                "type": entry.type.value,
                "timestamp": entry.timestamp.isoformat(),
                "step_name": entry.step_name,
                "summary": self._summarize_entry_content(entry)
            })
        
        # Extract key information
        summary["key_information"] = self._extract_key_information(entries)
        
        return summary
    
    def _summarize_entry_content(self, entry: ContextEntry) -> str:
        """Create a brief summary of entry content."""
        content = entry.content
        
        if entry.type == ContextType.USER_INPUT:
            message = content.get("message", "")
            return message[:100] + "..." if len(message) > 100 else message
        
        elif entry.type == ContextType.TOOL_RESULT:
            tool_name = content.get("tool_name", "unknown")
            return f"Tool result from {tool_name}"
        
        elif entry.type == ContextType.CLARIFICATION:
            question = content.get("question", "")
            return f"Clarification: {question[:50]}..."
        
        elif entry.type == ContextType.DRAFT_CREATED:
            draft_type = content.get("draft_type", "unknown")
            return f"Created {draft_type} draft"
        
        else:
            return f"{entry.type.value} entry"
    
    def _extract_key_information(self, entries: List[ContextEntry]) -> Dict[str, Any]:
        """Extract key information from context entries."""
        key_info = {
            "user_preferences": {},
            "important_data": {},
            "recent_tools": [],
            "clarifications": []
        }
        
        for entry in entries:
            if entry.type == ContextType.TOOL_RESULT:
                tool_name = entry.content.get("tool_name")
                if tool_name and tool_name not in key_info["recent_tools"]:
                    key_info["recent_tools"].append(tool_name)
            
            elif entry.type == ContextType.CLARIFICATION:
                key_info["clarifications"].append({
                    "question": entry.content.get("question"),
                    "response": entry.content.get("response"),
                    "timestamp": entry.timestamp.isoformat()
                })
        
        return key_info
    
    async def learn_user_preference(
        self,
        user_id: str,
        preference_type: PreferenceType,
        key: str,
        value: Any,
        confidence: float = 0.8
    ) -> UserPreference:
        """Learn a user preference from behavior."""
        # Check if preference already exists
        existing_pref = self.get_user_preference(user_id, preference_type, key)
        
        if existing_pref:
            # Update existing preference
            existing_pref.value = value
            existing_pref.confidence = min(existing_pref.confidence + 0.1, 1.0)
            existing_pref.updated_at = datetime.now()
            existing_pref.usage_count += 1
            
            self.logger.debug(f"Updated user preference: {key} = {value}")
            return existing_pref
        
        else:
            # Create new preference
            preference = UserPreference(
                user_id=user_id,
                preference_type=preference_type,
                key=key,
                value=value,
                confidence=confidence,
                learned=True
            )
            
            # Add to storage
            if user_id not in self._user_preferences:
                self._user_preferences[user_id] = []
            
            self._user_preferences[user_id].append(preference)
            self._stats["total_preferences"] += 1
            
            self.logger.debug(f"Learned new user preference: {key} = {value}")
            return preference
    
    def get_user_preference(
        self,
        user_id: str,
        preference_type: PreferenceType,
        key: str
    ) -> Optional[UserPreference]:
        """Get a specific user preference."""
        if user_id not in self._user_preferences:
            return None
        
        for pref in self._user_preferences[user_id]:
            if pref.preference_type == preference_type and pref.key == key:
                return pref
        
        return None
    
    def get_user_preferences(
        self,
        user_id: str,
        preference_type: Optional[PreferenceType] = None
    ) -> List[UserPreference]:
        """Get all preferences for a user."""
        if user_id not in self._user_preferences:
            return []
        
        preferences = self._user_preferences[user_id]
        
        if preference_type:
            preferences = [p for p in preferences if p.preference_type == preference_type]
        
        return sorted(preferences, key=lambda p: p.updated_at, reverse=True)
    
    async def cleanup_expired_context(self) -> int:
        """Clean up expired context entries."""
        cleaned_count = 0
        
        # Clean up context entries
        for thread_id in list(self._context_entries.keys()):
            entries = self._context_entries[thread_id]
            
            # Remove expired entries
            valid_entries = []
            for entry in entries:
                if entry.is_expired() or self._is_too_old(entry):
                    cleaned_count += 1
                    # Remove from indexes
                    self._remove_from_indexes(entry)
                else:
                    valid_entries.append(entry)
            
            if valid_entries:
                self._context_entries[thread_id] = valid_entries
            else:
                del self._context_entries[thread_id]
        
        # Update stats
        self._stats["cleanup_runs"] += 1
        self._stats["entries_cleaned"] += cleaned_count
        self._stats["total_entries"] -= cleaned_count
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} expired context entries")
        
        return cleaned_count
    
    def _is_too_old(self, entry: ContextEntry) -> bool:
        """Check if entry is too old based on max age."""
        return datetime.now() - entry.timestamp > self.max_context_age
    
    def _remove_from_indexes(self, entry: ContextEntry) -> None:
        """Remove entry from indexes."""
        # Remove from type index
        if entry.type in self._entries_by_type:
            try:
                self._entries_by_type[entry.type].remove(entry)
            except ValueError:
                pass
        
        # Remove from tag indexes
        for tag in entry.tags:
            if tag in self._entries_by_tag:
                try:
                    self._entries_by_tag[tag].remove(entry)
                except ValueError:
                    pass
    
    async def _enforce_size_limits(self, thread_id: str) -> None:
        """Enforce size limits for context entries."""
        if thread_id not in self._context_entries:
            return
        
        entries = self._context_entries[thread_id]
        
        if len(entries) > self.max_context_entries:
            # Keep the most recent entries
            entries_to_keep = sorted(entries, key=lambda e: e.timestamp, reverse=True)[:self.max_context_entries]
            entries_to_remove = [e for e in entries if e not in entries_to_keep]
            
            # Remove from indexes
            for entry in entries_to_remove:
                self._remove_from_indexes(entry)
            
            # Update storage
            self._context_entries[thread_id] = entries_to_keep
            
            removed_count = len(entries_to_remove)
            self._stats["total_entries"] -= removed_count
            
            self.logger.debug(f"Removed {removed_count} old entries to enforce size limit")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        return {
            **self._stats,
            "active_threads": len(self._context_entries),
            "users_with_preferences": len(self._user_preferences),
            "context_types_tracked": len(self._entries_by_type),
            "tags_tracked": len(self._entries_by_tag)
        }
    
    async def shutdown(self) -> None:
        """Shutdown context manager and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Context manager shutdown complete") 