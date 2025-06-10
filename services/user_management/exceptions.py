"""
Custom exceptions for User Management Service.

Defines application-specific exceptions with proper HTTP status codes
and structured error responses.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class UserManagementException(Exception):
    """Base exception for User Management Service."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class UserNotFoundException(UserManagementException):
    """Exception raised when a user is not found."""

    def __init__(self, user_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"User {user_id} not found"
        super().__init__(message, details)
        self.user_id = user_id


class UserAlreadyExistsException(UserManagementException):
    """Exception raised when trying to create a user that already exists."""

    def __init__(self, email: str, details: Optional[Dict[str, Any]] = None):
        message = f"User with email {email} already exists"
        super().__init__(message, details)
        self.email = email


class PreferencesNotFoundException(UserManagementException):
    """Exception raised when user preferences are not found."""

    def __init__(self, user_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"Preferences for user {user_id} not found"
        super().__init__(message, details)
        self.user_id = user_id


class IntegrationNotFoundException(UserManagementException):
    """Exception raised when an integration is not found."""

    def __init__(
        self, user_id: str, provider: str, details: Optional[Dict[str, Any]] = None
    ):
        message = f"Integration {provider} for user {user_id} not found"
        super().__init__(message, details)
        self.user_id = user_id
        self.provider = provider


class IntegrationAlreadyExistsException(UserManagementException):
    """Exception raised when trying to create an integration that already exists."""

    def __init__(
        self, user_id: str, provider: str, details: Optional[Dict[str, Any]] = None
    ):
        message = f"Integration {provider} for user {user_id} already exists"
        super().__init__(message, details)
        self.user_id = user_id
        self.provider = provider


class TokenNotFoundException(UserManagementException):
    """Exception raised when a token is not found."""

    def __init__(
        self,
        user_id: str,
        provider: str,
        token_type: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = (
            f"Token {token_type} for {provider} integration of user {user_id} not found"
        )
        super().__init__(message, details)
        self.user_id = user_id
        self.provider = provider
        self.token_type = token_type


class TokenExpiredException(UserManagementException):
    """Exception raised when a token has expired."""

    def __init__(
        self,
        user_id: str,
        provider: str,
        token_type: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Token {token_type} for {provider} integration of user {user_id} has expired"
        super().__init__(message, details)
        self.user_id = user_id
        self.provider = provider
        self.token_type = token_type


class EncryptionException(UserManagementException):
    """Exception raised when token encryption/decryption fails."""

    def __init__(self, operation: str, details: Optional[Dict[str, Any]] = None):
        message = f"Token {operation} failed"
        super().__init__(message, details)
        self.operation = operation


class ValidationException(UserManagementException):
    """Exception raised when request validation fails."""

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Validation failed for field '{field}': {reason}"
        super().__init__(message, details)
        self.field = field
        self.value = value
        self.reason = reason


class AuthenticationException(UserManagementException):
    """Exception raised when authentication fails."""

    def __init__(
        self,
        reason: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(reason, details)


class AuthorizationException(UserManagementException):
    """Exception raised when authorization fails."""

    def __init__(
        self, resource: str, action: str, details: Optional[Dict[str, Any]] = None
    ):
        message = f"Not authorized to {action} {resource}"
        super().__init__(message, details)
        self.resource = resource
        self.action = action


class ServiceException(UserManagementException):
    """Exception raised when a service operation fails."""

    def __init__(
        self,
        service: str,
        operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Service {service} operation {operation} failed: {reason}"
        super().__init__(message, details)
        self.service = service
        self.operation = operation
        self.reason = reason


class WebhookValidationException(UserManagementException):
    """Exception raised when webhook signature validation fails."""

    def __init__(
        self, provider: str, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        message = f"Webhook validation failed for {provider}: {reason}"
        super().__init__(message, details)
        self.provider = provider
        self.reason = reason


class WebhookProcessingError(UserManagementException):
    """Exception raised when webhook processing fails."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Webhook processing failed: {reason}"
        super().__init__(message, details)
        self.reason = reason


class DatabaseError(UserManagementException):
    """Exception raised when database operations fail."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Database operation failed: {reason}"
        super().__init__(message, details)
        self.reason = reason


class DatabaseException(UserManagementException):
    """Exception raised when database operations fail (alias for compatibility)."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Database operation failed: {reason}"
        super().__init__(message, details)
        self.reason = reason


class AuditException(UserManagementException):
    """Exception raised when audit logging operations fail."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Audit operation failed: {reason}"
        super().__init__(message, details)
        self.reason = reason


# HTTP Exception mappings for FastAPI
def user_not_found_exception(user_id: str) -> HTTPException:
    """Create HTTPException for user not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "UserNotFound",
            "message": f"User {user_id} not found",
            "user_id": user_id,
        },
    )


def preferences_not_found_exception(user_id: str) -> HTTPException:
    """Create HTTPException for preferences not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "PreferencesNotFound",
            "message": f"Preferences for user {user_id} not found",
            "user_id": user_id,
        },
    )


def integration_not_found_exception(user_id: str, provider: str) -> HTTPException:
    """Create HTTPException for integration not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "IntegrationNotFound",
            "message": f"Integration {provider} for user {user_id} not found",
            "user_id": user_id,
            "provider": provider,
        },
    )


def validation_exception(field: str, reason: str) -> HTTPException:
    """Create HTTPException for validation errors."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": "ValidationError",
            "message": f"Validation failed for field '{field}': {reason}",
            "field": field,
            "reason": reason,
        },
    )


def authentication_exception(reason: str = "Authentication failed") -> HTTPException:
    """Create HTTPException for authentication errors."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "AuthenticationError",
            "message": reason,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def authorization_exception(resource: str, action: str) -> HTTPException:
    """Create HTTPException for authorization errors."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "AuthorizationError",
            "message": f"Not authorized to {action} {resource}",
            "resource": resource,
            "action": action,
        },
    )
