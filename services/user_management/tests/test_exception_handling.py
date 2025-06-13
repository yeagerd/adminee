"""
Unit tests for exception handling and error response formatting.

Tests all custom exception types, error response format, user-friendly messages,
and exception hierarchy.
"""

import uuid
from datetime import datetime

from services.user_management.exceptions import (
    AuditException,
    AuthenticationException,
    AuthorizationException,
    DatabaseException,
    EncryptionException,
    IntegrationAlreadyExistsException,
    IntegrationException,
    IntegrationNotFoundException,
    InternalError,
    NotFoundError,
    PreferencesNotFoundException,
    ServiceException,
    TokenExpiredException,
    TokenNotFoundException,
    UserAlreadyExistsException,
    UserManagementException,
    UserNotFoundException,
    ValidationException,
    WebhookValidationException,
)


class TestUserManagementExceptionBase:
    """Test cases for the base UserManagementException class."""

    def test_base_exception_creation(self):
        """Test basic exception creation with all parameters."""
        details = {"key": "value", "count": 42}
        exc = UserManagementException(
            message="Test error",
            details=details,
            error_type="test_error",
            error_code="TEST_CODE",
        )

        assert exc.message == "Test error"
        assert exc.details == details
        assert exc.error_type == "test_error"
        assert exc.error_code == "TEST_CODE"
        assert isinstance(exc.timestamp, str)
        assert exc.request_id is not None

    def test_exception_with_defaults(self):
        """Test exception creation with default values."""
        exc = UserManagementException("Simple error")

        assert exc.message == "Simple error"
        assert exc.details == {}
        assert exc.error_type == "internal_error"
        assert exc.error_code is None

    def test_to_error_response_format(self):
        """Test the standardized error response format."""
        exc = UserManagementException(
            message="Test error",
            details={"field": "value"},
            error_type="validation_error",
            error_code="VALIDATION_FAILED",
        )

        response = exc.to_error_response()

        assert "error" in response
        error = response["error"]

        assert error["type"] == "validation_error"
        assert error["message"] == "Test error"
        assert "user_message" in error
        assert error["details"]["field"] == "value"
        assert error["details"]["code"] == "VALIDATION_FAILED"
        assert "timestamp" in error
        assert "request_id" in error

    def test_user_friendly_messages(self):
        """Test user-friendly message generation."""
        test_cases = [
            ("AUTH_FAILED", "Please check your login credentials and try again."),
            ("VALIDATION_FAILED", "Please check your input and try again."),
            ("NOT_FOUND", "The requested resource could not be found."),
            (
                "INTERNAL_ERROR",
                "An unexpected error occurred. Our team has been notified.",
            ),
        ]

        for error_code, expected_message in test_cases:
            exc = UserManagementException("Technical error", error_code=error_code)
            response = exc.to_error_response()
            assert response["error"]["user_message"] == expected_message

    def test_user_friendly_fallback_by_type(self):
        """Test user-friendly message fallback based on error type."""
        exc = UserManagementException("Error", error_type="validation_error")
        response = exc.to_error_response()
        assert "check your input" in response["error"]["user_message"]


class TestValidationExceptions:
    """Test cases for validation-related exceptions."""

    def test_validation_exception_creation(self):
        """Test ValidationException creation with field details."""
        exc = ValidationException(
            field="email",
            value="invalid@",
            reason="Invalid email format",
        )

        assert exc.field == "email"
        assert exc.value == "invalid@"
        assert exc.reason == "Invalid email format"
        assert exc.error_type == "validation_error"
        assert exc.error_code == "VALIDATION_FAILED"
        assert "Validation failed for field 'email'" in exc.message

    def test_validation_exception_response(self):
        """Test ValidationException error response."""
        exc = ValidationException("username", "a", "Too short")
        response = exc.to_error_response()

        error = response["error"]
        assert error["type"] == "validation_error"
        assert error["details"]["field"] == "username"
        assert error["details"]["value"] == "a"


class TestAuthenticationExceptions:
    """Test cases for authentication-related exceptions."""

    def test_authentication_exception_creation(self):
        """Test AuthenticationException creation."""
        exc = AuthenticationException("Invalid token")

        assert exc.message == "Invalid token"
        assert exc.error_type == "auth_error"
        assert exc.error_code == "AUTH_FAILED"

    def test_authentication_exception_default_message(self):
        """Test AuthenticationException with default message."""
        exc = AuthenticationException()
        assert "Authentication failed" in exc.message


