"""Custom exceptions for the Calendar Service."""


class GraphClientError(Exception):
    """Base class for errors originating from the Microsoft Graph client."""

    def __init__(
        self, message: str, status_code: int = None, graph_error_details: dict = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.graph_error_details = graph_error_details


class InvalidInputError(ValueError):
    """Raised when input provided to a function is invalid (e.g., bad date range, invalid timezone string)."""

    pass


class GraphAPIAuthError(GraphClientError):
    """Raised for authentication/authorization errors (401, 403) with Microsoft Graph."""

    pass


class GraphAPIRateLimitError(GraphClientError):
    """Raised for rate limiting errors (429) from Microsoft Graph."""

    pass


class GraphAPIClientError(GraphClientError):
    """Raised for other client-side errors (4xx, excluding 401, 403, 429) from Microsoft Graph."""

    pass


class GraphAPIServerError(GraphClientError):
    """Raised for server-side errors (5xx) from Microsoft Graph."""

    pass


class GraphAPIDecodingError(GraphClientError):
    """Raised when there's an issue decoding the JSON response from Microsoft Graph."""

    pass
