"""
Custom exceptions for User Management Service.

Defines application-specific exceptions with proper HTTP status codes
and structured error responses.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class UserManagementException(Exception):
    """Base exception for User Management Service."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_type: str = "internal_error",
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.details = details or {}
        self.error_type = error_type
        self.error_code = error_code
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.request_id = str(uuid.uuid4())
        super().__init__(self.message)

    def to_error_response(self) -> Dict[str, Any]:
        """Convert exception to standardized error response format."""
        user_friendly_message = self._get_user_friendly_message()

        return {
            "error": {
                "type": self.error_type,
                "message": self.message,
                "user_message": user_friendly_message,
                "details": {
                    **self.details,
                    **({"code": self.error_code} if self.error_code else {}),
                },
                "timestamp": self.timestamp,
                "request_id": self.request_id,
            }
        }

    def _get_user_friendly_message(self) -> str:
        """Get user-friendly error message based on error type and code."""
        # Map common error codes to user-friendly messages
        user_friendly_messages = {
            "AUTH_FAILED": "Please check your login credentials and try again.",
            "AUTHORIZATION_FAILED": "You don't have permission to perform this action.",
            "VALIDATION_FAILED": "Please check your input and try again.",
            "USER_NOT_FOUND": "The requested user could not be found.",
            "INTEGRATION_NOT_FOUND": "The integration you're looking for doesn't exist.",
            "INTEGRATION_ERROR": "There was a problem with the integration. Please try again later.",
            "TOKEN_EXPIRED": "Your session has expired. Please log in again.",
            "TOKEN_NOT_FOUND": "Authentication token is missing. Please log in again.",
            "ENCRYPTION_FAILED": "A security error occurred. Please try again later.",
            "DATABASE_ERROR": "A temporary service issue occurred. Please try again in a moment.",
            "INTERNAL_ERROR": "An unexpected error occurred. Our team has been notified.",
            "WEBHOOK_ERROR": "There was an issue processing the webhook.",
            "NOT_FOUND": "The requested resource could not be found.",
        }

        # Get user-friendly message based on error code
        if self.error_code and self.error_code in user_friendly_messages:
            return user_friendly_messages[self.error_code]

        # Fallback user-friendly messages based on error type
        type_messages = {
            "validation_error": "Please check your input and correct any errors.",
            "auth_error": "Authentication is required to access this resource.",
            "integration_error": "There was an issue with the integration service.",
            "encryption_error": "A security error occurred. Please try again later.",
            "not_found": "The requested resource could not be found.",
            "internal_error": "An unexpected error occurred. Please try again later.",
        }

        return type_messages.get(
            self.error_type, "An error occurred. Please try again later."
        )


# Validation Errors
class ValidationError(UserManagementException):
    """Exception raised when request validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        validation_details = details or {}
        if field:
            validation_details["field"] = field
        if value is not None:
            validation_details["value"] = str(value)

        super().__init__(
            message=message,
            details=validation_details,
            error_type="validation_error",
            error_code="VALIDATION_FAILED",
        )
        self.field = field
        self.value = value


class ValidationException(ValidationError):
    """Legacy alias for ValidationError - keep for backward compatibility."""

    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Validation failed for field '{field}': {reason}"
        super().__init__(
            message=message,
            field=field,
            value=value,
            details=details,
        )
        self.reason = reason


class SimpleValidationException(ValidationError):
    """Simple validation exception without field-specific details."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)


# Authentication & Authorization Errors
class AuthenticationError(UserManagementException):
    """Exception raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "AUTH_FAILED",
    ):
        super().__init__(
            message=message,
            details=details,
            error_type="auth_error",
            error_code=error_code,
        )


class AuthenticationException(AuthenticationError):
    """Legacy alias for AuthenticationError - keep for backward compatibility."""

    def __init__(
        self,
        reason: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=reason, details=details)


class AuthorizationError(UserManagementException):
    """Exception raised when authorization fails."""

    def __init__(
        self,
        resource: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Not authorized to {action} {resource}"
        auth_details = {**(details or {}), "resource": resource, "action": action}
        super().__init__(
            message=message,
            details=auth_details,
            error_type="auth_error",
            error_code="AUTHORIZATION_FAILED",
        )
        self.resource = resource
        self.action = action


class AuthorizationException(AuthorizationError):
    """Legacy alias for AuthorizationError - keep for backward compatibility."""

    def __init__(
        self, resource: str, action: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(resource=resource, action=action, details=details)


# Integration Errors
class IntegrationError(UserManagementException):
    """Exception raised when integration operations fail."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "INTEGRATION_ERROR",
    ):
        integration_details = details or {}
        if provider:
            integration_details["provider"] = provider
        if user_id:
            integration_details["user_id"] = user_id

        super().__init__(
            message=message,
            details=integration_details,
            error_type="integration_error",
            error_code=error_code,
        )
        self.provider = provider
        self.user_id = user_id


