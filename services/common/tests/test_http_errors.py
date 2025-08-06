"""
Unit tests for HTTP error handling functionality.

Tests the fixes for:
1. Request ID correlation - ensuring the same request ID is used across logs
2. HTTPException detail handling - proper handling of dictionary details
"""

import pytest
from fastapi import HTTPException
from services.common.http_errors import (
    NotFoundError,
    exception_to_response,
    request_id_var,
)


class TestRequestIDCorrelation:
    """Test request ID correlation across exception handlers."""

    def setup_method(self):
        """Reset request_id_var before each test."""
        request_id_var.set("uninitialized")

    def test_request_id_from_context(self):
        """Test that request ID is extracted from context."""
        # Set a request ID in context
        test_request_id = "test-request-123"
        request_id_var.set(test_request_id)

        # Create HTTPException
        http_exc = HTTPException(
            status_code=422, detail={"message": "Validation failed"}
        )

        # Test exception_to_response
        response = exception_to_response(http_exc)
        assert response.request_id == test_request_id

    def test_request_id_uninitialized_context(self):
        """Test request ID handling when context is uninitialized."""
        # Ensure context is uninitialized
        request_id_var.set("uninitialized")

        # Create HTTPException
        http_exc = HTTPException(status_code=404, detail="Not found")

        # Test exception_to_response
        response = exception_to_response(http_exc)
        # Should generate a new UUID instead of "uninitialized"
        assert response.request_id != "uninitialized"
        assert len(response.request_id) > 0

    def test_request_id_generation_outside_context(self):
        """Test that exception_to_response generates proper request IDs outside request context."""
        # Ensure context is uninitialized
        request_id_var.set("uninitialized")

        # Test with different exception types
        test_cases = [
            HTTPException(status_code=422, detail="Validation failed"),
            ValueError("Something went wrong"),
            RuntimeError("Database connection failed"),
        ]

        for exc in test_cases:
            response = exception_to_response(exc)

            # Should generate a new UUID instead of "uninitialized"
            assert response.request_id != "uninitialized"
            assert len(response.request_id) > 0

            # Should be a valid UUID format
            import re

            uuid_pattern = re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                re.IGNORECASE,
            )
            assert uuid_pattern.match(
                response.request_id
            ), f"Invalid UUID format: {response.request_id}"


class TestHTTPExceptionDetailHandling:
    """Test HTTPException detail field handling."""

    def test_dict_detail_with_message_field(self):
        """Test dictionary detail with 'message' field."""
        http_exc = HTTPException(
            status_code=422, detail={"message": "Validation failed", "field": "email"}
        )

        response = exception_to_response(http_exc)

        assert response.type == "http_error"
        assert response.message == "Validation failed"
        assert response.details["detail"]["field"] == "email"
        assert response.details["status_code"] == 422

    def test_dict_detail_with_detail_field(self):
        """Test dictionary detail with 'detail' field."""
        http_exc = HTTPException(
            status_code=400, detail={"detail": "Bad request", "code": "INVALID_INPUT"}
        )

        response = exception_to_response(http_exc)

        assert response.type == "http_error"
        assert response.message == "Bad request"
        assert response.details["detail"]["code"] == "INVALID_INPUT"

    def test_dict_detail_with_error_field(self):
        """Test dictionary detail with 'error' field."""
        http_exc = HTTPException(
            status_code=403, detail={"error": "Access denied", "permission": "read"}
        )

        response = exception_to_response(http_exc)

        assert response.type == "http_error"
        assert response.message == "Access denied"
        assert response.details["detail"]["permission"] == "read"

    def test_dict_detail_with_unknown_fields(self):
        """Test dictionary detail with unknown fields (fallback to str())."""
        http_exc = HTTPException(
            status_code=500, detail={"unknown_field": "value", "another_field": 123}
        )

        response = exception_to_response(http_exc)

        assert response.type == "http_error"
        assert response.message == "{'unknown_field': 'value', 'another_field': 123}"
        assert response.details["detail"]["unknown_field"] == "value"

    def test_string_detail(self):
        """Test string detail handling."""
        http_exc = HTTPException(status_code=404, detail="Resource not found")

        response = exception_to_response(http_exc)

        assert response.type == "http_error"
        assert response.message == "Resource not found"
        assert response.details["detail"] == "Resource not found"

    def test_none_detail(self):
        """Test None detail handling."""
        http_exc = HTTPException(status_code=500, detail=None)

        response = exception_to_response(http_exc)

        assert response.type == "http_error"
        assert response.message == "Internal Server Error"  # FastAPI default message
        assert (
            response.details["detail"] == "Internal Server Error"
        )  # FastAPI converts None to default


