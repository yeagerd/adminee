"""
Base API client for external service integrations.

Provides common functionality for HTTP requests, error handling,
and authentication across different provider APIs.
"""

import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from services.common.http_errors import ErrorCode, ProviderError
from services.common.logging_config import get_logger
from services.office.models import ApiCall, ApiCallStatus, Provider

# Configure logging
logger = get_logger(__name__)


class BaseAPIClient(ABC):
    """
    Base API client class that provides common functionality for provider-specific clients.

    Features:
    - httpx.AsyncClient integration with proper configuration
    - Request/response logging and metrics collection
    - Authentication header management
    - Error handling and retry logic foundation
    - API call tracking for monitoring
    """

    def __init__(self, access_token: str, user_id: str, provider: Provider):
        """
        Initialize the base API client.

        Args:
            access_token: OAuth access token for the provider
            user_id: User ID for tracking and logging
            provider: Provider enum (google, microsoft)
        """
        self.access_token = access_token
        self.user_id = user_id
        self.provider = provider
        self.http_client: Optional[httpx.AsyncClient] = None

        # Request tracking
        self._session_id = str(uuid.uuid4())[:8]

    async def __aenter__(self) -> "BaseAPIClient":
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 30 second timeout for external APIs
            headers=self._get_default_headers(),
        )
        logger.info(f"Initialized {self.provider} API client for user {self.user_id}")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()
            logger.debug(f"Closed {self.provider} API client for user {self.user_id}")

    @abstractmethod
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _get_base_url(self) -> str:
        """Get base URL for the provider API. Must be implemented by subclasses."""
        pass

    def _generate_request_id(self) -> str:
        """Generate a unique request ID for tracking"""
        # Use nanosecond precision and counter for better uniqueness
        import random
        import time

        timestamp = str(int(time.time_ns()))[-8:]
        random_suffix = str(random.randint(1000, 9999))
        return f"{self._session_id}-{timestamp}-{random_suffix}"

    def _parse_microsoft_error(
        self, response_text: str, status_code: int
    ) -> tuple[str, ErrorCode]:
        """
        Parse Microsoft Graph API error responses to provide user-friendly messages.

        Args:
            response_text: Raw response body from Microsoft API
            status_code: HTTP status code

        Returns:
            Tuple of (user-friendly error message, provider-specific error code)
        """
        try:
            import json

            error_data = json.loads(response_text)
            error = error_data.get("error", {})

            error_code = error.get("code", "")
            error_message = error.get("message", "")

            # Parse specific Microsoft error codes
            if status_code == 401:
                if "InvalidAuthenticationToken" in error_code:
                    # Check for specific token issues
                    if (
                        "JWT is not well formed" in error_message
                        or "no dots" in error_message
                    ):
                        return (
                            "Authentication token is malformed or invalid. Please refresh your Microsoft token.",
                            ErrorCode.MICROSOFT_TOKEN_MALFORMED,
                        )
                    elif (
                        "Lifetime validation failed" in error_message
                        or "expired" in error_message.lower()
                    ):
                        return (
                            "Microsoft token has expired. Please refresh your authentication.",
                            ErrorCode.MICROSOFT_TOKEN_EXPIRED,
                        )
                    elif "NotBefore" in error_message or "nbf" in error_message:
                        return (
                            "Microsoft token is not yet valid. Please check your system time.",
                            ErrorCode.MICROSOFT_TOKEN_NOT_YET_VALID,
                        )
                    elif "Signature validation failed" in error_message:
                        return (
                            "Microsoft token signature is invalid. Please re-authenticate.",
                            ErrorCode.MICROSOFT_TOKEN_SIGNATURE_INVALID,
                        )
                    elif (
                        "audience" in error_message.lower()
                        and "invalid" in error_message.lower()
                    ):
                        return (
                            "Microsoft token audience is invalid. Please re-authenticate with correct permissions.",
                            ErrorCode.MICROSOFT_TOKEN_AUDIENCE_INVALID,
                        )
                    elif "issuer" in error_message.lower() and (
                        "invalid" in error_message.lower()
                        or "untrusted" in error_message.lower()
                    ):
                        return (
                            "Microsoft token issuer is invalid. Please re-authenticate.",
                            ErrorCode.MICROSOFT_TOKEN_ISSUER_INVALID,
                        )
                    else:
                        return (
                            f"Microsoft authentication failed: {error_message}",
                            ErrorCode.MICROSOFT_AUTH_FAILED,
                        )
                elif "TokenExpired" in error_code:
                    return (
                        "Microsoft token has expired. Please refresh your authentication.",
                        ErrorCode.MICROSOFT_TOKEN_EXPIRED,
                    )
                elif "Unauthorized" in error_code:
                    return (
                        "Access denied. Please check your Microsoft permissions.",
                        ErrorCode.MICROSOFT_UNAUTHORIZED,
                    )
                elif "TokenNotFound" in error_code:
                    return (
                        "Microsoft token not found. Please authenticate first.",
                        ErrorCode.MICROSOFT_TOKEN_NOT_FOUND,
                    )
                elif "CompactToken" in error_code:
                    return (
                        "Microsoft token format is invalid. Please refresh your token.",
                        ErrorCode.MICROSOFT_TOKEN_FORMAT_INVALID,
                    )
                else:
                    return (
                        f"Microsoft authentication error: {error_message}",
                        ErrorCode.MICROSOFT_AUTH_ERROR,
                    )
            elif status_code == 403:
                if "Forbidden" in error_code:
                    return (
                        "Access forbidden. Insufficient permissions for Microsoft resource.",
                        ErrorCode.MICROSOFT_ACCESS_FORBIDDEN,
                    )
                elif "InsufficientPermissions" in error_code:
                    return (
                        "Insufficient Microsoft permissions. Please grant additional scopes.",
                        ErrorCode.MICROSOFT_INSUFFICIENT_PERMISSIONS,
                    )
                elif "ApplicationPermissionsRequired" in error_code:
                    return (
                        "Application permissions required. Please configure app permissions in Azure.",
                        ErrorCode.MICROSOFT_APP_PERMISSIONS_REQUIRED,
                    )
                else:
                    return (
                        f"Microsoft access denied: {error_message}",
                        ErrorCode.MICROSOFT_ACCESS_DENIED,
                    )
            elif status_code == 429:
                return (
                    "Microsoft API rate limit exceeded. Please try again later.",
                    ErrorCode.MICROSOFT_RATE_LIMITED,
                )
            elif status_code >= 500:
                return (
                    f"Microsoft service error: {error_message}",
                    ErrorCode.MICROSOFT_SERVICE_ERROR,
                )
            else:
                return (
                    f"Microsoft API error ({error_code}): {error_message}",
                    ErrorCode.MICROSOFT_API_ERROR,
                )

        except (json.JSONDecodeError, KeyError):
            # Fall back to generic message if parsing fails
            if status_code == 401:
                return (
                    "Microsoft authentication failed. Please refresh your token.",
                    ErrorCode.MICROSOFT_AUTH_FAILED,
                )
            elif status_code == 403:
                return (
                    "Microsoft access denied. Please check your permissions.",
                    ErrorCode.MICROSOFT_ACCESS_DENIED,
                )
            elif status_code == 429:
                return (
                    "Microsoft API rate limit exceeded.",
                    ErrorCode.MICROSOFT_RATE_LIMITED,
                )
            else:
                return (
                    f"Microsoft API error (HTTP {status_code})",
                    ErrorCode.MICROSOFT_API_ERROR,
                )

    def _parse_google_error(
        self, response_text: str, status_code: int
    ) -> tuple[str, ErrorCode]:
        """
        Parse Google API error responses to provide user-friendly messages.

        Args:
            response_text: Raw response body from Google API
            status_code: HTTP status code

        Returns:
            Tuple of (user-friendly error message, provider-specific error code)
        """
        try:
            import json

            error_data = json.loads(response_text)

            # Google APIs have different error formats
            error = error_data.get("error", {})
            if isinstance(error, dict):
                error_code = error.get("code", "")
                error_message = error.get("message", "")
            else:
                # Some Google APIs return error as a string
                error_message = str(error)
                error_code = ""

            if status_code == 401:
                if (
                    "Invalid Credentials" in error_message
                    or "unauthorized" in error_message.lower()
                ):
                    return (
                        "Google authentication failed. Please refresh your Google token.",
                        ErrorCode.GOOGLE_AUTH_FAILED,
                    )
                elif "Token has been expired" in error_message:
                    return (
                        "Google token has expired. Please refresh your authentication.",
                        ErrorCode.GOOGLE_TOKEN_EXPIRED,
                    )
                elif "insufficient authentication scopes" in error_message.lower():
                    return (
                        "Insufficient Google permissions. Please re-authenticate with required scopes.",
                        ErrorCode.GOOGLE_INSUFFICIENT_SCOPES,
                    )
                else:
                    return (
                        f"Google authentication error: {error_message}",
                        ErrorCode.GOOGLE_AUTH_ERROR,
                    )
            elif status_code == 403:
                if (
                    "insufficientPermissions" in error_code
                    or "forbidden" in error_message.lower()
                ):
                    return (
                        "Insufficient Google permissions. Please grant additional access.",
                        ErrorCode.GOOGLE_INSUFFICIENT_PERMISSIONS,
                    )
                elif "quotaExceeded" in error_code:
                    return (
                        "Google API quota exceeded. Please try again later.",
                        ErrorCode.GOOGLE_QUOTA_EXCEEDED,
                    )
                else:
                    return (
                        f"Google access denied: {error_message}",
                        ErrorCode.GOOGLE_ACCESS_DENIED,
                    )
            elif status_code == 429:
                return (
                    "Google API rate limit exceeded. Please try again later.",
                    ErrorCode.GOOGLE_RATE_LIMITED,
                )
            elif status_code >= 500:
                return (
                    f"Google service error: {error_message}",
                    ErrorCode.GOOGLE_SERVICE_ERROR,
                )
            else:
                return f"Google API error: {error_message}", ErrorCode.GOOGLE_API_ERROR

        except (json.JSONDecodeError, KeyError):
            # Fall back to generic message if parsing fails
            if status_code == 401:
                return (
                    "Google authentication failed. Please refresh your token.",
                    ErrorCode.GOOGLE_AUTH_FAILED,
                )
            elif status_code == 403:
                return (
                    "Google access denied. Please check your permissions.",
                    ErrorCode.GOOGLE_ACCESS_DENIED,
                )
            elif status_code == 429:
                return "Google API rate limit exceeded.", ErrorCode.GOOGLE_RATE_LIMITED
            else:
                return (
                    f"Google API error (HTTP {status_code})",
                    ErrorCode.GOOGLE_API_ERROR,
                )

    async def _log_api_call(
        self,
        method: str,
        endpoint: str,
        status: ApiCallStatus,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Log API call for monitoring and analytics"""
        try:
            # Create database record (fire and forget)
            ApiCall(
                user_id=self.user_id,
                provider=self.provider,
                endpoint=endpoint,
                method=method.upper(),
                status=status,
                response_time_ms=response_time_ms,
                error_message=error_message,
                created_at=datetime.now(timezone.utc),
            )
            # Note: In a real implementation, you'd want to save this asynchronously
            # For now, we'll just log it
            logger.info(
                f"API Call: {method.upper()} {endpoint} | "
                f"Status: {status} | User: {self.user_id} | "
                f"Provider: {self.provider} | Time: {response_time_ms}ms"
            )
        except Exception as e:
            logger.error(f"Failed to log API call: {e}")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Make an HTTP request with logging and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON payload for POST/PUT requests
            headers: Additional headers
            **kwargs: Additional httpx request arguments

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPError: For HTTP errors
            Exception: For other request failures
        """
        if not self.http_client:
            raise RuntimeError(
                "HTTP client not initialized. Use async context manager."
            )

        # Prepare URL and headers
        url = f"{self._get_base_url()}{endpoint}"
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)

        # Propagate current request ID if present, otherwise generate a new one
        from services.common.logging_config import request_id_var

        context_request_id = request_id_var.get()
        if context_request_id and context_request_id != "uninitialized":
            request_id = context_request_id
        else:
            request_id = self._generate_request_id()
        request_headers["X-Request-ID"] = request_id

        # Start timing
        start_time = time.time()

        try:
            logger.debug(
                f"Making {method.upper()} request to {endpoint} | "
                f"User: {self.user_id} | Provider: {self.provider} | "
                f"Request-ID: {request_id}"
            )

            response = await self.http_client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers,
                **kwargs,
            )

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Log successful request
            logger.debug(
                f"Response: {response.status_code} | "
                f"Endpoint: {endpoint} | "
                f"Time: {response_time_ms}ms | "
                f"Request-ID: {request_id}"
            )

            # Track API call
            await self._log_api_call(
                method=method,
                endpoint=endpoint,
                status=ApiCallStatus.SUCCESS,
                response_time_ms=response_time_ms,
            )

            # Raise for HTTP errors
            response.raise_for_status()

            return response

        except httpx.TimeoutException:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Request timeout after {response_time_ms}ms"

            logger.error(
                f"Timeout error: {error_msg} | "
                f"Endpoint: {endpoint} | "
                f"Request-ID: {request_id} | "
                f"User: {self.user_id} | Provider: {self.provider}"
            )

            await self._log_api_call(
                method=method,
                endpoint=endpoint,
                status=ApiCallStatus.TIMEOUT,
                response_time_ms=response_time_ms,
                error_message=error_msg,
            )

            raise ProviderError(
                message=f"Request timeout: {error_msg}",
                provider=self.provider.value,
                details={
                    "endpoint": endpoint,
                    "method": method.upper(),
                    "timeout_ms": response_time_ms,
                    "request_id": request_id,
                },
            )

        except httpx.HTTPStatusError as e:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Parse provider-specific error messages and codes
            if self.provider == Provider.MICROSOFT:
                user_friendly_error, provider_code = self._parse_microsoft_error(
                    e.response.text, e.response.status_code
                )
            elif self.provider == Provider.GOOGLE:
                user_friendly_error, provider_code = self._parse_google_error(
                    e.response.text, e.response.status_code
                )
            else:
                user_friendly_error = (
                    f"HTTP {e.response.status_code}: {e.response.text}"
                )
                provider_code = ErrorCode.PROVIDER_ERROR

            # Determine status based on response code
            if e.response.status_code == 429:
                status = ApiCallStatus.RATE_LIMITED
            else:
                status = ApiCallStatus.ERROR

            logger.error(
                f"HTTP error: {user_friendly_error} | "
                f"Endpoint: {endpoint} | "
                f"Request-ID: {request_id} | "
                f"User: {self.user_id} | Provider: {self.provider}"
            )

            await self._log_api_call(
                method=method,
                endpoint=endpoint,
                status=status,
                response_time_ms=response_time_ms,
                error_message=user_friendly_error,
            )

            # Extract retry-after header for rate limiting
            retry_after = None
            if e.response.status_code == 429:
                retry_after_header = e.response.headers.get("Retry-After")
                if retry_after_header:
                    try:
                        retry_after = int(retry_after_header)
                    except ValueError:
                        pass

            raise ProviderError(
                message=user_friendly_error,
                provider=self.provider.value,
                status_code=e.response.status_code,
                response_body=e.response.text,
                retry_after=retry_after,
                code=provider_code,
                details={
                    "endpoint": endpoint,
                    "method": method.upper(),
                    "request_id": request_id,
                    "response_headers": dict(e.response.headers),
                },
            )

        except httpx.RequestError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Request error: {str(e)}"

            logger.error(
                f"Request error: {error_msg} | "
                f"Endpoint: {endpoint} | "
                f"Request-ID: {request_id} | "
                f"User: {self.user_id} | Provider: {self.provider}"
            )

            await self._log_api_call(
                method=method,
                endpoint=endpoint,
                status=ApiCallStatus.ERROR,
                response_time_ms=response_time_ms,
                error_message=error_msg,
            )

            raise ProviderError(
                message=f"Request failed: {error_msg}",
                provider=self.provider.value,
                details={
                    "endpoint": endpoint,
                    "method": method.upper(),
                    "request_id": request_id,
                    "error_type": type(e).__name__,
                },
            )

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Unexpected error: {str(e)}"

            logger.error(
                f"Unexpected error: {error_msg} | "
                f"Endpoint: {endpoint} | "
                f"Request-ID: {request_id} | "
                f"User: {self.user_id} | Provider: {self.provider}"
            )

            await self._log_api_call(
                method=method,
                endpoint=endpoint,
                status=ApiCallStatus.ERROR,
                response_time_ms=response_time_ms,
                error_message=error_msg,
            )

            raise ProviderError(
                message=f"Unexpected error: {error_msg}",
                provider=self.provider.value,
                details={
                    "endpoint": endpoint,
                    "method": method.upper(),
                    "request_id": request_id,
                    "error_type": type(e).__name__,
                },
            )

    # Convenience methods for common HTTP verbs
    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> httpx.Response:
        """Make a GET request"""
        return await self._make_request("GET", endpoint, params=params, **kwargs)

    async def post(
        self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> httpx.Response:
        """Make a POST request"""
        return await self._make_request("POST", endpoint, json_data=json_data, **kwargs)

    async def put(
        self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> httpx.Response:
        """Make a PUT request"""
        return await self._make_request("PUT", endpoint, json_data=json_data, **kwargs)

    async def delete(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Make a DELETE request"""
        return await self._make_request("DELETE", endpoint, **kwargs)

    async def patch(
        self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> httpx.Response:
        """Make a PATCH request"""
        return await self._make_request(
            "PATCH", endpoint, json_data=json_data, **kwargs
        )
