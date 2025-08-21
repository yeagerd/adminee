"""
Unit tests for enhanced logging configuration.

Tests the enhanced text renderer, service context extraction,
file/line context, and request ID handling.
"""

import logging
import uuid
from unittest.mock import MagicMock

import structlog

from services.common.logging_config import (
    EnhancedTextRenderer,
    add_file_line_context,
    add_request_context,
    add_service_context,
    get_logger,
    request_id_var,
    setup_service_logging,
    user_id_var,
)


class TestEnhancedLoggingConfiguration:
    """Test the enhanced logging configuration features."""

    def setup_method(self):
        """Set up test environment."""
        # Reset context variables
        request_id_var.set("uninitialized")
        user_id_var.set("anonymous")

        # Clear any existing logging configuration
        logging.getLogger().handlers.clear()
        structlog.reset_defaults()

    def test_add_request_context(self):
        """Test that request context is properly added to log entries."""
        # Set up context variables
        test_request_id = "test-request-123"
        test_user_id = "test@example.com"
        request_id_var.set(test_request_id)
        user_id_var.set(test_user_id)

        # Create a mock event dict
        event_dict = {"event": "test message"}

        # Call the function
        result = add_request_context(MagicMock(), "info", event_dict)

        # Check that request context was added
        assert result["request_id"] == test_request_id
        assert result["user_id"] == test_user_id

    def test_add_request_context_no_context(self):
        """Test that request context handles missing context gracefully."""
        # Reset context variables
        request_id_var.set("uninitialized")
        user_id_var.set("anonymous")

        event_dict = {"event": "test message"}
        result = add_request_context(MagicMock(), "info", event_dict)

        # Should not add request_id or user_id when context is uninitialized
        assert "request_id" not in result
        assert "user_id" not in result

    def test_add_service_context(self):
        """Test that service context is extracted from logger names."""
        # Test with a service logger name
        event_dict = {"logger": "services.chat.api.health", "event": "test"}
        result = add_service_context(MagicMock(), "info", event_dict)

        assert result["service"] == "chat"

        # Test with a different service
        event_dict = {"logger": "services.office.core.settings", "event": "test"}
        result = add_service_context(MagicMock(), "info", event_dict)

        assert result["service"] == "office"

        # Test with non-service logger (should not add service)
        event_dict = {"logger": "some.other.logger", "event": "test"}
        result = add_service_context(MagicMock(), "info", event_dict)

        assert "service" not in result

    def test_add_file_line_context(self):
        """Test that file and line context is added."""
        event_dict = {"event": "test message"}
        result = add_file_line_context(MagicMock(), "info", event_dict)

        # Should add file and line information
        assert "file" in result
        assert "line" in result
        # The file name might vary depending on the call stack; verify it's a string
        assert isinstance(result["file"], str)
        assert isinstance(result["line"], int)

    def test_enhanced_text_renderer_basic(self):
        """Test basic text rendering functionality."""
        renderer = EnhancedTextRenderer("test-service")

        event_dict = {
            "timestamp": "2025-07-25T23:05:05.247325Z",
            "level": "INFO",
            "logger": "services.test.main",
            "event": "Service started successfully",
            "service": "test",
            "port": 8000,
            "environment": "development",
        }

        result = renderer(MagicMock(), "info", event_dict)

        # Check that all components are present
        assert "2025-07-25T23:05:05.247325Z" in result
        assert "[test]" in result
        assert "[INFO]" in result
        assert "test.main" in result  # Cleaned logger name without "services." prefix
        assert "Service started successfully" in result
        assert "port=8000" in result
        assert "environment=development" in result

    def test_enhanced_text_renderer_with_request_id(self):
        """Test text rendering with request ID."""
        renderer = EnhancedTextRenderer("test-service")

        event_dict = {
            "timestamp": "2025-07-25T23:05:05.247325Z",
            "level": "INFO",
            "logger": "services.test.main",
            "event": "Processing request",
            "service": "test",
            "request_id": "9f1b0f5d-a388-4ae2-8d66-67256cc71235",
        }

        result = renderer(MagicMock(), "info", event_dict)

        # Should show last 4 characters of request ID
        assert "[1235]" in result

    def test_enhanced_text_renderer_with_user_id(self):
        """Test text rendering with user ID."""
        renderer = EnhancedTextRenderer("test-service")

        event_dict = {
            "timestamp": "2025-07-25T23:05:05.247325Z",
            "level": "INFO",
            "logger": "services.test.main",
            "event": "User action",
            "service": "test",
            "user_id": "demo@example.com",
        }

        result = renderer(MagicMock(), "info", event_dict)

        # Should show user information
        assert "| User: demo@example.com" in result

    def test_enhanced_text_renderer_with_file_line(self):
        """Test text rendering with file and line information (extra context)."""
        renderer = EnhancedTextRenderer("test-service")

        event_dict = {
            "timestamp": "2025-07-25T23:05:05.247325Z",
            "level": "INFO",
            "logger": "services.test.main",
            "event": "Test message",
            "service": "test",
            "file": "api.py",
            "line": 42,
        }

        result = renderer(MagicMock(), "info", event_dict)

        # File and line information should be shown as extra context, not inline
        assert "file=api.py" in result
        assert "line=42" in result

    def test_enhanced_text_renderer_complex(self):
        """Test text rendering with all features combined."""
        renderer = EnhancedTextRenderer("office-service")

        event_dict = {
            "timestamp": "2025-07-25T23:05:05.247325Z",
            "level": "ERROR",
            "logger": "services.office.api.health",
            "event": "Failed to process request",
            "service": "office",
            "request_id": "9f1b0f5d-a388-4ae2-8d66-67256cc71235",
            "user_id": "demo@example.com",
            "file": "health.py",
            "line": 123,
            "error_code": 500,
            "method": "GET",
            "path": "/v1/health",
        }

        result = renderer(MagicMock(), "error", event_dict)

        # Check all components are present
        assert "2025-07-25T23:05:05.247325Z" in result
        assert "[office]" in result
        assert "[ERROR]" in result
        assert "[1235]" in result  # Request ID suffix
        assert (
            "office.api.health" in result
        )  # Cleaned logger name without "services." prefix
        assert "Failed to process request" in result
        assert "| User: demo@example.com" in result
        assert "error_code=500" in result
        assert "method=GET" in result
        assert "path=/v1/health" in result
        # File and line information should be shown as extra context
        assert "file=health.py" in result
        assert "line=123" in result

    def test_enhanced_text_renderer_long_values(self):
        """Test that long values are handled appropriately."""
        renderer = EnhancedTextRenderer("test-service")

        long_value = "x" * 100  # Very long string

        event_dict = {
            "timestamp": "2025-07-25T23:05:05.247325Z",
            "level": "INFO",
            "logger": "services.test.main",
            "event": "Test message",
            "service": "test",
            "long_field": long_value,
        }

        result = renderer(MagicMock(), "info", event_dict)

        # Should include the field name
        assert "long_field=" in result
        # Should include the long value (we don't truncate strings)
        assert long_value in result
        # The result should be reasonably sized (allow for the long value)
        assert len(result) < 3000  # Allow for longer output with all the formatting

    def test_setup_service_logging_text_format(self):
        """Test that setup_service_logging works with text format."""
        # This test verifies the integration works
        setup_service_logging(
            service_name="test-service", log_level="INFO", log_format="text"
        )

        logger = get_logger("services.test.main")

        # Set up context for testing
        request_id_var.set("test-request-123")
        user_id_var.set("test@example.com")

        # This should not raise any exceptions
        logger.info("Test message", test_field="test_value")

    def test_setup_service_logging_json_format(self):
        """Test that setup_service_logging still works with JSON format."""
        setup_service_logging(
            service_name="test-service", log_level="INFO", log_format="json"
        )

        logger = get_logger("services.test.main")

        # Set up context for testing
        request_id_var.set("test-request-123")
        user_id_var.set("test@example.com")

        # This should not raise any exceptions
        logger.info("Test message", test_field="test_value")

    def test_request_id_truncation_edge_cases(self):
        """Test request ID truncation with various lengths."""
        renderer = EnhancedTextRenderer("test-service")

        # Test with 4-character ID
        event_dict = {
            "timestamp": "2025-07-25T23:05:05.247325Z",
            "level": "INFO",
            "logger": "services.test.main",
            "event": "Test",
            "service": "test",
            "request_id": "1234",
        }

        result = renderer(MagicMock(), "info", event_dict)
        assert "[1234]" in result

        # Test with 3-character ID
        event_dict["request_id"] = "123"
        result = renderer(MagicMock(), "info", event_dict)
        assert "[123]" in result

        # Test with empty ID
        event_dict["request_id"] = ""
        result = renderer(MagicMock(), "info", event_dict)
        assert "[1234]" not in result  # Should not show anything

    def test_service_name_extraction_edge_cases(self):
        """Test service name extraction with various logger names."""
        # Test with standard service logger
        event_dict = {"logger": "services.chat.api.health", "event": "test"}
        result = add_service_context(MagicMock(), "info", event_dict)
        assert result["service"] == "chat"

        # Test with single-level logger
        event_dict = {"logger": "services", "event": "test"}
        result = add_service_context(MagicMock(), "info", event_dict)
        assert "service" not in result  # Not enough levels

        # Test with non-service logger
        event_dict = {"logger": "other.package.module", "event": "test"}
        result = add_service_context(MagicMock(), "info", event_dict)
        assert "service" not in result

        # Test with empty logger name
        event_dict = {"logger": "", "event": "test"}
        result = add_service_context(MagicMock(), "info", event_dict)
        assert "service" not in result