class TestExceptionToResponse:
    """Test the exception_to_response utility function."""

    def test_briefly_api_exception(self):
        """Test conversion of BrieflyAPIException."""
        exc = NotFoundError(resource="User", identifier="user-123")
        response = exception_to_response(exc)

        assert response.type == "not_found"  # Actual type from the exception
        assert "User user-123 not found" in response.message
        assert response.details["resource"] == "User"
        assert response.details["identifier"] == "user-123"

    def test_http_exception_string(self):
        """Test conversion of HTTPException with string detail."""
        exc = HTTPException(status_code=404, detail="Not found")
        response = exception_to_response(exc)

        assert response.type == "http_error"
        assert response.message == "Not found"
        assert response.details["detail"] == "Not found"
        assert response.details["status_code"] == 404

    def test_http_exception_dict(self):
        """Test conversion of HTTPException with dictionary detail."""
        exc = HTTPException(
            status_code=422, detail={"message": "Validation failed", "field": "email"}
        )
        response = exception_to_response(exc)

        assert response.type == "http_error"
        assert response.message == "Validation failed"
        assert response.details["detail"]["field"] == "email"

    def test_generic_exception(self):
        """Test generic exception handling."""
        print("Testing generic exception handling...")

        generic_exc = ValueError("Something went wrong")

        response = exception_to_response(generic_exc)

        assert response.type == "internal_error"
        assert response.message == "Something went wrong"
        assert response.details["error_type"] == "ValueError"

        print("✅ Generic exception test passed")

    def test_generic_exception_consistency(self):
        """Test that generic exceptions produce consistent results."""
        exc = RuntimeError("Database connection failed")

        # Test exception_to_response
        response = exception_to_response(exc)

        assert response.type == "internal_error"
        assert response.message == "Database connection failed"
        assert response.details["error_type"] == "RuntimeError"

        # Verify the response structure matches what the handler should produce
        assert hasattr(response, "type")
        assert hasattr(response, "message")
        assert hasattr(response, "details")
        assert hasattr(response, "timestamp")
        assert hasattr(response, "request_id")


class TestBackwardCompatibility:
    """Test backward compatibility of error responses."""

    def test_http_exception_detail_structure_preserved(self):
        """Test that HTTPException detail structure is preserved for backward compatibility."""
        original_detail = {
            "message": "Custom error",
            "field": "email",
            "code": "VALIDATION_FAILED",
            "additional_data": {"nested": "value"},
        }

        http_exc = HTTPException(status_code=422, detail=original_detail)
        response = exception_to_response(http_exc)

        # Verify the original structure is preserved
        assert response.details["detail"] == original_detail
        assert response.details["detail"]["field"] == "email"
        assert response.details["detail"]["code"] == "VALIDATION_FAILED"
        assert response.details["detail"]["additional_data"]["nested"] == "value"

    def test_error_response_structure_consistency(self):
        """Test that error response structure remains consistent."""
        http_exc = HTTPException(
            status_code=400, detail={"message": "Bad request", "field": "input"}
        )
        response = exception_to_response(http_exc)

        # Verify all required fields are present
        assert hasattr(response, "type")
        assert hasattr(response, "message")
        assert hasattr(response, "details")
        assert hasattr(response, "timestamp")
        assert hasattr(response, "request_id")

        # Verify field types
        assert isinstance(response.type, str)
        assert isinstance(response.message, str)
        assert isinstance(response.details, dict)
        assert isinstance(response.timestamp, str)
        assert isinstance(response.request_id, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
