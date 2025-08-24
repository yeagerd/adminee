"""
Test helpers for idempotency testing.

This module contains utility functions for testing idempotency functionality
without cluttering the main IdempotencyService class.

Example Usage:
    from services.common.tests.helpers.idempotency_test_helpers import (
        simulate_event_processing,
    )

    # Test idempotency configuration for email creation
    result = simulate_event_processing(
        event_type="email",
        operation="create",
        user_id="user123",
        provider="gmail",
        event_id="email123"
    )

    assert result["simulation"] is True
    assert result["strategy_info"]["strategy"] == "immutable"
    assert result["key_valid"] is True
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.common.idempotency.idempotency_keys import (
    IdempotencyKeyGenerator,
    IdempotencyKeyValidator,
    IdempotencyStrategy,
)


def simulate_event_processing(
    event_type: str,
    operation: str,
    user_id: str,
    provider: str,
    event_id: str,
    batch_id: Optional[str] = None,
    key_generator: Optional[IdempotencyKeyGenerator] = None,
    key_validator: Optional[IdempotencyKeyValidator] = None,
    strategy: Optional[IdempotencyStrategy] = None,
) -> Dict[str, Any]:
    """
    Simulate event processing to test idempotency configuration.

    This function is moved from IdempotencyService to avoid cluttering
    the production service with test-only functionality.

    Args:
        event_type: Type of event being processed
        operation: Operation being performed (create, update, delete)
        user_id: ID of the user associated with the event
        provider: Provider/service name
        event_id: Unique identifier for the event
        batch_id: Optional batch identifier for batch operations
        key_generator: Optional key generator instance
        key_validator: Optional key validator instance
        strategy: Optional strategy instance

    Returns:
        Dictionary containing simulation results and configuration info
    """
    # Use provided instances or create defaults
    key_gen = key_generator or IdempotencyKeyGenerator()
    key_val = key_validator or IdempotencyKeyValidator()
    strat = strategy or IdempotencyStrategy()

    # Generate a test key
    test_key = key_gen.generate_generic_key(
        event_type=event_type,
        event_id=event_id,
        user_id=user_id,
        provider=provider,
        operation=operation,
        batch_id=batch_id,
    )

    # Validate the key
    key_valid = key_val.validate_key_format(test_key)

    # Get strategy info
    strategy_info = validate_idempotency_config(event_type, operation, strat)

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


def validate_idempotency_config(
    event_type: str, operation: str, strategy: IdempotencyStrategy
) -> Dict[str, Any]:
    """
    Validate idempotency configuration for a given event type and operation.

    Args:
        event_type: Type of event being processed
        operation: Operation being performed
        strategy: Strategy instance to use for validation

    Returns:
        Dictionary containing strategy validation results
    """
    # Get strategy info
    strategy_name = strategy.get_key_strategy(event_type, operation)

    # Get component information
    components = strategy.get_key_components(event_type, operation)

    return {
        "strategy": strategy_name,
        "components": components,
        "is_immutable": strategy.is_immutable_operation(event_type, operation),
        "is_mutable": strategy.is_mutable_operation(event_type, operation),
        "is_batch": strategy.is_batch_operation(event_type, operation),
        "valid": strategy_name != "unknown",
    }
