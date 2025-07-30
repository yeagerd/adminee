"""
Pydantic models for validating office service responses in the chat service.

These models ensure type safety and catch data structure issues early.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from services.office.schemas import CalendarEvent


class OfficeServiceCalendarResponse(BaseModel):
    """Model for office service calendar events response."""

    success: bool
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[str] = None
    request_id: str
    data: Union[List[CalendarEvent], Dict[str, Any]] = Field(
        description="Events data - can be direct list or nested dict with events field"
    )

    @field_validator("data")
    @classmethod
    def validate_data_structure(
        cls, v: Union[List[CalendarEvent], Dict[str, Any]]
    ) -> Union[List[CalendarEvent], Dict[str, Any]]:
        """Validate that data is either a list of events or a dict with events field."""
        if isinstance(v, list):
            # Direct array format - validate each item is a CalendarEvent
            for item in v:
                if not isinstance(item, CalendarEvent):
                    raise ValueError(f"Expected CalendarEvent, got {type(item)}")
            return v
        elif isinstance(v, dict):
            # Nested format - check if it has events field
            if "events" not in v:
                raise ValueError("Dict format must contain 'events' field")
            events = v["events"]
            if not isinstance(events, list):
                raise ValueError("Events field must be a list")
            for item in events:
                if not isinstance(item, CalendarEvent):
                    raise ValueError(
                        f"Expected CalendarEvent in events list, got {type(item)}"
                    )
            return v
        else:
            raise ValueError(f"Data must be list or dict, got {type(v)}")

    def get_events(self) -> List[CalendarEvent]:
        """Extract events list regardless of format."""
        if isinstance(self.data, list):
            return self.data
        elif isinstance(self.data, dict) and "events" in self.data:
            return self.data["events"]
        else:
            raise ValueError("No events found in response data")

    def get_provider_errors(self) -> Optional[Dict[str, str]]:
        """Extract provider errors if available."""
        if isinstance(self.data, dict):
            return self.data.get("provider_errors")
        return None

    def get_providers_used(self) -> Optional[List[str]]:
        """Extract providers used if available."""
        if isinstance(self.data, dict):
            return self.data.get("providers_used")
        return None


class OfficeServiceErrorResponse(BaseModel):
    """Model for office service error responses."""

    success: bool = False
    error: Dict[str, Any]
    request_id: str


class CalendarToolResponse(BaseModel):
    """Model for calendar tool responses returned to LLM agents."""

    events: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

    @field_validator("events", mode="before")
    @classmethod
    def validate_events(cls, v: Any) -> Optional[List[Dict[str, Any]]]:
        """Validate events list."""
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError(f"Events must be a list, got {type(v)}")
        return v

    @field_validator("error", mode="before")
    @classmethod
    def validate_error(cls, v: Any) -> Optional[str]:
        """Validate error message."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError(f"Error must be a string, got {type(v)}")
        return v

    def has_error(self) -> bool:
        """Check if response contains an error."""
        return self.error is not None

    def get_event_count(self) -> int:
        """Get number of events."""
        return len(self.events) if self.events else 0
