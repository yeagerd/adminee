"""
Idempotency service for ensuring event processing is idempotent.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Union, Callable

from services.common.idempotency.idempotency_keys import (
    IdempotencyKeyGenerator, IdempotencyStrategy, IdempotencyKeyValidator
)
from services.common.idempotency.redis_reference import RedisReferencePattern
from services.common.events import (
    EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent
)


logger = logging.getLogger(__name__)


class IdempotencyService:
    """Service for ensuring idempotent event processing."""
    
    def __init__(self, redis_reference: RedisReferencePattern):
        self.redis_reference = redis_reference
        self.key_generator = IdempotencyKeyGenerator()
        self.key_validator = IdempotencyKeyValidator()
        self.strategy = IdempotencyStrategy()
    
    def process_event_with_idempotency(
        self,
        event: Union[EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent],
        processor_func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Process an event with idempotency checking."""
        try:
            # Generate idempotency key
            idempotency_key = self._generate_event_key(event)
            
            # Check if we've already processed this event
            existing_metadata = self.redis_reference.check_idempotency_key(idempotency_key)
            
            if existing_metadata:
                logger.info(f"Event already processed with key: {idempotency_key}")
                return {
                    "success": True,
                    "idempotent": True,
                    "idempotency_key": idempotency_key,
                    "existing_result": existing_metadata.get("result"),
                    "processed_at": existing_metadata.get("processed_at"),
                    "message": "Event already processed"
                }
            
            # Store idempotency key before processing
            metadata = {
                "event_type": self._get_event_type(event),
                "user_id": event.user_id,
                "operation": event.operation,
                "batch_id": event.batch_id,
                "stored_at": datetime.utcnow().isoformat(),
                "status": "processing"
            }
            
            self.redis_reference.store_idempotency_key(idempotency_key, metadata)
            
            # Process the event
            start_time = datetime.utcnow()
            result = processor_func(event, *args, **kwargs)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update metadata with result
            metadata.update({
                "status": "completed",
                "processed_at": datetime.utcnow().isoformat(),
                "processing_time_seconds": processing_time,
                "result": result,
                "success": True
            })
            
            # Update idempotency key with result
            self.redis_reference.store_idempotency_key(idempotency_key, metadata)
            
            logger.info(f"Successfully processed event with idempotency key: {idempotency_key}")
            
            return {
                "success": True,
                "idempotent": False,
                "idempotency_key": idempotency_key,
                "result": result,
                "processing_time_seconds": processing_time,
                "message": "Event processed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error processing event with idempotency: {e}")
            
            # Update metadata with error
            if 'idempotency_key' in locals():
                error_metadata = {
                    "event_type": self._get_event_type(event),
                    "user_id": event.user_id,
                    "operation": event.operation,
                    "batch_id": event.batch_id,
                    "stored_at": datetime.utcnow().isoformat(),
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "success": False
                }
                
                self.redis_reference.store_idempotency_key(idempotency_key, error_metadata)
            
            raise
    
    def process_batch_with_idempotency(
        self,
        batch_id: str,
        correlation_id: str,
        events: list,
        processor_func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a batch of events with idempotency checking."""
        try:
            # Generate batch idempotency key
            batch_key = self.key_generator.generate_batch_key(batch_id, correlation_id)
            
            # Check if batch was already processed
            existing_batch = self.redis_reference.retrieve_batch_reference(batch_id, correlation_id)
            
            if existing_batch:
                logger.info(f"Batch already processed: {batch_id}")
                return {
                    "success": True,
                    "idempotent": True,
                    "batch_id": batch_id,
                    "correlation_id": correlation_id,
                    "existing_result": existing_batch.get("result"),
                    "processed_at": existing_batch.get("processed_at"),
                    "message": "Batch already processed"
                }
            
            # Store batch reference before processing
            batch_metadata = {
                "batch_id": batch_id,
                "correlation_id": correlation_id,
                "event_count": len(events),
                "event_types": [self._get_event_type(event) for event in events],
                "stored_at": datetime.utcnow().isoformat(),
                "status": "processing"
            }
            
            self.redis_reference.store_batch_reference(batch_id, correlation_id, batch_metadata)
            
            # Process each event with individual idempotency
            results = []
            errors = []
            
            for event in events:
                try:
                    event_result = self.process_event_with_idempotency(event, processor_func, *args, **kwargs)
                    results.append(event_result)
                except Exception as e:
                    error_info = {
                        "event_type": self._get_event_type(event),
                        "user_id": event.user_id,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    errors.append(error_info)
                    logger.error(f"Error processing event in batch: {e}")
            
            # Update batch metadata with results
            batch_metadata.update({
                "status": "completed",
                "processed_at": datetime.utcnow().isoformat(),
                "results": results,
                "errors": errors,
                "success_count": len(results),
                "error_count": len(errors),
                "success": len(errors) == 0
            })
            
            self.redis_reference.store_batch_reference(batch_id, correlation_id, batch_metadata)
            
            logger.info(f"Successfully processed batch: {batch_id} ({len(results)} events, {len(errors)} errors)")
            
            return {
                "success": len(errors) == 0,
                "idempotent": False,
                "batch_id": batch_id,
                "correlation_id": correlation_id,
                "results": results,
                "errors": errors,
                "success_count": len(results),
                "error_count": len(errors),
                "message": f"Batch processed with {len(results)} successes and {len(errors)} errors"
            }
            
        except Exception as e:
            logger.error(f"Error processing batch with idempotency: {e}")
            
            # Update batch metadata with error
            if 'batch_id' in locals() and 'correlation_id' in locals():
                error_metadata = {
                    "batch_id": batch_id,
                    "correlation_id": correlation_id,
                    "event_count": len(events),
                    "stored_at": datetime.utcnow().isoformat(),
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "success": False
                }
                
                self.redis_reference.store_batch_reference(batch_id, correlation_id, error_metadata)
            
            raise
    
    def _generate_event_key(self, event: Union[EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent]) -> str:
        """Generate idempotency key for an event."""
        if isinstance(event, EmailEvent):
            return self.key_generator.generate_email_key(event)
        elif isinstance(event, CalendarEvent):
            return self.key_generator.generate_calendar_key(event)
        elif isinstance(event, ContactEvent):
            return self.key_generator.generate_contact_key(event)
        elif isinstance(event, DocumentEvent):
            return self.key_generator.generate_document_key(event)
        elif isinstance(event, TodoEvent):
            return self.key_generator.generate_todo_key(event)
        else:
            # Fallback to generic key generation
            return self.key_generator.generate_generic_key(
                event_type=type(event).__name__,
                event_id=getattr(event, 'id', 'unknown'),
                user_id=event.user_id,
                provider=getattr(event, 'provider', 'unknown'),
                operation=event.operation,
                updated_at=event.last_updated,
                batch_id=event.batch_id
            )
    
    def _get_event_type(self, event: Union[EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent]) -> str:
        """Get the event type string."""
        if isinstance(event, EmailEvent):
            return "email"
        elif isinstance(event, CalendarEvent):
            return "calendar"
        elif isinstance(event, ContactEvent):
            return "contact"
        elif isinstance(event, DocumentEvent):
            return "document"
        elif isinstance(event, TodoEvent):
            return "todo"
        else:
            return type(event).__name__.lower()
    
    def check_idempotency_status(self, key: str) -> Optional[Dict[str, Any]]:
        """Check the status of an idempotency key."""
        return self.redis_reference.check_idempotency_key(key)
    
    def get_idempotency_stats(self) -> Dict[str, Any]:
        """Get statistics about idempotency usage."""
        try:
            # This would typically query Redis for statistics
            # For now, return basic info
            return {
                "service": "idempotency",
                "timestamp": datetime.utcnow().isoformat(),
                "key_generator": "IdempotencyKeyGenerator",
                "strategy": "IdempotencyStrategy",
                "validator": "IdempotencyKeyValidator",
                "redis_integration": True
            }
        except Exception as e:
            logger.error(f"Error getting idempotency stats: {e}")
            return {"error": str(e)}
    
    def cleanup_expired_keys(self, max_age_hours: int = 24) -> int:
        """Clean up expired idempotency keys."""
        try:
            # This would typically scan Redis for expired keys
            # For now, return 0 as cleanup is not implemented
            logger.info("Cleanup of expired idempotency keys not implemented")
            return 0
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def validate_idempotency_config(self, event_type: str, operation: str) -> Dict[str, Any]:
        """Validate idempotency configuration for an event type and operation."""
        strategy = self.strategy.get_key_strategy(event_type, operation)
        components = self.strategy.get_key_components(event_type, operation)
        
        return {
            "event_type": event_type,
            "operation": operation,
            "strategy": strategy,
            "components": components,
            "is_immutable": self.strategy.is_immutable_operation(event_type, operation),
            "is_mutable": self.strategy.is_mutable_operation(event_type, operation),
            "is_batch": self.strategy.is_batch_operation(event_type, operation),
            "valid": strategy != "unknown"
        }
    
    def simulate_event_processing(
        self,
        event_type: str,
        operation: str,
        user_id: str,
        provider: str,
        event_id: str,
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Simulate event processing to test idempotency configuration."""
        # Generate a test key
        test_key = self.key_generator.generate_generic_key(
            event_type=event_type,
            event_id=event_id,
            user_id=user_id,
            provider=provider,
            operation=operation,
            batch_id=batch_id
        )
        
        # Validate the key
        key_valid = self.key_validator.validate_key_format(test_key)
        
        # Get strategy info
        strategy_info = self.validate_idempotency_config(event_type, operation)
        
        return {
            "simulation": True,
            "event_type": event_type,
            "operation": operation,
            "user_id": user_id,
            "provider": provider,
            "event_id": event_id,
            "batch_id": batch_id,
            "generated_key": test_key,
            "key_valid": key_valid,
            "strategy_info": strategy_info,
            "timestamp": datetime.utcnow().isoformat()
        }
