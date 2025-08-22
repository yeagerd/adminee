"""
Idempotency key generation for different data types and operations.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional, Union

from services.common.events import (
    EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent
)


class IdempotencyKeyGenerator:
    """Generates idempotency keys for different event types and operations."""
    
    @staticmethod
    def generate_email_key(event: EmailEvent) -> str:
        """Generate idempotency key for email events."""
        # For emails, use provider_message_id + user_id as the base
        # This ensures uniqueness across different email providers
        base_key = f"{event.provider}:{event.email.message_id}:{event.user_id}"
        
        # For mutable data, include updated_at timestamp
        if event.operation in ["update", "delete"] and event.last_updated:
            base_key += f":{int(event.last_updated.timestamp())}"
        
        # For batch operations, include batch_id
        if event.batch_id:
            base_key += f":{event.batch_id}"
        
        return IdempotencyKeyGenerator._hash_key(base_key)
    
    @staticmethod
    def generate_calendar_key(event: CalendarEvent) -> str:
        """Generate idempotency key for calendar events."""
        # For calendar events, use provider event ID + user_id
        base_key = f"{event.provider}:{event.event.id}:{event.user_id}"
        
        # For mutable data, include updated_at timestamp
        if event.operation in ["update", "delete"] and event.last_updated:
            base_key += f":{int(event.last_updated.timestamp())}"
        
        # For batch operations, include batch_id
        if event.batch_id:
            base_key += f":{event.batch_id}"
        
        return IdempotencyKeyGenerator._hash_key(base_key)
    
    @staticmethod
    def generate_contact_key(event: ContactEvent) -> str:
        """Generate idempotency key for contact events."""
        # For contacts, use provider contact ID + user_id
        base_key = f"{event.provider}:{event.contact.id}:{event.user_id}"
        
        # For mutable data, include updated_at timestamp
        if event.operation in ["update", "delete"] and event.last_updated:
            base_key += f":{int(event.last_updated.timestamp())}"
        
        # For batch operations, include batch_id
        if event.batch_id:
            base_key += f":{event.batch_id}"
        
        return IdempotencyKeyGenerator._hash_key(base_key)
    
    @staticmethod
    def generate_document_key(event: DocumentEvent) -> str:
        """Generate idempotency key for document events."""
        # For documents, use provider document ID + user_id
        base_key = f"{event.provider}:{event.document.id}:{event.user_id}"
        
        # For mutable data, include updated_at timestamp
        if event.operation in ["update", "delete"] and event.last_updated:
            base_key += f":{int(event.last_updated.timestamp())}"
        
        # For batch operations, include batch_id
        if event.batch_id:
            base_key += f":{event.batch_id}"
        
        return IdempotencyKeyGenerator._hash_key(base_key)
    
    @staticmethod
    def generate_todo_key(event: TodoEvent) -> str:
        """Generate idempotency key for todo events."""
        # For todos, use provider todo ID + user_id
        base_key = f"{event.provider}:{event.todo.id}:{event.user_id}"
        
        # For mutable data, include updated_at timestamp
        if event.operation in ["update", "delete"] and event.last_updated:
            base_key += f":{int(event.last_updated.timestamp())}"
        
        # For batch operations, include batch_id
        if event.batch_id:
            base_key += f":{event.batch_id}"
        
        return IdempotencyKeyGenerator._hash_key(base_key)
    
    @staticmethod
    def generate_generic_key(
        event_type: str,
        event_id: str,
        user_id: str,
        provider: str,
        operation: str,
        updated_at: Optional[datetime] = None,
        batch_id: Optional[str] = None
    ) -> str:
        """Generate idempotency key for generic events."""
        base_key = f"{provider}:{event_id}:{user_id}"
        
        # For mutable data, include updated_at timestamp
        if operation in ["update", "delete"] and updated_at:
            base_key += f":{int(updated_at.timestamp())}"
        
        # For batch operations, include batch_id
        if batch_id:
            base_key += f":{batch_id}"
        
        return IdempotencyKeyGenerator._hash_key(base_key)
    
    @staticmethod
    def generate_batch_key(batch_id: str, correlation_id: Optional[str] = None) -> str:
        """Generate idempotency key for batch operations."""
        base_key = f"batch:{batch_id}"
        
        if correlation_id:
            base_key += f":{correlation_id}"
        
        return IdempotencyKeyGenerator._hash_key(base_key)
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash the key to create a consistent, fixed-length identifier."""
        return hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]
    
    @staticmethod
    def parse_key_components(key: str) -> Dict[str, Any]:
        """Parse the components of an idempotency key (for debugging)."""
        # This is a reverse operation for debugging purposes
        # In practice, the key is hashed, so we can't recover the original components
        return {
            "key": key,
            "length": len(key),
            "is_hex": all(c in '0123456789abcdef' for c in key.lower())
        }