class TestAuthorizationExceptions:
    """Test cases for authorization-related exceptions."""

    def test_authorization_exception_creation(self):
        """Test AuthorizationException creation."""
        exc = AuthorizationException("users", "delete")

        assert exc.resource == "users"
        assert exc.action == "delete"
        assert exc.error_type == "auth_error"
        assert exc.error_code == "AUTHORIZATION_FAILED"
        assert "Not authorized to delete users" in exc.message

    def test_authorization_exception_response(self):
        """Test AuthorizationException error response."""
        exc = AuthorizationException("profiles", "view")
        response = exc.to_error_response()

        error = response["error"]
        assert error["details"]["resource"] == "profiles"
        assert error["details"]["action"] == "view"


class TestIntegrationExceptions:
    """Test cases for integration-related exceptions."""

    def test_integration_not_found_exception(self):
        """Test IntegrationNotFoundException creation."""
        exc = IntegrationNotFoundException("user123", "google")

        assert exc.user_id == "user123"
        assert exc.provider == "google"
        assert exc.error_code == "INTEGRATION_NOT_FOUND"
        assert "Integration google for user user123 not found" in exc.message

    def test_integration_already_exists_exception(self):
        """Test IntegrationAlreadyExistsException creation."""
        exc = IntegrationAlreadyExistsException("user123", "microsoft")

        assert exc.user_id == "user123"
        assert exc.provider == "microsoft"
        assert exc.error_code == "INTEGRATION_ALREADY_EXISTS"

    def test_integration_exception_general(self):
        """Test general IntegrationException."""
        exc = IntegrationException("OAuth flow failed")

        assert exc.error_type == "integration_error"
        assert "Integration operation failed: OAuth flow failed" in exc.message


class TestTokenExceptions:
    """Test cases for token-related exceptions."""

    def test_token_not_found_exception(self):
        """Test TokenNotFoundException creation."""
        exc = TokenNotFoundException("user123", "google", "access_token")

        assert exc.user_id == "user123"
        assert exc.provider == "google"
        assert exc.token_type == "access_token"
        assert exc.error_code == "TOKEN_NOT_FOUND"

    def test_token_expired_exception(self):
        """Test TokenExpiredException creation."""
        exc = TokenExpiredException("user123", "microsoft", "refresh_token")

        assert exc.user_id == "user123"
        assert exc.provider == "microsoft"
        assert exc.token_type == "refresh_token"
        assert exc.error_code == "TOKEN_EXPIRED"


class TestNotFoundExceptions:
    """Test cases for not found exceptions."""

    def test_user_not_found_exception(self):
        """Test UserNotFoundException creation."""
        exc = UserNotFoundException("user123")

        assert exc.user_id == "user123"
        assert exc.error_code == "USER_NOT_FOUND"
        assert "User user123 not found" in exc.message

    def test_preferences_not_found_exception(self):
        """Test PreferencesNotFoundException creation."""
        exc = PreferencesNotFoundException("user123")

        assert exc.user_id == "user123"
        assert exc.error_code == "PREFERENCES_NOT_FOUND"

    def test_not_found_error_generic(self):
        """Test generic NotFoundError."""
        exc = NotFoundError("Document", "doc123")

        assert exc.error_code == "NOT_FOUND"
        assert "Document doc123 not found" in exc.message

    def test_not_found_error_without_identifier(self):
        """Test NotFoundError without identifier."""
        exc = NotFoundError("Resource")

        assert "Resource not found" in exc.message


class TestUserAlreadyExistsException:
    """Test cases for user already exists exceptions."""

    def test_user_already_exists_exception(self):
        """Test UserAlreadyExistsException creation."""
        exc = UserAlreadyExistsException("test@example.com")

        assert exc.email == "test@example.com"
        assert exc.error_code == "USER_ALREADY_EXISTS"
        assert "User with email test@example.com already exists" in exc.message


class TestSystemExceptions:
    """Test cases for system-level exceptions."""

    def test_encryption_exception(self):
        """Test EncryptionException creation."""
        exc = EncryptionException("encrypt")

        assert exc.error_type == "encryption_error"
        assert exc.error_code == "ENCRYPTION_FAILED"
        assert "Token encrypt failed" in exc.message

    def test_database_exception(self):
        """Test DatabaseException creation."""
        exc = DatabaseException("Connection timeout")

        assert exc.error_type == "internal_error"
        assert exc.error_code == "DATABASE_ERROR"

    def test_service_exception(self):
        """Test ServiceException creation."""
        exc = ServiceException("payment", "charge", "API timeout")

        assert exc.service == "payment"
        assert exc.operation == "charge"
        assert exc.error_code == "SERVICE_ERROR"

    def test_audit_exception(self):
        """Test AuditException creation."""
        exc = AuditException("Log write failed")

        assert exc.error_type == "internal_error"
        assert exc.error_code == "AUDIT_ERROR"

    def test_internal_error(self):
        """Test InternalError creation."""
        exc = InternalError("System failure")

        assert exc.error_type == "internal_error"
        assert exc.error_code == "INTERNAL_ERROR"


