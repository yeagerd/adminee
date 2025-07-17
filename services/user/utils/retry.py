"""
Retry utilities for handling transient failures.

Provides decorators and utility functions for implementing automatic retry
logic with exponential backoff for database operations, external API calls,
and other operations that may fail due to transient issues.
"""

import asyncio
import random
from functools import wraps
from typing import Any, Callable, List, Optional, Type

from services.common.http_errors import NotFoundError, ServiceError
from services.common.logging_config import get_logger

logger = get_logger(__name__)


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted."""

    def __init__(self, message: str, attempts: int, last_exception: Exception):
        self.message = message
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"{message} (after {attempts} attempts): {last_exception}")


def is_transient_error(exception: Exception) -> bool:
    """
    Determine if an exception represents a transient failure that should be retried.

    Args:
        exception: The exception to check

    Returns:
        True if the error is transient and should be retried
    """
    # Service errors (including database, network, etc.)
    if isinstance(exception, ServiceError):
        return True
    # NotFoundError is not considered transient
    if isinstance(exception, NotFoundError):
        return False

    # HTTP-related errors that might be transient
    error_message = str(exception).lower()
    transient_indicators = [
        "connection",
        "timeout",
        "network",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "too many requests",
        "rate limit",
        "temporary",
        "retry",
    ]

    return any(indicator in error_message for indicator in transient_indicators)


async def retry_async(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    ignore_exceptions: Optional[List[Type[Exception]]] = None,
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: The async function to retry
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retry_exceptions: Specific exceptions to retry on (if None, uses is_transient_error)
        ignore_exceptions: Exceptions to never retry on

    Returns:
        The result of the function call

    Raises:
        RetryError: If all retry attempts are exhausted
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            result = await func()
            if attempt > 0:
                logger.info(f"Function succeeded on attempt {attempt + 1}")
            return result

        except Exception as e:
            last_exception = e

            # Check if we should ignore this exception
            if ignore_exceptions and any(
                isinstance(e, exc_type) for exc_type in ignore_exceptions
            ):
                logger.info(f"Not retrying due to ignore exception: {type(e).__name__}")
                raise

            # Check if we should retry this exception
            should_retry = False
            if retry_exceptions:
                should_retry = any(
                    isinstance(e, exc_type) for exc_type in retry_exceptions
                )
            else:
                should_retry = is_transient_error(e)

            if not should_retry:
                logger.info(f"Not retrying non-transient error: {type(e).__name__}")
                raise

            # If this is the last attempt, don't wait
            if attempt == max_attempts - 1:
                break

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base**attempt), max_delay)

            # Add jitter to avoid thundering herd
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                f"Attempt {attempt + 1} failed with {type(e).__name__}: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )

            await asyncio.sleep(delay)

    # All attempts exhausted
    if last_exception is None:
        last_exception = Exception("Unknown error occurred")
    raise RetryError(
        f"Function failed after {max_attempts} attempts",
        max_attempts,
        last_exception,
    )


def retry_sync(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    ignore_exceptions: Optional[List[Type[Exception]]] = None,
) -> Any:
    """
    Retry a synchronous function with exponential backoff.

    Args:
        func: The function to retry
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retry_exceptions: Specific exceptions to retry on (if None, uses is_transient_error)
        ignore_exceptions: Exceptions to never retry on

    Returns:
        The result of the function call

    Raises:
        RetryError: If all retry attempts are exhausted
    """
    import time

    last_exception = None

    for attempt in range(max_attempts):
        try:
            result = func()
            if attempt > 0:
                logger.info(f"Function succeeded on attempt {attempt + 1}")
            return result

        except Exception as e:
            last_exception = e

            # Check if we should ignore this exception
            if ignore_exceptions and any(
                isinstance(e, exc_type) for exc_type in ignore_exceptions
            ):
                logger.info(f"Not retrying due to ignore exception: {type(e).__name__}")
                raise

            # Check if we should retry this exception
            should_retry = False
            if retry_exceptions:
                should_retry = any(
                    isinstance(e, exc_type) for exc_type in retry_exceptions
                )
            else:
                should_retry = is_transient_error(e)

            if not should_retry:
                logger.info(f"Not retrying non-transient error: {type(e).__name__}")
                raise

            # If this is the last attempt, don't wait
            if attempt == max_attempts - 1:
                break

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base**attempt), max_delay)

            # Add jitter to avoid thundering herd
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                f"Attempt {attempt + 1} failed with {type(e).__name__}: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )

            time.sleep(delay)

    # All attempts exhausted
    if last_exception is None:
        last_exception = Exception("Unknown error occurred")
    raise RetryError(
        f"Function failed after {max_attempts} attempts",
        max_attempts,
        last_exception,
    )


def retry_on_transient_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    ignore_exceptions: Optional[List[Type[Exception]]] = None,
) -> Callable[..., Any]:
    """
    Decorator for automatic retry on transient failures.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retry_exceptions: Specific exceptions to retry on (if None, uses is_transient_error)
        ignore_exceptions: Exceptions to never retry on

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_async(
                    lambda: func(*args, **kwargs),
                    max_attempts=max_attempts,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    exponential_base=exponential_base,
                    jitter=jitter,
                    retry_exceptions=retry_exceptions,
                    ignore_exceptions=ignore_exceptions,
                )

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_sync(
                    lambda: func(*args, **kwargs),
                    max_attempts=max_attempts,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    exponential_base=exponential_base,
                    jitter=jitter,
                    retry_exceptions=retry_exceptions,
                    ignore_exceptions=ignore_exceptions,
                )

            return sync_wrapper

    return decorator


# Convenience decorators for common scenarios
def retry_database_operations(max_attempts: int = 3, base_delay: float = 0.5) -> Callable[..., Any]:
    """Decorator for retrying database operations."""
    return retry_on_transient_failure(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=10.0,
        retry_exceptions=[ServiceError],
    )


def retry_external_api_calls(max_attempts: int = 3, base_delay: float = 1.0) -> Callable[..., Any]:
    """Decorator for retrying external API calls."""
    return retry_on_transient_failure(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=30.0,
        retry_exceptions=[ServiceError],
    )


def retry_oauth_operations(max_attempts: int = 2, base_delay: float = 1.0) -> Callable[..., Any]:
    """Decorator for retrying OAuth operations with shorter delays."""
    return retry_on_transient_failure(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=5.0,
        retry_exceptions=[ServiceError],
        ignore_exceptions=[NotFoundError],  # Don't retry on missing tokens
    )
