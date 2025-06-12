"""
Unit tests for retry utilities and error recovery procedures.

Tests the retry logic, exponential backoff, jitter, exception handling,
and convenience decorators for different types of operations.
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.user_management.exceptions import (
    DatabaseException,
    IntegrationException,
    ServiceException,
    TokenNotFoundException,
    UserNotFoundException,
)
from services.user_management.utils.retry import (
    RetryError,
    is_transient_error,
    retry_async,
    retry_database_operations,
    retry_external_api_calls,
    retry_oauth_operations,
    retry_on_transient_failure,
    retry_sync,
)


class TestRetryError:
    """Test cases for RetryError exception."""

    def test_retry_error_creation(self):
        """Test RetryError exception creation."""
        original_error = ValueError("Original error")
        retry_error = RetryError("Retry failed", 3, original_error)

        assert retry_error.message == "Retry failed"
        assert retry_error.attempts == 3
        assert retry_error.last_exception == original_error
        assert "after 3 attempts" in str(retry_error)
        assert "Original error" in str(retry_error)


class TestTransientErrorDetection:
    """Test cases for transient error detection."""

    def test_database_exception_is_transient(self):
        """Test that database exceptions are considered transient."""
        exc = DatabaseException("Connection lost")
        assert is_transient_error(exc) is True

    def test_service_exception_is_transient(self):
        """Test that service exceptions are considered transient."""
        exc = ServiceException("api", "call", "timeout")
        assert is_transient_error(exc) is True

    def test_connection_errors_are_transient(self):
        """Test that connection-related errors are considered transient."""
        exceptions = [
            ValueError("Connection timeout"),
            RuntimeError("Network error"),
            Exception("Service unavailable"),
            OSError("Bad gateway"),
            ConnectionError("Connection refused"),
        ]

        for exc in exceptions:
            assert is_transient_error(exc) is True

    def test_non_transient_errors(self):
        """Test that non-transient errors are correctly identified."""
        exceptions = [
            UserNotFoundException("user123"),
            TokenNotFoundException("user123", "google", "access"),
            ValueError("Invalid input"),
            TypeError("Wrong type"),
        ]

        for exc in exceptions:
            assert is_transient_error(exc) is False


class TestAsyncRetry:
    """Test cases for async retry functionality."""

    @pytest.mark.asyncio
    async def test_successful_function_no_retry(self):
        """Test that successful functions are not retried."""
        mock_func = AsyncMock(return_value="success")

        result = await retry_async(mock_func, max_attempts=3)

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retry on transient failures."""
        mock_func = AsyncMock()
        mock_func.side_effect = [
            DatabaseException("Connection lost"),
            DatabaseException("Timeout"),
            "success",
        ]

        result = await retry_async(mock_func, max_attempts=3, base_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_transient_failure(self):
        """Test that non-transient failures are not retried."""
        mock_func = AsyncMock(side_effect=UserNotFoundException("user123"))

        with pytest.raises(UserNotFoundException):
            await retry_async(mock_func, max_attempts=3)

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_retry_error(self):
        """Test that RetryError is raised when all attempts are exhausted."""
        mock_func = AsyncMock(side_effect=DatabaseException("Always fails"))

        with pytest.raises(RetryError) as exc_info:
            await retry_async(mock_func, max_attempts=2, base_delay=0.01)

        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.last_exception, DatabaseException)
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_specific_retry_exceptions(self):
        """Test retry with specific exception types."""
        mock_func = AsyncMock()
        mock_func.side_effect = [ServiceException("api", "call", "error"), "success"]

        result = await retry_async(
            mock_func,
            max_attempts=3,
            base_delay=0.01,
            retry_exceptions=[ServiceException],
        )

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_ignore_exceptions(self):
        """Test that ignored exceptions are never retried."""
        mock_func = AsyncMock(
            side_effect=TokenNotFoundException("user", "google", "access")
        )

        with pytest.raises(TokenNotFoundException):
            await retry_async(
                mock_func, max_attempts=3, ignore_exceptions=[TokenNotFoundException]
            )

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff timing works correctly."""
        mock_func = AsyncMock()
        mock_func.side_effect = [
            DatabaseException("Error 1"),
            DatabaseException("Error 2"),
            "success",
        ]

        start_time = time.time()
        result = await retry_async(
            mock_func,
            max_attempts=3,
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False,
        )
        elapsed = time.time() - start_time

        assert result == "success"
        # Should have delays of ~0.1s and ~0.2s = ~0.3s total
        assert elapsed >= 0.25  # Allow some tolerance
        assert elapsed < 0.5


class TestSyncRetry:
    """Test cases for synchronous retry functionality."""

    def test_successful_function_no_retry(self):
        """Test that successful functions are not retried."""
        mock_func = Mock(return_value="success")

        result = retry_sync(mock_func, max_attempts=3)

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_transient_failure(self):
        """Test retry on transient failures."""
        mock_func = Mock()
        mock_func.side_effect = [DatabaseException("Connection lost"), "success"]

        result = retry_sync(mock_func, max_attempts=3, base_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_exhausted_raises_retry_error(self):
        """Test that RetryError is raised when all attempts are exhausted."""
        mock_func = Mock(side_effect=DatabaseException("Always fails"))

        with pytest.raises(RetryError):
            retry_sync(mock_func, max_attempts=2, base_delay=0.01)

        assert mock_func.call_count == 2


class TestRetryDecorator:
    """Test cases for the retry decorator."""

    @pytest.mark.asyncio
    async def test_async_decorator(self):
        """Test the retry decorator on async functions."""
        call_count = 0

        @retry_on_transient_failure(max_attempts=3, base_delay=0.01)
        async def failing_async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DatabaseException("Transient error")
            return "success"

        result = await failing_async_func()

        assert result == "success"
        assert call_count == 3

    def test_sync_decorator(self):
        """Test the retry decorator on sync functions."""
        call_count = 0

        @retry_on_transient_failure(max_attempts=3, base_delay=0.01)
        def failing_sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise DatabaseException("Transient error")
            return "success"

        result = failing_sync_func()

        assert result == "success"
        assert call_count == 2


class TestConvenienceDecorators:
    """Test cases for convenience decorators."""

    @pytest.mark.asyncio
    async def test_retry_database_operations(self):
        """Test the database operations retry decorator."""
        call_count = 0

        @retry_database_operations(
            max_attempts=2, base_delay=0.01
        )  # Fast delay for testing
        async def database_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise DatabaseException("Database error")
            return "database_success"

        result = await database_operation()

        assert result == "database_success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_external_api_calls(self):
        """Test the external API calls retry decorator."""
        call_count = 0

        @retry_external_api_calls(
            max_attempts=2, base_delay=0.01
        )  # Fast delay for testing
        async def api_call():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ServiceException("api", "call", "timeout")
            return "api_success"

        result = await api_call()

        assert result == "api_success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_oauth_operations(self):
        """Test the OAuth operations retry decorator."""
        call_count = 0

        @retry_oauth_operations(
            max_attempts=2, base_delay=0.01
        )  # Fast delay for testing
        async def oauth_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise IntegrationException("OAuth error")
            return "oauth_success"

        result = await oauth_operation()

        assert result == "oauth_success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_oauth_operations_ignore_token_not_found(self):
        """Test that OAuth operations don't retry on token not found errors."""

        @retry_oauth_operations(max_attempts=3)
        async def oauth_operation():
            raise TokenNotFoundException("user", "google", "access")

        with pytest.raises(TokenNotFoundException):
            await oauth_operation()


