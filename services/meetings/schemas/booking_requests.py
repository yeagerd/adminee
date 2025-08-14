import re
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator, validator


# Base Models
class BusinessHoursConfig(BaseModel):
    start: str = Field(default="", description="Start time in HH:MM format")
    end: str = Field(default="", description="End time in HH:MM format")
    enabled: bool = Field(True, description="Whether this day is enabled for bookings")

    @validator("start", "end")
    def validate_time_format(cls: "BusinessHoursConfig", v: str) -> str:
        try:
            hour, minute = map(int, v.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            raise ValueError("Time must be in HH:MM format (00:00-23:59)")
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "BusinessHoursConfig":
        if self.enabled:
            start_time = datetime.strptime(self.start, "%H:%M").time()
            end_time = datetime.strptime(self.end, "%H:%M").time()
            if start_time >= end_time:
                raise ValueError("End time must be after start time")
        return self


class BookingSettings(BaseModel):
    duration: int = Field(30, ge=15, le=480, description="Meeting duration in minutes")
    buffer_before: int = Field(
        0, ge=0, le=120, description="Buffer before meeting in minutes"
    )
    buffer_after: int = Field(
        0, ge=0, le=120, description="Buffer after meeting in minutes"
    )
    max_per_day: int = Field(10, ge=1, le=50, description="Maximum meetings per day")
    max_per_week: int = Field(50, ge=1, le=200, description="Maximum meetings per week")
    advance_days: int = Field(
        1, ge=0, le=30, description="Minimum days in advance for booking"
    )
    max_advance_days: int = Field(
        90, ge=1, le=365, description="Maximum days in advance for booking"
    )
    last_minute_cutoff: int = Field(
        2, ge=0, le=24, description="Hours before meeting when booking closes"
    )
    business_hours: Dict[str, BusinessHoursConfig] = Field(
        default_factory=dict,
        description="Business hours configuration for each day of the week",
    )
    holiday_exclusions: List[str] = Field(
        default_factory=list, description="List of holiday dates in YYYY-MM-DD format"
    )

    @validator("max_advance_days")
    def validate_advance_window(cls: "BookingSettings", v: int, values: dict) -> int:
        if "advance_days" in values and v < values["advance_days"]:
            raise ValueError(
                "max_advance_days must be greater than or equal to advance_days"
            )
        return v

    @validator("holiday_exclusions")
    def validate_holiday_format(cls: "BookingSettings", v: List[str]) -> List[str]:
        for date_str in v:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError(
                    f"Invalid date format: {date_str}. Use YYYY-MM-DD format"
                )
        return v

    @model_validator(mode="after")
    def validate_buffer_limits(self) -> "BookingSettings":
        total_buffer = self.buffer_before + self.buffer_after
        if total_buffer >= self.duration:
            raise ValueError("Total buffer time must be less than meeting duration")
        return self


class QuestionField(BaseModel):
    id: str = Field(default="", description="Unique identifier for the question")
    label: str = Field(
        default="",
        min_length=1,
        max_length=200,
        description="Display label for the question",
    )
    required: bool = Field(False, description="Whether this question is required")
    type: str = Field(
        default="",
        description="Question type: text, email, textarea, select, phone, number",
    )
    options: Optional[List[str]] = Field(
        None, description="Options for select type questions"
    )
    placeholder: Optional[str] = Field(
        None, max_length=100, description="Placeholder text for the input"
    )
    validation: Optional[str] = Field(
        None, description="Validation rule (e.g., email, phone, url)"
    )

    @validator("id")
    def validate_id_format(cls: "QuestionField", v: str) -> str:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "ID must start with a letter and contain only alphanumeric characters, hyphens, and underscores"
            )
        return v

    @validator("type")
    def validate_question_type(cls: "QuestionField", v: str) -> str:
        valid_types = ["text", "email", "textarea", "select", "phone", "number", "url"]
        if v not in valid_types:
            raise ValueError(f'Question type must be one of: {", ".join(valid_types)}')
        return v

    @model_validator(mode="after")
    def validate_select_options(self) -> "QuestionField":
        if self.type == "select" and (not self.options or len(self.options) < 2):
            raise ValueError("Select questions must have at least 2 options")
        return self