class TestLoggingIntegration:
    """Integration tests for the complete logging system."""

    def setup_method(self):
        """Set up test environment."""
        # Reset context variables
        request_id_var.set("uninitialized")
        user_id_var.set("anonymous")

        # Clear any existing logging configuration
        logging.getLogger().handlers.clear()
        structlog.reset_defaults()

    def test_complete_logging_flow(self):
        """Test the complete logging flow with all features."""
        # Set up logging
        setup_service_logging(
            service_name="integration-test-service", log_level="INFO", log_format="text"
        )

        # Set up context
        request_id = str(uuid.uuid4())
        user_id = "integration@test.com"
        request_id_var.set(request_id)
        user_id_var.set(user_id)

        # Get logger
        logger = get_logger("services.integration.test")

        # Log a message
        logger.info(
            "Integration test message", test_field="test_value", numeric_field=42
        )

        # The logging should complete without errors
        # We can't easily capture the output in a unit test,
        # but we can verify the system doesn't crash

    def test_logging_without_context(self):
        """Test logging works correctly without request context."""
        setup_service_logging(
            service_name="no-context-service", log_level="INFO", log_format="text"
        )

        logger = get_logger("services.no.context")

        # Log without setting context variables
        logger.info("Message without context", field="value")

        # Should complete without errors