class IntegrationException(IntegrationError):
    """Legacy alias for IntegrationError - keep for backward compatibility."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Integration operation failed: {reason}", details=details
        )


class IntegrationNotFoundError(IntegrationError):
    """Exception raised when an integration is not found."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if user_id and provider:
            message = f"Integration {provider} for user {user_id} not found"
        elif provider:
            message = f"Integration {provider} not found"
        else:
            message = "Integration not found"

        super().__init__(
            message=message,
            provider=provider,
            user_id=user_id,
            details=details,
            error_code="INTEGRATION_NOT_FOUND",
        )


class IntegrationNotFoundException(IntegrationNotFoundError):
    """Legacy alias for IntegrationNotFoundError - keep for backward compatibility."""

    def __init__(
        self, user_id: str, provider: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(user_id=user_id, provider=provider, details=details)


class IntegrationAlreadyExistsError(IntegrationError):
    """Exception raised when trying to create an integration that already exists."""

    def __init__(
        self,
        user_id: str,
        provider: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Integration {provider} for user {user_id} already exists"
        super().__init__(
            message=message,
            provider=provider,
            user_id=user_id,
            details=details,
            error_code="INTEGRATION_ALREADY_EXISTS",
        )


class IntegrationAlreadyExistsException(IntegrationAlreadyExistsError):
    """Legacy alias for IntegrationAlreadyExistsError - keep for backward compatibility."""

    def __init__(
        self, user_id: str, provider: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(user_id=user_id, provider=provider, details=details)


class InvalidOAuthStateError(IntegrationError):
    """Exception raised when OAuth state validation fails."""

    def __init__(
        self,
        provider: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Invalid OAuth state for {provider}"
        super().__init__(
            message=message,
            provider=provider,
            details=details,
            error_code="INVALID_OAUTH_STATE",
        )


class InsufficientScopesError(IntegrationError):
    """Exception raised when required scopes are not available."""

    def __init__(
        self,
        provider: str,
        required_scopes: list,
        granted_scopes: list,
        details: Optional[Dict[str, Any]] = None,
    ):
        missing_scopes = set(required_scopes) - set(granted_scopes)
        message = (
            f"Insufficient scopes for {provider}. Missing: {', '.join(missing_scopes)}"
        )

        scopes_details = details or {}
        scopes_details.update(
            {
                "required_scopes": required_scopes,
                "granted_scopes": granted_scopes,
                "missing_scopes": list(missing_scopes),
            }
        )

        super().__init__(
            message=message,
            provider=provider,
            details=scopes_details,
            error_code="INSUFFICIENT_SCOPES",
        )
        self.required_scopes = required_scopes
        self.granted_scopes = granted_scopes


# Token Errors
class TokenError(UserManagementException):
    """Base exception for token-related errors."""

    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        token_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "TOKEN_ERROR",
    ):
        token_details = details or {}
        if user_id:
            token_details["user_id"] = user_id
        if provider:
            token_details["provider"] = provider
        if token_type:
            token_details["token_type"] = token_type

        super().__init__(
            message=message,
            details=token_details,
            error_type="integration_error",  # Token errors are integration-related
            error_code=error_code,
        )
        self.user_id = user_id
        self.provider = provider
        self.token_type = token_type


class TokenNotFoundError(TokenError):
    """Exception raised when a token is not found."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        token_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if all([user_id, provider, token_type]):
            message = f"Token {token_type} for {provider} integration of user {user_id} not found"
        elif provider and token_type:
            message = f"Token {token_type} for {provider} not found"
        else:
            message = "Token not found"

        super().__init__(
            message=message,
            user_id=user_id,
            provider=provider,
            token_type=token_type,
            details=details,
            error_code="TOKEN_NOT_FOUND",
        )


class TokenNotFoundException(TokenNotFoundError):
    """Legacy alias for TokenNotFoundError - keep for backward compatibility."""

    def __init__(
        self,
        user_id: str,
        provider: str,
        token_type: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            user_id=user_id,
            provider=provider,
            token_type=token_type,
            details=details,
        )


class RefreshTokenNotFoundError(TokenError):
    """Exception raised when a refresh token is not found."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if user_id and provider:
            message = (
                f"Refresh token for {provider} integration of user {user_id} not found"
            )
        else:
            message = "Refresh token not found"

        super().__init__(
            message=message,
            user_id=user_id,
            provider=provider,
            token_type="refresh_token",
            details=details,
            error_code="REFRESH_TOKEN_NOT_FOUND",
        )


class TokenExpiredError(TokenError):
    """Exception raised when a token has expired."""

    def __init__(
        self,
        user_id: str,
        provider: str,
        token_type: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Token {token_type} for {provider} integration of user {user_id} has expired"
        super().__init__(
            message=message,
            user_id=user_id,
            provider=provider,
            token_type=token_type,
            details=details,
            error_code="TOKEN_EXPIRED",
        )


class TokenExpiredException(TokenExpiredError):
    """Legacy alias for TokenExpiredError - keep for backward compatibility."""

    def __init__(
        self,
        user_id: str,
        provider: str,
        token_type: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            user_id=user_id,
            provider=provider,
            token_type=token_type,
            details=details,
        )


# Encryption Errors
class EncryptionError(UserManagementException):
    """Exception raised when token encryption/decryption fails."""

    def __init__(
        self,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "ENCRYPTION_FAILED",
    ):
        message = f"Token {operation} failed"
        encryption_details = {**(details or {}), "operation": operation}
        super().__init__(
            message=message,
            details=encryption_details,
            error_type="encryption_error",
            error_code=error_code,
        )
        self.operation = operation


class EncryptionException(EncryptionError):
    """Legacy alias for EncryptionError - keep for backward compatibility."""

    def __init__(self, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(operation=operation, details=details)


# Not Found Errors
class NotFoundError(UserManagementException):
    """Base exception for resource not found errors."""

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "NOT_FOUND",
    ):
        if identifier:
            message = f"{resource} {identifier} not found"
        else:
            message = f"{resource} not found"

        notfound_details = {
            **(details or {}),
            "resource": resource,
            "identifier": identifier,
        }
        super().__init__(
            message=message,
            details=notfound_details,
            error_type="not_found",
            error_code=error_code,
        )
        self.resource = resource
        self.identifier = identifier


class NotFoundException(NotFoundError):
    """Legacy alias for NotFoundError - keep for backward compatibility."""

    def __init__(self, resource: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(resource=resource, details=details)


class UserNotFoundError(NotFoundError):
    """Exception raised when a user is not found."""

    def __init__(self, user_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            resource="User",
            identifier=user_id,
            details=details,
            error_code="USER_NOT_FOUND",
        )
        self.user_id = user_id


class UserNotFoundException(UserNotFoundError):
    """Legacy alias for UserNotFoundError - keep for backward compatibility."""

    def __init__(self, user_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(user_id=user_id, details=details)


class UserAlreadyExistsError(UserManagementException):
    """Exception raised when trying to create a user that already exists."""

    def __init__(self, email: str, details: Optional[Dict[str, Any]] = None):
        message = f"User with email {email} already exists"
        user_details = {**(details or {}), "email": email}
        super().__init__(
            message=message,
            details=user_details,
            error_type="validation_error",
            error_code="USER_ALREADY_EXISTS",
        )
        self.email = email


class UserAlreadyExistsException(UserAlreadyExistsError):
    """Legacy alias for UserAlreadyExistsError - keep for backward compatibility."""

    def __init__(self, email: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(email=email, details=details)


class PreferencesNotFoundError(NotFoundError):
    """Exception raised when user preferences are not found."""

    def __init__(self, user_id: str, details: Optional[Dict[str, Any]] = None):
        prefs_details = {**(details or {}), "user_id": user_id}
        super().__init__(
            resource="Preferences",
            identifier=f"user {user_id}",
            details=prefs_details,
            error_code="PREFERENCES_NOT_FOUND",
        )
        self.user_id = user_id


class PreferencesNotFoundException(PreferencesNotFoundError):
    """Legacy alias for PreferencesNotFoundError - keep for backward compatibility."""

    def __init__(self, user_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(user_id=user_id, details=details)


# Service & Internal Errors
class InternalError(UserManagementException):
    """Exception raised for internal service errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "INTERNAL_ERROR",
    ):
        super().__init__(
            message=message,
            details=details,
            error_type="internal_error",
            error_code=error_code,
        )


class ServiceError(InternalError):
    """Exception raised when a service operation fails."""

    def __init__(
        self,
        service: str,
        operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"Service {service} operation {operation} failed: {reason}"
        service_details = {
            **(details or {}),
            "service": service,
            "operation": operation,
            "reason": reason,
        }
        super().__init__(
            message=message,
            details=service_details,
            error_code="SERVICE_ERROR",
        )
        self.service = service
        self.operation = operation
        self.reason = reason


class ServiceException(ServiceError):
    """Legacy alias for ServiceError - keep for backward compatibility."""

    def __init__(
        self,
        service: str,
        operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            service=service,
            operation=operation,
            reason=reason,
            details=details,
        )


class DatabaseError(InternalError):
    """Exception raised when database operations fail."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Database operation failed: {reason}"
        db_details = {**(details or {}), "reason": reason}
        super().__init__(
            message=message,
            details=db_details,
            error_code="DATABASE_ERROR",
        )
        self.reason = reason


class DatabaseException(DatabaseError):
    """Legacy alias for DatabaseError - keep for backward compatibility."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(reason=reason, details=details)


class AuditError(InternalError):
    """Exception raised when audit operations fail."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Audit operation failed: {reason}"
        audit_details = {**(details or {}), "reason": reason}
        super().__init__(
            message=message,
            details=audit_details,
            error_code="AUDIT_ERROR",
        )
        self.reason = reason


class AuditException(AuditError):
    """Legacy alias for AuditError - keep for backward compatibility."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(reason=reason, details=details)


# Webhook Errors
class WebhookError(UserManagementException):
    """Base exception for webhook-related errors."""

    def __init__(
        self,
        provider: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "WEBHOOK_ERROR",
    ):
        webhook_details = {**(details or {}), "provider": provider}
        super().__init__(
            message=message,
            details=webhook_details,
            error_type="integration_error",
            error_code=error_code,
        )
        self.provider = provider


class WebhookValidationError(WebhookError):
    """Exception raised when webhook signature validation fails."""

    def __init__(
        self, provider: str, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        message = f"Webhook validation failed for {provider}: {reason}"
        validation_details = {**(details or {}), "reason": reason}
        super().__init__(
            provider=provider,
            message=message,
            details=validation_details,
            error_code="WEBHOOK_VALIDATION_FAILED",
        )
        self.reason = reason


class WebhookValidationException(WebhookValidationError):
    """Legacy alias for WebhookValidationError - keep for backward compatibility."""

    def __init__(
        self, provider: str, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(provider=provider, reason=reason, details=details)


class WebhookProcessingError(WebhookError):
    """Exception raised when webhook processing fails."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        message = f"Webhook processing failed: {reason}"
        processing_details = {**(details or {}), "reason": reason}
        super().__init__(
            provider="unknown",
            message=message,
            details=processing_details,
            error_code="WEBHOOK_PROCESSING_FAILED",
        )
        self.reason = reason


# Legacy HTTPException helper functions for backward compatibility
def user_not_found_exception(user_id: str) -> HTTPException:
    """Create HTTP exception for user not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": {
                "type": "not_found",
                "message": f"User {user_id} not found",
                "details": {"user_id": user_id, "code": "USER_NOT_FOUND"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": str(uuid.uuid4()),
            }
        },
    )


def preferences_not_found_exception(user_id: str) -> HTTPException:
    """Create HTTP exception for preferences not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": {
                "type": "not_found",
                "message": f"Preferences for user {user_id} not found",
                "details": {"user_id": user_id, "code": "PREFERENCES_NOT_FOUND"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": str(uuid.uuid4()),
            }
        },
    )


def integration_not_found_exception(user_id: str, provider: str) -> HTTPException:
    """Create HTTP exception for integration not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": {
                "type": "not_found",
                "message": f"Integration {provider} for user {user_id} not found",
                "details": {
                    "user_id": user_id,
                    "provider": provider,
                    "code": "INTEGRATION_NOT_FOUND",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": str(uuid.uuid4()),
            }
        },
    )


def validation_exception(field: str, reason: str) -> HTTPException:
    """Create HTTP exception for validation error."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": {
                "type": "validation_error",
                "message": f"Validation failed for field '{field}': {reason}",
                "details": {
                    "field": field,
                    "reason": reason,
                    "code": "VALIDATION_FAILED",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": str(uuid.uuid4()),
            }
        },
    )


def authentication_exception(reason: str = "Authentication failed") -> HTTPException:
    """Create HTTP exception for authentication error."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {
                "type": "auth_error",
                "message": reason,
                "details": {"code": "AUTH_FAILED"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": str(uuid.uuid4()),
            }
        },
    )


def authorization_exception(resource: str, action: str) -> HTTPException:
    """Create HTTP exception for authorization error."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": {
                "type": "auth_error",
                "message": f"Not authorized to {action} {resource}",
                "details": {
                    "resource": resource,
                    "action": action,
                    "code": "AUTHORIZATION_FAILED",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": str(uuid.uuid4()),
            }
        },
    )
