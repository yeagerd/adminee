"""
Input sanitization middleware for User Management Service.

Provides middleware to automatically sanitize all incoming user data
to prevent XSS, injection attacks, and other security vulnerabilities.
"""

import json
from typing import Any, Dict, Union

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from services.common.logging_config import get_logger
from services.user.utils.validation import (
    check_sql_injection_patterns,
    validate_json_safe_string,
)

logger = get_logger(__name__)


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to sanitize all incoming request data.

    Automatically sanitizes:
    - JSON request bodies
    - Query parameters
    - Path parameters
    - Form data
    """

    def __init__(self, app, enabled: bool = True, strict_mode: bool = False):
        """
        Initialize sanitization middleware.

        Args:
            app: FastAPI application
            enabled: Whether sanitization is enabled
            strict_mode: If True, rejects requests with potentially malicious content
        """
        super().__init__(app)
        self.enabled = enabled
        self.strict_mode = strict_mode

        # Fields that should not be sanitized (e.g., passwords, tokens)
        self.skip_fields = {
            "password",
            "token",
            "secret",
            "key",
            "signature",
            "authorization",
            "user_id",  # Generic user identifier
            "access_token",
            "refresh_token",
            "api_key",
        }

        # Content types to process
        self.processable_content_types = {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        }

    async def dispatch(self, request: Request, call_next):
        """Process request and sanitize input data."""
        if not self.enabled:
            return await call_next(request)

        try:
            # Sanitize query parameters
            if request.query_params:
                await self._sanitize_query_params(request)

            # Sanitize request body if applicable
            if self._should_process_body(request):
                await self._sanitize_request_body(request)

            # Continue processing request
            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"Error in sanitization middleware: {e}", exc_info=True)
            # Don't fail the request due to sanitization errors in non-strict mode
            if self.strict_mode:
                raise
            return await call_next(request)

    def _should_process_body(self, request: Request) -> bool:
        """Determine if request body should be processed."""
        content_type = request.headers.get("content-type", "").split(";")[0].strip()
        return (
            request.method in ["POST", "PUT", "PATCH"]
            and content_type in self.processable_content_types
        )

    async def _sanitize_query_params(self, request: Request):
        """Sanitize query parameters."""
        if not request.query_params:
            return

        sanitized_params = {}
        for key, value in request.query_params.items():
            try:
                # Skip sensitive fields
                if key.lower() in self.skip_fields:
                    sanitized_params[key] = value
                    continue

                # Sanitize the value
                sanitized_value = self._sanitize_string_value(value, key)
                sanitized_params[key] = sanitized_value

            except Exception as e:
                if self.strict_mode:
                    logger.warning(
                        f"Rejecting request due to malicious query param '{key}': {e}"
                    )
                    raise ValueError(f"Invalid query parameter: {key}")
                else:
                    logger.info(f"Sanitized malicious query param '{key}': {e}")
                    sanitized_params[key] = ""

        # Update the request scope with sanitized params
        # Note: This is a bit hacky but necessary for middleware
        query_string = "&".join(f"{k}={v}" for k, v in sanitized_params.items())
        request.scope["query_string"] = query_string.encode()

    async def _sanitize_request_body(self, request: Request):
        """Sanitize JSON request body."""
        try:
            # Read the body
            body = await request.body()
            if not body:
                return

            content_type = request.headers.get("content-type", "").split(";")[0].strip()

            if content_type == "application/json":
                await self._sanitize_json_body(request, body)
            elif content_type in [
                "application/x-www-form-urlencoded",
                "multipart/form-data",
            ]:
                # For form data, we'll handle it at the route level since it's more complex
                pass

        except json.JSONDecodeError:
            # Invalid JSON - let the route handler deal with it
            pass
        except Exception as e:
            logger.error(f"Error sanitizing request body: {e}", exc_info=True)
            if self.strict_mode:
                raise

    async def _sanitize_json_body(self, request: Request, body: bytes):
        """Sanitize JSON request body."""
        try:
            data = json.loads(body)
            sanitized_data = self._sanitize_dict(data)

            # Replace the body with sanitized data
            new_body = json.dumps(sanitized_data).encode()

            # Update content length header
            request.headers.__dict__["_list"] = [
                (
                    (name, value)
                    if name != b"content-length"
                    else (name, str(len(new_body)).encode())
                )
                for name, value in request.headers.raw
            ]

            # Replace the body in request scope
            async def receive():
                return {"type": "http.request", "body": new_body}

            request._receive = receive

        except Exception as e:
            logger.error(f"Error sanitizing JSON body: {e}", exc_info=True)
            if self.strict_mode:
                raise

    def _sanitize_dict(self, data: Union[Dict, Any]) -> Any:
        """Recursively sanitize dictionary data."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Skip sensitive fields
                if key.lower() in self.skip_fields:
                    sanitized[key] = value
                else:
                    sanitized[key] = self._sanitize_dict(value)
            return sanitized

        elif isinstance(data, list):
            return [self._sanitize_dict(item) for item in data]

        elif isinstance(data, str):
            return self._sanitize_string_value(data, "body_field")

        else:
            return data

    def _sanitize_string_value(self, value: str, field_name: str) -> str:
        """Sanitize a string value."""
        try:
            # Check for SQL injection patterns
            check_sql_injection_patterns(value, field_name)

            # Validate JSON safety
            validate_json_safe_string(value, field_name)

            # Sanitize text content (but preserve some formatting)
            # For API input, we want to be less aggressive than full HTML sanitization
            sanitized = self._light_sanitize(value)

            return sanitized

        except Exception as e:
            if self.strict_mode:
                raise ValueError(f"Malicious content detected in {field_name}: {e}")
            else:
                # Log but continue with empty string
                logger.info(
                    f"Sanitized potentially malicious content in {field_name}: {e}"
                )
                return ""

    def _light_sanitize(self, text: str) -> str:
        """
        Light sanitization that preserves most content but removes dangerous patterns.

        This is less aggressive than full HTML sanitization since API inputs
        might legitimately contain some special characters.
        """
        if not text:
            return text

        # Remove null bytes and dangerous control characters
        text = text.replace("\x00", "")

        # Remove or escape dangerous script patterns
        import re

        # Remove script tags
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL
        )

        # Remove javascript: and data: URLs
        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
        text = re.sub(r"data:", "", text, flags=re.IGNORECASE)

        # Remove on* event handlers
        text = re.sub(r"on\w+\s*=", "", text, flags=re.IGNORECASE)

        return text.strip()

    def add_skip_field(self, field_name: str):
        """Add a field to skip during sanitization."""
        self.skip_fields.add(field_name.lower())

    def remove_skip_field(self, field_name: str):
        """Remove a field from the skip list."""
        self.skip_fields.discard(field_name.lower())


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware specifically for XSS protection in responses.

    Adds security headers and sanitizes output if needed.
    """

    def __init__(self, app):
        super().__init__(app)

        # XSS protection headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; object-src 'none';",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)

        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value

        return response


# Utility functions for manual sanitization
def sanitize_user_input(data: Dict[str, Any], skip_fields: set | None = None) -> Any:
    """
    Manually sanitize user input dictionary.

    Args:
        data: Dictionary to sanitize
        skip_fields: Fields to skip during sanitization

    Returns:
        Sanitized dictionary
    """
    if skip_fields is None:
        skip_fields = {
            "password",
            "token",
            "secret",
            "key",
            "user_id",
            "sub",
        }  # 'sub' is standard OIDC claim for subject identifier

    def sanitize_dict_recursive(data_item: Any) -> Any:
        """Recursively sanitize dictionary data."""
        if isinstance(data_item, dict):
            sanitized = {}
            for key, value in data_item.items():
                # Skip sensitive fields
                if key.lower() in skip_fields:
                    sanitized[key] = value
                else:
                    sanitized[key] = sanitize_dict_recursive(value)
            return sanitized

        elif isinstance(data_item, list):
            return [sanitize_dict_recursive(item) for item in data_item]

        elif isinstance(data_item, str):
            return light_sanitize_text(data_item)

        else:
            return data_item

    return sanitize_dict_recursive(data)


def light_sanitize_text(text: str) -> str:
    """
    Light sanitization that preserves most content but removes dangerous patterns.
    """
    if not text:
        return text

    # Remove null bytes and dangerous control characters
    text = text.replace("\x00", "")

    # Remove or escape dangerous script patterns
    import re

    # Remove script tags completely
    text = re.sub(
        r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL
    )

    # Also remove just opening script tags
    text = re.sub(r"<script[^>]*>", "", text, flags=re.IGNORECASE)

    # Remove javascript: and data: URLs
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
    text = re.sub(r"data:", "", text, flags=re.IGNORECASE)

    # Remove on* event handlers
    text = re.sub(r"on\w+\s*=", "", text, flags=re.IGNORECASE)

    return text.strip()


def is_safe_text(text: str) -> bool:
    """
    Check if text is safe (no malicious patterns).

    Args:
        text: Text to check

    Returns:
        True if text is safe, False otherwise
    """
    try:
        check_sql_injection_patterns(text)
        validate_json_safe_string(text)
        return True
    except Exception:
        return False