# Request Models
class CreateBookingLinkRequest(BaseModel):
    title: str = Field(
        default="",
        min_length=1,
        max_length=100,
        description="Title for the booking link",
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Description of the booking link"
    )
    slug: Optional[str] = Field(
        None, max_length=64, description="Custom slug for the URL"
    )
    settings: BookingSettings = Field(
        default_factory=lambda: BookingSettings(
            duration=30,
            buffer_before=0,
            buffer_after=0,
            max_per_day=10,
            max_per_week=50,
            advance_days=1,
            max_advance_days=90,
            last_minute_cutoff=2,
        ),
        description="Booking configuration settings",
    )
    template_name: Optional[str] = Field(
        None, max_length=100, description="Name for the template"
    )
    questions: List[QuestionField] = Field(
        default_factory=list, description="Custom questions for recipients"
    )
    email_followup: bool = Field(False, description="Whether to send follow-up emails")

    @validator("slug")
    def validate_slug(
        cls: "CreateBookingLinkRequest", v: Optional[str]
    ) -> Optional[str]:
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9_-]+$", v):
                raise ValueError(
                    "Slug must contain only alphanumeric characters, hyphens, and underscores"
                )
            if len(v) < 3:
                raise ValueError("Slug must be at least 3 characters long")
        return v

    @validator("title")
    def validate_title(cls: "CreateBookingLinkRequest", v: str) -> str:
        # Check for potentially harmful content
        harmful_patterns = ["<script", "javascript:", "onclick", "onload"]
        for pattern in harmful_patterns:
            if pattern.lower() in v.lower():
                raise ValueError("Title contains potentially harmful content")
        return v

    @model_validator(mode="after")
    def validate_questions_limit(self) -> "CreateBookingLinkRequest":
        if len(self.questions) > 20:
            raise ValueError("Maximum 20 questions allowed per booking link")
        return self


class UpdateBookingLinkRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = Field(
        None, description="Partial settings update"
    )
    is_active: Optional[bool] = Field(None, description="Whether the link is active")

    @validator("title")
    def validate_title(
        cls: "UpdateBookingLinkRequest", v: Optional[str]
    ) -> Optional[str]:
        if v is not None:
            harmful_patterns = ["<script", "javascript:", "onclick", "onload"]
            for pattern in harmful_patterns:
                if pattern.lower() in v.lower():
                    raise ValueError("Title contains potentially harmful content")
        return v


class CreateOneTimeLinkRequest(BaseModel):
    recipient_email: EmailStr = Field(
        default="", description="Email address of the recipient"
    )
    recipient_name: str = Field(
        default="", min_length=1, max_length=100, description="Name of the recipient"
    )
    expires_in_days: int = Field(
        7, ge=1, le=365, description="Days until the link expires"
    )

    @validator("recipient_name")
    def validate_recipient_name(cls: "CreateOneTimeLinkRequest", v: str) -> str:
        harmful_patterns = ["<script", "javascript:", "onclick", "onload"]
        for pattern in harmful_patterns:
            if pattern.lower() in v.lower():
                raise ValueError("Recipient name contains potentially harmful content")
        return v


class CreatePublicBookingRequest(BaseModel):
    start: datetime = Field(
        default_factory=lambda: datetime.now(), description="Start time of the meeting"
    )
    end: datetime = Field(
        default_factory=lambda: datetime.now(), description="End time of the meeting"
    )
    attendee_email: EmailStr = Field(
        default="", description="Email address of the attendee"
    )
    answers: Dict[str, str] = Field(
        default_factory=dict, description="Answers to template questions"
    )

    @validator("start")
    def validate_start_time(cls: "CreatePublicBookingRequest", v: datetime) -> datetime:
        if v < datetime.now():
            raise ValueError("Start time cannot be in the past")
        return v

    @validator("end")
    def validate_end_after_start(
        cls: "CreatePublicBookingRequest", v: datetime, values: dict
    ) -> datetime:
        if "start" in values and v <= values["start"]:
            raise ValueError("End time must be after start time")
        return v

    @model_validator(mode="after")
    def validate_booking_window(self) -> "CreatePublicBookingRequest":
        # Ensure booking is not too far in the future (e.g., 2 years)
        max_future = datetime.now().replace(year=datetime.now().year + 2)
        if self.start > max_future:
            raise ValueError("Booking cannot be more than 2 years in the future")
        return self


