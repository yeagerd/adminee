"""
Pydantic schemas for user profile operations.

Defines request and response models for user CRUD operations
with comprehensive validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


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

    @validator("first_name", "last_name", pre=True)
    def validate_names(cls, v):
        """Validate and sanitize name fields."""
        if v is not None:
            v = v.strip()
            if not v:  # Empty string after strip
                return None
            # Remove any HTML tags or special characters for security
            import re

            v = re.sub(r"<[^>]*>", "", v)  # Remove HTML tags
            v = re.sub(r'[<>"\']', "", v)  # Remove potentially dangerous characters
        return v

    @validator("profile_image_url")
    def validate_profile_image_url(cls, v):
        """Validate profile image URL format."""
        if v is not None:
            import re

            url_pattern = re.compile(
                r"^https?://"  # http:// or https://
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
                r"localhost|"  # localhost...
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
                r"(?::\d+)?"  # optional port
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )
            if not url_pattern.match(v):
                raise ValueError("Invalid URL format for profile image")
        return v


class UserCreate(UserBase):
    """Schema for creating a new user."""

    clerk_id: str = Field(
        ..., min_length=1, max_length=255, description="Clerk user ID"
    )

    @validator("clerk_id")
    def validate_clerk_id(cls, v):
        """Validate Clerk ID format."""
        if not v or not v.strip():
            raise ValueError("Clerk ID cannot be empty")
        # Clerk IDs typically start with 'user_' followed by alphanumeric characters
        import re

        if not re.match(r"^user_[a-zA-Z0-9]+$", v.strip()):
            raise ValueError("Invalid Clerk ID format")
        return v.strip()


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

    @validator("first_name", "last_name", pre=True)
    def validate_names(cls, v):
        """Validate and sanitize name fields."""
        if v is not None:
            v = v.strip()
            if not v:  # Empty string after strip
                return None
            # Remove any HTML tags or special characters for security
            import re

            v = re.sub(r"<[^>]*>", "", v)  # Remove HTML tags
            v = re.sub(r'[<>"\']', "", v)  # Remove potentially dangerous characters
        return v

    @validator("profile_image_url")
    def validate_profile_image_url(cls, v):
        """Validate profile image URL format."""
        if v is not None:
            import re

            url_pattern = re.compile(
                r"^https?://"  # http:// or https://
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
                r"localhost|"  # localhost...
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
                r"(?::\d+)?"  # optional port
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )
            if not url_pattern.match(v):
                raise ValueError("Invalid URL format for profile image")
        return v

    class Config:
        """Pydantic config for update schema."""

        # Allow partial updates - all fields are optional
        exclude_none = True


class UserResponse(UserBase):
    """Schema for user response data."""

    id: int = Field(..., description="User's database ID")
    clerk_id: str = Field(..., description="Clerk user ID")
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
    user_id: int = Field(..., description="ID of the deleted user")
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

    @validator("onboarding_step")
    def validate_onboarding_step(cls, v, values):
        """Validate onboarding step based on completion status."""
        if values.get("onboarding_completed") and v is not None:
            raise ValueError(
                "Onboarding step should be None when onboarding is completed"
            )

        if not values.get("onboarding_completed") and v is None:
            raise ValueError(
                "Onboarding step is required when onboarding is not completed"
            )

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


class UserSearchRequest(BaseModel):
    """Schema for user search requests."""

    query: Optional[str] = Field(None, max_length=255, description="Search query")
    email: Optional[EmailStr] = Field(None, description="Filter by email")
    onboarding_completed: Optional[bool] = Field(
        None, description="Filter by onboarding status"
    )
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Number of results per page")

    @validator("query")
    def validate_query(cls, v):
        """Validate and sanitize search query."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # Basic sanitization to prevent injection attacks
            import re

            v = re.sub(r'[<>"\';]', "", v)  # Remove potentially dangerous characters
        return v