class IdempotencyStrategy:
    """Defines idempotency strategies for different data types."""
    
    # Immutable data types (create once, never update)
    IMMUTABLE_TYPES = {
        "email": ["create"],
        "calendar": ["create"],
        "contact": ["create"],
        "document": ["create"],
        "todo": ["create"],
    }
    
    # Mutable data types (can be updated)
    MUTABLE_TYPES = {
        "email": ["update", "delete"],
        "calendar": ["update", "delete"],
        "contact": ["update", "delete"],
        "document": ["update", "delete"],
        "todo": ["update", "delete"],
    }
    
    # Batch operation types
    BATCH_TYPES = {
        "email": ["batch_create", "batch_update"],
        "calendar": ["batch_create", "batch_update"],
        "contact": ["batch_create", "batch_update"],
        "document": ["batch_create", "batch_update"],
        "todo": ["batch_create", "batch_update"],
    }
    
    @classmethod
    def is_immutable_operation(cls, data_type: str, operation: str) -> bool:
        """Check if an operation is immutable for a data type."""
        return (
            data_type in cls.IMMUTABLE_TYPES and
            operation in cls.IMMUTABLE_TYPES[data_type]
        )
    
    @classmethod
    def is_mutable_operation(cls, data_type: str, operation: str) -> bool:
        """Check if an operation is mutable for a data type."""
        return (
            data_type in cls.MUTABLE_TYPES and
            operation in cls.MUTABLE_TYPES[data_type]
        )
    
    @classmethod
    def is_batch_operation(cls, data_type: str, operation: str) -> bool:
        """Check if an operation is a batch operation for a data type."""
        return (
            data_type in cls.BATCH_TYPES and
            operation in cls.BATCH_TYPES[data_type]
        )
    
    @classmethod
    def get_key_strategy(cls, data_type: str, operation: str) -> str:
        """Get the appropriate key strategy for a data type and operation."""
        if cls.is_batch_operation(data_type, operation):
            return "batch"
        elif cls.is_immutable_operation(data_type, operation):
            return "immutable"
        elif cls.is_mutable_operation(data_type, operation):
            return "mutable"
        else:
            return "unknown"
    
    @classmethod
    def get_key_components(cls, data_type: str, operation: str) -> Dict[str, bool]:
        """Get the required components for generating an idempotency key."""
        strategy = cls.get_key_strategy(data_type, operation)
        
        if strategy == "immutable":
            return {
                "include_provider_id": True,
                "include_message_id": True,
                "include_user_id": True,
                "include_updated_at": False,
                "include_batch_id": False,
                "include_correlation_id": False,
            }
        elif strategy == "mutable":
            return {
                "include_provider_id": True,
                "include_message_id": True,
                "include_user_id": True,
                "include_updated_at": True,
                "include_batch_id": False,
                "include_correlation_id": False,
            }
        elif strategy == "batch":
            return {
                "include_provider_id": True,
                "include_message_id": False,
                "include_user_id": True,
                "include_updated_at": False,
                "include_batch_id": True,
                "include_correlation_id": True,
            }
        else:
            return {
                "include_provider_id": False,
                "include_message_id": False,
                "include_user_id": False,
                "include_updated_at": False,
                "include_batch_id": False,
                "include_correlation_id": False,
            }


class IdempotencyKeyValidator:
    """Validates idempotency keys and their components."""
    
    @staticmethod
    def validate_key_format(key: str) -> bool:
        """Validate that a key follows the expected format."""
        if not key:
            return False
        
        # Check length (32 characters for SHA-256 hash)
        if len(key) != 32:
            return False
        
        # Check that it's a valid hex string
        try:
            int(key, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_key_uniqueness(
        existing_keys: set,
        new_key: str,
        ttl_seconds: int = 86400  # 24 hours
    ) -> bool:
        """Validate that a key is unique within the TTL window."""
        # In a real implementation, this would check against a Redis store
        # with TTL-based expiration
        return new_key not in existing_keys
    
    @staticmethod
    def should_regenerate_key(
        data_type: str,
        operation: str,
        last_attempt: Optional[datetime] = None,
        max_retries: int = 3
    ) -> bool:
        """Determine if a key should be regenerated based on retry logic."""
        if not last_attempt:
            return False
        
        # For immutable operations, never regenerate
        if IdempotencyStrategy.is_immutable_operation(data_type, operation):
            return False
        
        # For mutable operations, allow regeneration after TTL
        if IdempotencyStrategy.is_mutable_operation(data_type, operation):
            time_since_last = (datetime.utcnow() - last_attempt).total_seconds()
            return time_since_last > 300  # 5 minutes
        
        # For batch operations, allow regeneration with correlation ID
        if IdempotencyStrategy.is_batch_operation(data_type, operation):
            return True
        
        return False
