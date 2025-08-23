"""
Idempotency service for ensuring event processing is idempotent.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from typing import Any, Callable, Dict, List, Optional, Union

from services.common.events.calendar_events import CalendarEvent
from services.common.events.contact_events import ContactEvent
from services.common.events.document_events import DocumentEvent
from services.common.events.email_events import EmailEvent
from services.common.events.todo_events import TodoEvent
from services.common.idempotency.idempotency_keys import (
    IdempotencyKeyGenerator,
    IdempotencyKeyValidator,
    IdempotencyStrategy,
)
from services.common.idempotency.redis_reference import RedisReferencePattern

logger = logging.getLogger(__name__)


class IdempotencyService:
    """Service for managing idempotency in event processing."""

    def __init__(
        self,
        redis_reference: RedisReferencePattern,
        key_generator: Optional[IdempotencyKeyGenerator] = None,
        key_validator: Optional[IdempotencyKeyValidator] = None,
        strategy: Optional[IdempotencyStrategy] = None,
        cleanup_interval_hours: int = 24,
        enable_auto_cleanup: bool = True,
    ) -> None:
        self.redis_reference = redis_reference
        self.key_generator = key_generator or IdempotencyKeyGenerator()
        self.key_validator = key_validator or IdempotencyKeyValidator()
        self.strategy = strategy or IdempotencyStrategy()

        # Cleanup configuration
        self.cleanup_interval_hours = cleanup_interval_hours
        self.enable_auto_cleanup = enable_auto_cleanup
        self._cleanup_thread: Optional[Thread] = None
        self._stop_cleanup = Event()

        # Cleanup monitoring
        self._last_cleanup_time: Optional[datetime] = None
        self._total_cleanups = 0
        self._total_keys_cleaned = 0

        # Start auto-cleanup if enabled
        if self.enable_auto_cleanup:
            self._start_cleanup_scheduler()

    def process_event_with_idempotency(
        self,
        event: Union[EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent],
        processor_func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Process an event with idempotency checking."""
        try:
            # Generate idempotency key
            idempotency_key = self._generate_event_key(event)

            # Check if we've already processed this event
            existing_metadata = self.redis_reference.check_idempotency_key(
                idempotency_key
            )

            if existing_metadata:
                logger.info(f"Event already processed with key: {idempotency_key}")
                return {
                    "success": True,
                    "idempotent": True,
                    "idempotency_key": idempotency_key,
                    "existing_result": existing_metadata.get("result"),
                    "processed_at": existing_metadata.get("processed_at"),
                    "message": "Event already processed",
                }

            # Store idempotency key before processing
            metadata = {
                "event_type": self._get_event_type(event),
                "user_id": event.user_id,
                "operation": event.operation,
                "batch_id": event.batch_id,
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "status": "processing",
            }

            self.redis_reference.store_idempotency_key(idempotency_key, metadata)

            # Process the event
            start_time = datetime.now(timezone.utc)
            result = processor_func(event, *args, **kwargs)
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Update metadata with result
            metadata.update(
                {
                    "status": "completed",
                    "result": result,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "processing_time": str(processing_time),
                }
            )

            self.redis_reference.store_idempotency_key(idempotency_key, metadata)

            return {
                "success": True,
                "idempotent": False,
                "idempotency_key": idempotency_key,
                "result": result,
                "processing_time": processing_time,
                "message": "Event processed successfully",
            }

        except Exception as e:
            logger.error(f"Error processing event with idempotency: {e}")
            # Update metadata with error
            if "idempotency_key" in locals():
                error_metadata = {
                    "status": "error",
                    "error": str(e),
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                }
                self.redis_reference.store_idempotency_key(
                    idempotency_key, error_metadata
                )

            return {"error": str(e)}

    def process_batch_with_idempotency(
        self,
        batch_id: str,
        correlation_id: str,
        events: List[
            Union[EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent]
        ],
        processor_func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Process a batch of events with idempotency checking."""
        try:
            # Generate batch idempotency key
            batch_key = self.key_generator.generate_batch_key(batch_id, correlation_id)

            # Check if batch was already processed
            existing_batch = self.redis_reference.retrieve_batch_reference(
                batch_id, correlation_id
            )

            if existing_batch:
                logger.info(f"Batch already processed: {batch_id}")
                return {
                    "success": True,
                    "idempotent": True,
                    "batch_id": batch_id,
                    "correlation_id": correlation_id,
                    "existing_result": existing_batch.get("result"),
                    "processed_at": existing_batch.get("processed_at"),
                    "message": "Batch already processed",
                }

            # Store batch reference before processing
            batch_metadata = {
                "batch_id": batch_id,
                "correlation_id": correlation_id,
                "event_count": len(events),
                "event_types": [self._get_event_type(event) for event in events],
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "status": "processing",
            }

            self.redis_reference.store_batch_reference(
                batch_id, correlation_id, batch_metadata
            )

            # Process each event with individual idempotency
            results = []
            errors = []

            for event in events:
                try:
                    event_result = self.process_event_with_idempotency(
                        event, processor_func, *args, **kwargs
                    )
                    results.append(event_result)
                except Exception as e:
                    error_info = {
                        "event_type": self._get_event_type(event),
                        "user_id": event.user_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                    errors.append(error_info)
                    logger.error(f"Error processing event in batch: {e}")

            # Update batch metadata with results
            batch_metadata.update(
                {
                    "status": "completed",
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "results": results,
                    "errors": errors,
                    "success_count": len(results),
                    "error_count": len(errors),
                    "success": len(errors) == 0,
                }
            )

            self.redis_reference.store_batch_reference(
                batch_id, correlation_id, batch_metadata
            )

            logger.info(
                f"Successfully processed batch: {batch_id} "
                f"({len(results)} events, {len(errors)} errors)"
            )

            return {
                "success": len(errors) == 0,
                "idempotent": False,
                "batch_id": batch_id,
                "correlation_id": correlation_id,
                "results": results,
                "errors": errors,
                "success_count": len(results),
                "error_count": len(errors),
                "message": (
                    f"Batch processed: {len(results)} successes, {len(errors)} errors"
                ),
            }

        except Exception as e:
            logger.error(f"Error processing batch with idempotency: {e}")

            # Update batch metadata with error
            if "batch_id" in locals() and "correlation_id" in locals():
                error_metadata = {
                    "batch_id": batch_id,
                    "correlation_id": correlation_id,
                    "event_count": len(events),
                    "stored_at": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "success": False,
                }

                self.redis_reference.store_batch_reference(
                    batch_id, correlation_id, error_metadata
                )

            raise

    def _generate_event_key(
        self,
        event: Union[EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent],
    ) -> str:
        """Generate a unique idempotency key for an event."""
        return self.key_generator.generate_key(
            event_type=self._get_event_type(event),
            user_id=event.user_id,
            operation=event.operation,
            batch_id=event.batch_id,
        )

    def _get_event_type(
        self,
        event: Union[EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent],
    ) -> str:
        """Get the event type as a string."""
        return type(event).__name__.lower().replace("event", "")

    def check_idempotency_status(self, key: str) -> Optional[Dict[str, Any]]:
        """Check the status of an idempotency key."""
        return self.redis_reference.check_idempotency_key(key)

    def get_idempotency_stats(self) -> Dict[str, Any]:
        """Get statistics about idempotency usage."""
        try:
            stats = self.redis_reference.get_idempotency_stats()
            return {
                "total_keys": stats.get("total_keys", 0),
                "active_keys": stats.get("active_keys", 0),
                "expired_keys": stats.get("expired_keys", 0),
                "last_cleanup": (
                    self._last_cleanup_time.isoformat()
                    if self._last_cleanup_time
                    else None
                ),
                "total_cleanups": self._total_cleanups,
                "total_keys_cleaned": self._total_keys_cleaned,
            }
        except Exception as e:
            logger.error(f"Error getting idempotency stats: {e}")
            return {"error": str(e)}

    def cleanup_expired_keys(self, max_age_hours: int = 24) -> int:
        """Clean up expired idempotency keys."""
        try:
            logger.info(
                f"Starting cleanup of expired idempotency keys "
                f"(max age: {max_age_hours} hours)"
            )

            # Calculate the cutoff timestamp
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            cutoff_timestamp = int(cutoff_time.timestamp())

            # Use Redis SCAN to iterate through keys efficiently
            cleaned_count = 0
            cursor = 0
            pattern = "idempotency:*"

            while True:
                # Scan for keys matching the pattern
                cursor, keys = self.redis_reference.redis.scan(
                    cursor=cursor, match=pattern, count=100
                )

                for key in keys:
                    try:
                        # Check if key exists and get its TTL
                        ttl = self.redis_reference.redis.ttl(key)

                        if ttl == -1:  # Key has no TTL set
                            # Check if it's an old key by looking at the stored
                            # timestamp
                            key_data = self.redis_reference.redis.get(key)
                            if key_data:
                                try:
                                    data = json.loads(key_data)
                                    stored_timestamp = data.get("timestamp")
                                    if stored_timestamp:
                                        # Convert to timestamp if it's a string
                                        if isinstance(stored_timestamp, str):
                                            stored_timestamp = datetime.fromisoformat(
                                                stored_timestamp.replace("Z", "+00:00")
                                            ).timestamp()

                                        if stored_timestamp < cutoff_timestamp:
                                            # Key is old, delete it
                                            self.redis_reference.redis.delete(key)
                                            cleaned_count += 1
                                            logger.debug(f"Deleted expired key: {key}")
                                except (json.JSONDecodeError, ValueError) as e:
                                    logger.warning(
                                        f"Could not parse timestamp for key {key}: {e}"
                                    )
                                    # If we can't parse the timestamp, delete the key as
                                    # it's likely corrupted
                                    self.redis_reference.redis.delete(key)
                                    cleaned_count += 1
                                    logger.debug(
                                        f"Deleted corrupted idempotency key: {key}"
                                    )

                        elif ttl == -2:  # Key doesn't exist (was deleted)
                            continue

                        elif ttl == 0:  # Key has expired TTL
                            # Delete the expired key
                            self.redis_reference.redis.delete(key)
                            cleaned_count += 1
                            logger.debug(f"Deleted expired idempotency key: {key}")

                    except Exception as e:
                        logger.warning(
                            f"Error processing key {key} during cleanup: {e}"
                        )
                        continue

                # If cursor is 0, we've completed the scan
                if cursor == 0:
                    break

            logger.info(
                f"Cleanup completed. Deleted {cleaned_count} expired idempotency keys"
            )

            # Update monitoring statistics
            self._last_cleanup_time = datetime.now(timezone.utc)
            self._total_cleanups += 1
            self._total_keys_cleaned += cleaned_count

            return cleaned_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

    def cleanup_expired_keys_batch(
        self, max_age_hours: int = 24, batch_size: int = 100
    ) -> int:
        """Clean up expired idempotency keys in batches for better performance."""
        try:
            logger.info(
                f"Starting batch cleanup of expired idempotency keys "
                f"(max age: {max_age_hours} hours, batch size: {batch_size})"
            )

            # Calculate the cutoff timestamp
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            cutoff_timestamp = int(cutoff_time.timestamp())

            # Use Redis SCAN with batch processing
            cleaned_count = 0
            cursor = 0
            pattern = "idempotency:*"

            while True:
                # Scan for keys matching the pattern
                cursor, keys = self.redis_reference.redis.scan(
                    cursor=cursor, match=pattern, count=batch_size
                )

                # Process batch of keys
                for key in keys:
                    try:
                        # Check if key exists and get its TTL
                        ttl = self.redis_reference.redis.ttl(key)

                        if ttl == -1:  # Key has no TTL set
                            # Check if it's an old key by looking at the stored
                            # timestamp
                            key_data = self.redis_reference.redis.get(key)
                            if key_data:
                                try:
                                    data = json.loads(key_data)
                                    stored_timestamp = data.get("timestamp")
                                    if stored_timestamp:
                                        # Convert to timestamp if it's a string
                                        if isinstance(stored_timestamp, str):
                                            stored_timestamp = datetime.fromisoformat(
                                                stored_timestamp.replace("Z", "+00:00")
                                            ).timestamp()

                                        if stored_timestamp < cutoff_timestamp:
                                            # Key is old, delete it
                                            self.redis_reference.redis.delete(key)
                                            cleaned_count += 1
                                            logger.debug(f"Deleted expired key: {key}")
                                except (json.JSONDecodeError, ValueError) as e:
                                    logger.warning(
                                        f"Could not parse timestamp for key {key}: {e}"
                                    )
                                    # If we can't parse the timestamp, delete the key as
                                    # it's likely corrupted
                                    self.redis_reference.redis.delete(key)
                                    cleaned_count += 1
                                    logger.debug(
                                        f"Deleted corrupted idempotency key: {key}"
                                    )

                        elif ttl == -2:  # Key doesn't exist (was deleted)
                            continue

                        elif ttl == 0:  # Key has expired TTL
                            # Delete the expired key
                            self.redis_reference.redis.delete(key)
                            cleaned_count += 1
                            logger.debug(f"Deleted expired idempotency key: {key}")

                    except Exception as e:
                        logger.warning(
                            f"Error processing key {key} during batch cleanup: {e}"
                        )
                        continue

                # If cursor is 0, we've completed the scan
                if cursor == 0:
                    break

            logger.info(
                f"Batch cleanup completed. Deleted {cleaned_count} expired idempotency keys"
            )

            # Update monitoring statistics
            self._last_cleanup_time = datetime.now(timezone.utc)
            self._total_cleanups += 1
            self._total_keys_cleaned += cleaned_count

            return cleaned_count

        except Exception as e:
            logger.error(f"Error during batch cleanup: {e}")
            return 0

    def validate_idempotency_config(
        self, event_type: str, operation: str
    ) -> Dict[str, Any]:
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
            "valid": strategy != "unknown",
        }

    def simulate_event_processing(
        self,
        event_type: str,
        operation: str,
        user_id: str,
        provider: str,
        event_id: str,
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Simulate event processing to test idempotency configuration."""
        # Generate a test key
        test_key = self.key_generator.generate_generic_key(
            event_type=event_type,
            event_id=event_id,
            user_id=user_id,
            provider=provider,
            operation=operation,
            batch_id=batch_id,
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _start_cleanup_scheduler(self) -> None:
        """Start the background cleanup scheduler."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return

        self._stop_cleanup.clear()
        self._cleanup_thread = Thread(target=self._cleanup_scheduler_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("Started idempotency cleanup scheduler")

    def _cleanup_scheduler_loop(self) -> None:
        """Main loop for the cleanup scheduler."""
        while not self._stop_cleanup.is_set():
            try:
                # Wait for the cleanup interval
                self._stop_cleanup.wait(self.cleanup_interval_hours * 3600)

                if not self._stop_cleanup.is_set():
                    # Perform cleanup
                    cleaned_count = self.cleanup_expired_keys()
                    logger.info(
                        f"Scheduled cleanup completed. Deleted {cleaned_count} keys"
                    )

            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}")
                # Wait a bit before retrying
                self._stop_cleanup.wait(300)  # 5 minutes

    def stop_cleanup_scheduler(self) -> None:
        """Stop the background cleanup scheduler."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=10)
            logger.info("Stopped idempotency cleanup scheduler")

    def get_cleanup_status(self) -> Dict[str, Any]:
        """Get the status of the cleanup scheduler."""
        return {
            "auto_cleanup_enabled": self.enable_auto_cleanup,
            "cleanup_interval_hours": self.cleanup_interval_hours,
            "scheduler_running": self._cleanup_thread is not None
            and self._cleanup_thread.is_alive(),
            "last_cleanup": getattr(self, "_last_cleanup_time", None),
            "cleanup_stats": {
                "total_cleanups": getattr(self, "_total_cleanups", 0),
                "total_keys_cleaned": getattr(self, "_total_keys_cleaned", 0),
            },
        }

    def __del__(self) -> None:
        """Cleanup when the service is destroyed."""
        self.stop_cleanup_scheduler()