class CreateTemplateRequest(BaseModel):
    name: str = Field(
        default="", min_length=1, max_length=100, description="Template name"
    )
    questions: List[QuestionField] = Field(
        default_factory=list, description="Questions for the template"
    )
    email_followup_enabled: bool = Field(
        False, description="Whether to enable follow-up emails"
    )

    @validator("name")
    def validate_template_name(cls: "CreateTemplateRequest", v: str) -> str:
        harmful_patterns = ["<script", "javascript:", "onclick", "onload"]
        for pattern in harmful_patterns:
            if pattern.lower() in v.lower():
                raise ValueError("Template name contains potentially harmful content")
        return v

    @model_validator(mode="after")
    def validate_questions_limit(self) -> "CreateTemplateRequest":
        if len(self.questions) > 20:
            raise ValueError("Maximum 20 questions allowed per template")
        return self


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    questions: Optional[List[QuestionField]] = Field(None)
    email_followup_enabled: Optional[bool] = Field(None)

    @validator("name")
    def validate_template_name(
        cls: "UpdateTemplateRequest", v: Optional[str]
    ) -> Optional[str]:
        if v is not None:
            harmful_patterns = ["<script", "javascript:", "onclick", "onload"]
            for pattern in harmful_patterns:
                if pattern.lower() in v.lower():
                    raise ValueError(
                        "Template name contains potentially harmful content"
                    )
        return v


# Response Models
class BookingLinkResponse(BaseModel):
    id: str
    owner_user_id: str
    slug: str
    is_active: bool
    settings: Dict[str, Any]
    template_id: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    total_views: int
    total_bookings: int
    conversion_rate: str

    model_config = ConfigDict(from_attributes=True)


class OneTimeLinkResponse(BaseModel):
    id: str
    recipient_email: str
    recipient_name: str
    token: str
    expires_at: Optional[str]
    status: str
    created_at: Optional[str]
    is_expired: bool
    public_url: str

    model_config = ConfigDict(from_attributes=True)


class BookingResponse(BaseModel):
    id: str
    link_id: str
    one_time_link_id: Optional[str]
    start_at: str
    end_at: str
    attendee_email: str
    answers: Optional[Dict[str, str]]
    calendar_event_id: Optional[str]
    created_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TemplateResponse(BaseModel):
    id: str
    name: str
    questions: List[QuestionField]
    email_followup_enabled: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    links_using_template: int

    model_config = ConfigDict(from_attributes=True)


class AnalyticsResponse(BaseModel):
    link_id: str
    views: int
    bookings: int
    conversion_rate: str
    last_viewed: Optional[str]
    top_referrers: List[str]
    recent_activity: List[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class PublicLinkResponse(BaseModel):
    title: str
    description: str
    template_questions: List[QuestionField]
    duration_options: List[int]
    is_active: bool


class AvailabilityResponse(BaseModel):
    slots: List[Dict[str, Any]]
    duration: int
    timezone: str


# Enhanced Error Response Models
class FieldError(BaseModel):
    field: str
    message: str
    code: Optional[str] = None
    value: Optional[Any] = None


class ErrorResponse(BaseModel):
    type: str = Field(
        default="", description="Error type (e.g., validation_error, not_found)"
    )
    message: str = Field(default="", description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error context"
    )
    field_errors: Optional[List[FieldError]] = Field(
        None, description="Field-specific validation errors"
    )
    timestamp: str = Field(
        default="", description="ISO timestamp of when the error occurred"
    )
    request_id: str = Field(
        default="", description="Unique request identifier for tracing"
    )


class SuccessResponse(BaseModel):
    data: Dict[str, Any]
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# List Response Models
class BookingLinksListResponse(BaseModel):
    data: List[BookingLinkResponse]
    total: int
    page: Optional[int] = None
    per_page: Optional[int] = None
    has_more: bool = False


class OneTimeLinksListResponse(BaseModel):
    data: List[OneTimeLinkResponse]
    total: int
    page: Optional[int] = None
    per_page: Optional[int] = None
    has_more: bool = False


class TemplatesListResponse(BaseModel):
    data: List[TemplateResponse]
    total: int
    page: Optional[int] = None
    per_page: Optional[int] = None
    has_more: bool = False


# Pagination and Filtering
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")


class BookingLinkFilters(BaseModel):
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    template_id: Optional[str] = Field(None, description="Filter by template")
    created_after: Optional[datetime] = Field(
        None, description="Filter by creation date"
    )
    created_before: Optional[datetime] = Field(
        None, description="Filter by creation date"
    )
    search: Optional[str] = Field(
        None, max_length=100, description="Search in title and description"
    )
