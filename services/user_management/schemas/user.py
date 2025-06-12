"""
Pydantic schemas for user profile operations.

Defines request and response models for user CRUD operations
with comprehensive validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from services.user_management.utils.validation import (
    check_sql_injection_patterns,
    sanitize_text_input,
    validate_email_address,
    validate_url,
    validate_json_safe_string,
)


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(..., description="User's email address")
    first_name: Optional[str] = Field(
        None, max_length=100, description="User's first name"
    )
    last_name: Optional[str] = Field(
        None, max_length=100, description="User's last name"
    )
    profile_image_url: Optional[str] = Field(
        None, description="URL to user's profile image"
    )

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def validate_names(cls, v):
        """Validate and sanitize name fields."""
        if v is None:
            return v

        # Check for SQL injection patterns
        check_sql_injection_patterns(str(v), "name")

        # Sanitize the input
        sanitized = sanitize_text_input(str(v), max_length=100)

        return sanitized

    @field_validator("profile_image_url")
    @classmethod
    def validate_profile_image_url(cls, v):
        """Validate profile image URL format."""
        if v is None:
            return v

        # Use comprehensive URL validation
        return validate_url(v, allowed_schemes=["http", "https"])

    @field_validator("email")
    @classmethod
    def validate_email_enhanced(cls, v):
        """Enhanced email validation with security checks."""
        if v is None:
            return v

        # Use comprehensive email validation
        return validate_email_address(v)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    external_auth_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="External authentication provider user ID",
    )
    auth_provider: str = Field(
        default="clerk", max_length=50, description="Authentication provider name"
    )

    @field_validator("external_auth_id")
    @classmethod
    def validate_external_auth_id(cls, v):
        """Validate external auth ID format."""
        if not v or not v.strip():
            raise ValueError("External auth ID cannot be empty")

        v = v.strip()

        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "external_auth_id")

        return v

    @field_validator("auth_provider")
    @classmethod
    def validate_auth_provider(cls, v):
        """Validate auth provider format."""
        if not v or not v.strip():
            raise ValueError("Auth provider cannot be empty")

        v = v.strip().lower()

        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "auth_provider")

        valid_providers = ["clerk", "custom", "auth0", "firebase", "supabase"]
        if v not in valid_providers:
            raise ValueError(
                f"Invalid auth provider. Must be one of: {', '.join(valid_providers)}"
            )

        return v


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    email: Optional[EmailStr] = Field(None, description="User's email address")
    first_name: Optional[str] = Field(
        None, max_length=100, description="User's first name"
    )
    last_name: Optional[str] = Field(
        None, max_length=100, description="User's last name"
    )
    profile_image_url: Optional[str] = Field(
        None, description="URL to user's profile image"
    )

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def validate_names(cls, v):
        """Validate and sanitize name fields."""
        if v is None:
            return v

        # Check for SQL injection patterns
        check_sql_injection_patterns(str(v), "name")

        # Sanitize the input
        sanitized = sanitize_text_input(str(v), max_length=100)

        return sanitized

    @field_validator("profile_image_url")
    @classmethod
    def validate_profile_image_url(cls, v):
        """Validate profile image URL format."""
        if v is None:
            return v

        # Use comprehensive URL validation
        return validate_url(v, allowed_schemes=["http", "https"])

    @field_validator("email")
    @classmethod
    def validate_email_enhanced(cls, v):
        """Enhanced email validation with security checks."""
        if v is None:
            return v

        # Use comprehensive email validation
        return validate_email_address(v)

    class Config:
        """Pydantic config for update schema."""

        # Allow partial updates - all fields are optional
        exclude_none = True


class UserResponse(UserBase):
    """Schema for user response data."""

    id: int = Field(..., description="User's internal database ID (primary key)")
    external_auth_id: str = Field(
        ..., description="External authentication provider user ID"
    )
    auth_provider: str = Field(..., description="Authentication provider name")
    onboarding_completed: bool = Field(
        ..., description="Whether user has completed onboarding"
    )
    onboarding_step: Optional[str] = Field(
        None, description="Current onboarding step if not completed"
    )
    created_at: datetime = Field(..., description="When the user was created")
    updated_at: datetime = Field(..., description="When the user was last updated")

    class Config:
        """Pydantic config for response schema."""

        from_attributes = True  # Enable ORM mode for Ormar models
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class UserListResponse(BaseModel):
    """Schema for paginated user list responses."""

    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of users per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class UserDeleteResponse(BaseModel):
    """Schema for user deletion response."""

    success: bool = Field(..., description="Whether the deletion was successful")
    message: str = Field(..., description="Deletion status message")
    user_id: int = Field(..., description="Internal database ID of the deleted user")
    external_auth_id: str = Field(
        ..., description="External auth ID of the deleted user"
    )
    deleted_at: datetime = Field(..., description="When the user was deleted")

    class Config:
        """Pydantic config for delete response schema."""

        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class UserOnboardingUpdate(BaseModel):
    """Schema for updating user onboarding status."""

    onboarding_completed: bool = Field(
        ..., description="Whether onboarding is completed"
    )
    onboarding_step: Optional[str] = Field(None, description="Current onboarding step")

    @field_validator("onboarding_step")
    @classmethod
    def validate_onboarding_step(cls, v):
        """Validate onboarding step format."""
        if v is None:
            return v

        # Check for SQL injection patterns
        check_sql_injection_patterns(str(v), "onboarding_step")

        # Sanitize the input
        v = sanitize_text_input(str(v), max_length=50)

        if v is not None:
            valid_steps = [
                "profile_setup",
                "preferences_setup",
                "integration_setup",
                "welcome_tour",
            ]
            if v not in valid_steps:
                raise ValueError(
                    f'Invalid onboarding step. Must be one of: {", ".join(valid_steps)}'
                )

        return v

    @model_validator(mode="after")
    def validate_onboarding_consistency(self):
        """Validate onboarding step consistency."""
        if self.onboarding_completed and self.onboarding_step is not None:
            raise ValueError(
                "Onboarding step should be None when onboarding is completed"
            )

        if not self.onboarding_completed and self.onboarding_step is None:
            raise ValueError(
                "Onboarding step is required when onboarding is not completed"
            )

        return self


class UserSearchRequest(BaseModel):
    """Schema for user search requests."""

    query: Optional[str] = Field(None, max_length=255, description="Search query")
    email: Optional[EmailStr] = Field(None, description="Filter by email")
    onboarding_completed: Optional[bool] = Field(
        None, description="Filter by onboarding status"
    )
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Number of results per page")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        """Validate and sanitize search query."""
        if v is None:
            return v

        # Check for SQL injection patterns
        check_sql_injection_patterns(str(v), "search_query")

        # Sanitize the input
        sanitized = sanitize_text_input(str(v), max_length=255)

        return sanitized

    @field_validator("email")
    @classmethod
    def validate_email_search(cls, v):
        """Enhanced email validation for search."""
        if v is None:
            return v

        # Use comprehensive email validation
        return validate_email_address(v)