class TestWebhookExceptions:
    """Test cases for webhook-related exceptions."""

    def test_webhook_validation_exception(self):
        """Test WebhookValidationException creation."""
        exc = WebhookValidationException("clerk", "Invalid signature")

        assert exc.provider == "clerk"
        assert exc.reason == "Invalid signature"
        assert exc.error_code == "WEBHOOK_VALIDATION_FAILED"


class TestExceptionHierarchy:
    """Test cases for exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from UserManagementException."""
        exception_classes = [
            ValidationException,
            AuthenticationException,
            AuthorizationException,
            IntegrationNotFoundException,
            TokenNotFoundException,
            UserNotFoundException,
            EncryptionException,
            DatabaseException,
            ServiceException,
            AuditException,
            WebhookValidationException,
        ]

        for exc_class in exception_classes:
            # Create instance with minimal args
            if exc_class == ValidationException:
                exc = exc_class("field", "value", "reason")
            elif exc_class == AuthorizationException:
                exc = exc_class("resource", "action")
            elif exc_class in [IntegrationNotFoundException, TokenNotFoundException]:
                exc = (
                    exc_class("user", "provider", "type")
                    if exc_class == TokenNotFoundException
                    else exc_class("user", "provider")
                )
            elif exc_class in [UserNotFoundException, PreferencesNotFoundException]:
                exc = exc_class("user123")
            elif exc_class in [EncryptionException, DatabaseException, AuditException]:
                exc = exc_class(
                    "operation" if exc_class == EncryptionException else "reason"
                )
            elif exc_class == ServiceException:
                exc = exc_class("service", "operation", "reason")
            elif exc_class == WebhookValidationException:
                exc = exc_class("provider", "reason")
            else:
                exc = exc_class("test message")

            assert isinstance(exc, UserManagementException)

    def test_exception_response_consistency(self):
        """Test that all exceptions produce consistent response format."""
        exceptions = [
            ValidationException("email", "invalid", "Bad format"),
            AuthenticationException("Bad token"),
            UserNotFoundException("user123"),
            DatabaseException("Connection lost"),
        ]

        for exc in exceptions:
            response = exc.to_error_response()

            # Check required fields
            assert "error" in response
            error = response["error"]

            required_fields = [
                "type",
                "message",
                "user_message",
                "details",
                "timestamp",
                "request_id",
            ]
            for field in required_fields:
                assert (
                    field in error
                ), f"Missing field '{field}' in {type(exc).__name__} response"

            # Check field types
            assert isinstance(error["type"], str)
            assert isinstance(error["message"], str)
            assert isinstance(error["user_message"], str)
            assert isinstance(error["details"], dict)
            assert isinstance(error["timestamp"], str)
            assert isinstance(error["request_id"], str)


class TestErrorResponseDetails:
    """Test cases for error response detail fields."""

    def test_error_response_includes_error_code(self):
        """Test that error responses include error codes when present."""
        exc = UserNotFoundException("user123")
        response = exc.to_error_response()

        assert response["error"]["details"]["code"] == "USER_NOT_FOUND"

    def test_error_response_without_error_code(self):
        """Test error response when error code is None."""
        exc = UserManagementException("Error without code")
        response = exc.to_error_response()

        # Should not include 'code' key when error_code is None
        assert "code" not in response["error"]["details"]

    def test_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        exc = UserManagementException("Test error")
        response = exc.to_error_response()

        timestamp = response["error"]["timestamp"]
        # Should be parseable as ISO datetime
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)

    def test_request_id_uniqueness(self):
        """Test that request IDs are unique."""
        exc1 = UserManagementException("Error 1")
        exc2 = UserManagementException("Error 2")

        response1 = exc1.to_error_response()
        response2 = exc2.to_error_response()

        assert response1["error"]["request_id"] != response2["error"]["request_id"]

    def test_request_id_format(self):
        """Test that request ID is a valid UUID."""
        exc = UserManagementException("Test error")
        response = exc.to_error_response()

        request_id = response["error"]["request_id"]
        # Should be parseable as UUID
        uuid.UUID(request_id)  # Raises ValueError if invalid


class TestExceptionStringRepresentation:
    """Test cases for exception string representations."""

    def test_exception_str_representation(self):
        """Test that exceptions have proper string representation."""
        exc = UserNotFoundException("user123")

        exc_str = str(exc)
        assert "User user123 not found" in exc_str

    def test_nested_exception_details(self):
        """Test exceptions with nested detail structures."""
        details = {
            "operation": "token_refresh",
            "metadata": {"attempt": 2, "last_error": "timeout"},
        }
        exc = TokenExpiredException("user123", "google", "refresh", details)

        response = exc.to_error_response()
        assert response["error"]["details"]["operation"] == "token_refresh"
        assert response["error"]["details"]["metadata"]["attempt"] == 2
