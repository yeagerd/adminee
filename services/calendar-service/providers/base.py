from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from ..models import (
    CalendarEventResponse,
)  # Assuming models.py is in the parent directory of providers/
from ..exceptions import (
    GraphClientError,
)  # Or a more generic ProviderError if we want to broaden


class CalendarProvider(ABC):
    """Abstract Base Class for calendar providers."""

    @abstractmethod
    async def get_events(
        self,
        token: str,
        user_timezone: str,
        start_datetime: datetime,  # Expected to be naive, representing local time in user_timezone
        end_datetime: datetime,  # Expected to be naive, representing local time in user_timezone
        top: int = 50,
    ) -> CalendarEventResponse:
        """
        Fetches calendar events from the provider.

        Args:
            token: The OAuth access token for the provider.
            user_timezone: The IANA timezone ID for interpreting start/end datetimes and for response event times.
            start_datetime: Naive datetime representing the start of the period in user_timezone.
            end_datetime: Naive datetime representing the end of the period in user_timezone.
            top: Maximum number of events to return.

        Returns:
            A CalendarEventResponse object containing the list of events.

        Raises:
            InvalidInputError: If input parameters are invalid.
            GraphClientError (or specific subtypes like GraphAPIAuthError, etc.): For errors during API interaction.
            (Consider a more generic ProviderError if this base needs to be less Graph-specific in its raised exceptions)
        """
        pass


# Example of a more generic error if needed:
# class ProviderError(Exception):
# """Base class for errors from calendar providers."""
# pass

# class ProviderAuthError(ProviderError):
# pass