class TestRetryWithJitter:
    """Test cases for retry with jitter."""

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to retry delays."""
        # Run multiple times to test randomness
        delays = []
        for i in range(3):
            mock_func = AsyncMock()
            mock_func.side_effect = [
                DatabaseException(f"Error {i}_1"),
                DatabaseException(f"Error {i}_2"),
                f"success_{i}",
            ]

            with patch("asyncio.sleep") as mock_sleep:
                await retry_async(
                    mock_func, max_attempts=3, base_delay=1.0, jitter=True
                )
                # Get the delays from the mock calls
                if mock_sleep.call_args_list:
                    delays.extend([call[0][0] for call in mock_sleep.call_args_list])

        # With jitter, delays should vary
        if len(delays) > 1:
            assert not all(
                d == delays[0] for d in delays
            ), "Jitter should add randomness"

    @pytest.mark.asyncio
    async def test_no_jitter_consistent_delays(self):
        """Test that without jitter, delays are consistent."""
        mock_func = AsyncMock()
        mock_func.side_effect = [DatabaseException("Error 1"), "success"]

        with patch("asyncio.sleep") as mock_sleep:
            await retry_async(mock_func, max_attempts=2, base_delay=1.0, jitter=False)

            # Should have exactly one delay call with base_delay
            assert len(mock_sleep.call_args_list) == 1
            assert mock_sleep.call_args_list[0][0][0] == 1.0


class TestRetryConfiguration:
    """Test cases for retry configuration options."""

    @pytest.mark.asyncio
    async def test_max_delay_limit(self):
        """Test that delays are capped at max_delay."""
        mock_func = AsyncMock()
        mock_func.side_effect = [
            DatabaseException("Error 1"),
            DatabaseException("Error 2"),
            "success",
        ]

        with patch("asyncio.sleep") as mock_sleep:
            await retry_async(
                mock_func,
                max_attempts=3,
                base_delay=10.0,
                max_delay=5.0,
                exponential_base=2.0,
                jitter=False,
            )

            # All delays should be capped at max_delay
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert all(delay <= 5.0 for delay in delays)

    @pytest.mark.asyncio
    async def test_custom_exponential_base(self):
        """Test retry with custom exponential base."""
        mock_func = AsyncMock()
        mock_func.side_effect = [
            DatabaseException("Error 1"),
            DatabaseException("Error 2"),
            "success",
        ]

        with patch("asyncio.sleep") as mock_sleep:
            await retry_async(
                mock_func,
                max_attempts=3,
                base_delay=1.0,
                exponential_base=3.0,
                jitter=False,
            )

            delays = [call[0][0] for call in mock_sleep.call_args_list]
            # Should be [1.0, 3.0] with base=3.0
            assert delays[0] == 1.0
            assert delays[1] == 3.0
