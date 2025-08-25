"""
Pydantic schemas for user preferences management.

This module defines request and response models for user preferences,
including UI settings, notification preferences, AI configuration,
integration settings, and privacy controls.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThemeMode(str, Enum):
    """Theme mode options."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class Language(str, Enum):
    """Supported languages."""

    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    PT = "pt"
    JA = "ja"
    KO = "ko"
    ZH = "zh"


class Timezone(str, Enum):
    """Common timezone options."""

    UTC = "UTC"
    US_EASTERN = "America/New_York"
    US_CENTRAL = "America/Chicago"
    US_MOUNTAIN = "America/Denver"
    US_PACIFIC = "America/Los_Angeles"
    EUROPE_LONDON = "Europe/London"
    EUROPE_PARIS = "Europe/Paris"
    EUROPE_BERLIN = "Europe/Berlin"
    ASIA_TOKYO = "Asia/Tokyo"
    ASIA_SEOUL = "Asia/Seoul"
    ASIA_SHANGHAI = "Asia/Shanghai"
    AUSTRALIA_SYDNEY = "Australia/Sydney"


class DateFormat(str, Enum):
    """Date format options."""

    US = "MM/DD/YYYY"
    EUROPEAN = "DD/MM/YYYY"
    ISO = "YYYY-MM-DD"


class TimeFormat(str, Enum):
    """Time format options."""

    TWELVE_HOUR = "12h"
    TWENTY_FOUR_HOUR = "24h"


class NotificationFrequency(str, Enum):
    """Notification frequency options."""

    IMMEDIATE = "immediate"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


class AIModelProvider(str, Enum):
    """AI model provider options."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"


class AIModelType(str, Enum):
    """AI model type options."""

    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    GEMINI_PRO = "gemini-pro"
    GEMINI_ULTRA = "gemini-ultra"


class AIPreferencesSchema(BaseModel):
    """AI preferences schema."""

    preferred_provider: AIModelProvider = Field(
        default=AIModelProvider.OPENAI, description="Preferred AI provider"
    )
    preferred_model: AIModelType = Field(
        default=AIModelType.GPT_4, description="Preferred AI model"
    )

    # Response settings
    response_style: str = Field(
        default="balanced", description="AI response style preference"
    )
    response_length: str = Field(
        default="medium", description="Preferred response length"
    )

    # Feature toggles
    auto_summarization: bool = Field(
        default=True, description="Enable automatic summarization"
    )
    smart_suggestions: bool = Field(
        default=True, description="Enable smart suggestions"
    )
    context_awareness: bool = Field(
        default=True, description="Enable context-aware responses"
    )

    # Advanced settings
    temperature: float = Field(
        default=0.7, ge=0.0, le=1.0, description="AI creativity/randomness level"
    )
    max_tokens: int = Field(
        default=2000, ge=100, le=8000, description="Maximum tokens per response"
    )

    @field_validator("response_style")
    @classmethod
    def validate_response_style(cls, v: str) -> str:
        """Enhanced response style validation."""
        # Sanitize the input
        v = v.strip()
        if not v:
            raise ValueError("Response style cannot be empty")

        # Use enum validation
        valid_styles = ["concise", "balanced", "detailed", "creative", "technical"]
        if v not in valid_styles:
            raise ValueError(f"Invalid response style. Must be one of: {valid_styles}")
        return v

    @field_validator("response_length")
    @classmethod
    def validate_response_length(cls, v: str) -> str:
        """Enhanced response length validation."""
        # Sanitize the input
        v = v.strip()
        if not v:
            raise ValueError("Response length cannot be empty")

        # Use enum validation
        valid_lengths = ["short", "medium", "long"]
        if v not in valid_lengths:
            raise ValueError(f"Invalid response length. Must be one of: {valid_lengths}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "preferred_provider": "openai",
                "preferred_model": "gpt-4",
                "response_style": "balanced",
                "response_length": "medium",
                "auto_summarization": True,
                "smart_suggestions": True,
                "context_awareness": True,
                "temperature": 0.7,
                "max_tokens": 2000,
            }
        }
    )


class IntegrationPreferencesSchema(BaseModel):
    """Integration preferences schema."""

    auto_sync: bool = Field(
        default=True, description="Enable automatic synchronization"
    )
    sync_frequency: int = Field(
        default=30, ge=5, le=1440, description="Sync frequency in minutes"
    )

    # Provider-specific settings
    google_drive_enabled: bool = Field(
        default=False, description="Enable Google Drive integration"
    )
    microsoft_365_enabled: bool = Field(
        default=False, description="Enable Microsoft 365 integration"
    )
    dropbox_enabled: bool = Field(
        default=False, description="Enable Dropbox integration"
    )

    # Sync settings
    sync_document_content: bool = Field(
        default=True, description="Sync document content"
    )
    sync_metadata: bool = Field(default=True, description="Sync file metadata")
    sync_permissions: bool = Field(default=False, description="Sync file permissions")

    # Conflict resolution
    conflict_resolution: str = Field(
        default="prompt", description="How to handle sync conflicts"
    )

    @field_validator("conflict_resolution")
    @classmethod
    def validate_conflict_resolution(cls, v: str) -> str:
        """Enhanced conflict resolution strategy validation."""
        # Sanitize the input
        v = v.strip()
        if not v:
            raise ValueError("Conflict resolution cannot be empty")

        # Use enum validation
        valid_strategies = ["prompt", "local_wins", "remote_wins", "create_copy"]
        if v not in valid_strategies:
            raise ValueError(f"Invalid conflict resolution. Must be one of: {valid_strategies}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "auto_sync": True,
                "sync_frequency": 30,
                "google_drive_enabled": True,
                "microsoft_365_enabled": False,
                "dropbox_enabled": False,
                "sync_document_content": True,
                "sync_metadata": True,
                "sync_permissions": False,
                "conflict_resolution": "prompt",
            }
        }
    )


class UIPreferencesSchema(BaseModel):
    """UI preferences schema."""

    theme: ThemeMode = Field(
        default=ThemeMode.SYSTEM, description="Theme preference"
    )
    language: Language = Field(
        default=Language.EN, description="Language preference"
    )
    timezone: Timezone = Field(
        default=Timezone.UTC, description="Timezone preference"
    )
    date_format: DateFormat = Field(
        default=DateFormat.ISO, description="Date format preference"
    )
    time_format: TimeFormat = Field(
        default=TimeFormat.TWENTY_FOUR_HOUR, description="Time format preference"
    )

    # Layout preferences
    sidebar_collapsed: bool = Field(
        default=False, description="Whether sidebar is collapsed"
    )
    compact_mode: bool = Field(
        default=False, description="Enable compact layout mode"
    )
    show_animations: bool = Field(
        default=True, description="Show UI animations"
    )

    # Accessibility
    high_contrast: bool = Field(
        default=False, description="Enable high contrast mode"
    )
    font_size: str = Field(
        default="medium", description="Font size preference"
    )
    reduce_motion: bool = Field(
        default=False, description="Reduce motion for accessibility"
    )

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesSchema(BaseModel):
    """Notification preferences schema."""

    email_notifications: bool = Field(
        default=True, description="Enable email notifications"
    )
    push_notifications: bool = Field(
        default=True, description="Enable push notifications"
    )
    sms_notifications: bool = Field(
        default=False, description="Enable SMS notifications"
    )

    # Frequency settings
    notification_frequency: NotificationFrequency = Field(
        default=NotificationFrequency.IMMEDIATE, description="Notification frequency"
    )
    quiet_hours_start: Optional[str] = Field(
        None, description="Quiet hours start time (HH:MM)"
    )
    quiet_hours_end: Optional[str] = Field(
        None, description="Quiet hours end time (HH:MM)"
    )

    # Type-specific settings
    meeting_reminders: bool = Field(
        default=True, description="Meeting reminder notifications"
    )
    email_alerts: bool = Field(
        default=True, description="Email alert notifications"
    )
    system_updates: bool = Field(
        default=True, description="System update notifications"
    )

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate time format."""
        if v is None:
            return v

        try:
            # Validate HH:MM format
            hour, minute = map(int, v.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time values")
            return v
        except (ValueError, AttributeError):
            raise ValueError("Time must be in HH:MM format")

    model_config = ConfigDict(from_attributes=True)


class PrivacyPreferencesSchema(BaseModel):
    """Privacy preferences schema."""

    data_collection: bool = Field(
        default=True, description="Allow data collection for analytics"
    )
    personalized_ads: bool = Field(
        default=False, description="Allow personalized advertisements"
    )
    third_party_sharing: bool = Field(
        default=False, description="Allow third-party data sharing"
    )

    # Data retention
    data_retention_days: int = Field(
        default=365, ge=30, le=2555, description="Data retention period in days"
    )
    auto_delete_old_data: bool = Field(
        default=True, description="Automatically delete old data"
    )

    # Privacy controls
    profile_visibility: str = Field(
        default="private", description="Profile visibility level"
    )
    search_indexing: bool = Field(
        default=False, description="Allow search engine indexing"
    )

    model_config = ConfigDict(from_attributes=True)


class PreferencesResetRequest(BaseModel):
    """Request model for resetting user preferences to defaults."""

    reset_all: bool = Field(
        default=True, description="Reset all preferences to defaults"
    )
    categories: Optional[List[str]] = Field(
        None, description="Specific preference categories to reset"
    )
    confirm_reset: bool = Field(
        ..., description="User must confirm the reset operation"
    )

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate preference categories."""
        if v is not None:
            valid_categories = ["ui", "notifications", "ai", "integrations", "privacy"]
            for category in v:
                if category not in valid_categories:
                    raise ValueError(f"Invalid category: {category}. Must be one of: {valid_categories}")
        return v


class PreferencesImportRequest(BaseModel):
    """Request model for importing user preferences from external source."""

    preferences_data: Dict[str, Any] = Field(..., description="Preferences data to import")
    source: str = Field(..., description="Source of the preferences data")
    overwrite_existing: bool = Field(
        default=False, description="Whether to overwrite existing preferences"
    )
    validate_only: bool = Field(
        default=False, description="Only validate the data without importing"
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate import source."""
        valid_sources = ["backup", "migration", "sync", "manual"]
        if v not in valid_sources:
            raise ValueError(f"Invalid source: {v}. Must be one of: {valid_sources}")
        return v


class UserPreferences(BaseModel):
    """Complete user preferences model."""

    id: int = Field(..., description="Preferences ID")
    user_id: str = Field(..., description="User ID")

    # Preference categories
    ui: UIPreferencesSchema = Field(description="UI preferences")
    notifications: NotificationPreferencesSchema = Field(description="Notification preferences")
    ai: AIPreferencesSchema = Field(description="AI preferences")
    integrations: IntegrationPreferencesSchema = Field(description="Integration preferences")
    privacy: PrivacyPreferencesSchema = Field(description="Privacy preferences")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserPreferencesUpdate(BaseModel):
    """Request model for updating user preferences."""

    ui: Optional[UIPreferencesSchema] = Field(
        None, description="UI preferences to update"
    )
    notifications: Optional[NotificationPreferencesSchema] = Field(
        None, description="Notification preferences to update"
    )
    ai: Optional[AIPreferencesSchema] = Field(
        None, description="AI preferences to update"
    )
    integrations: Optional[IntegrationPreferencesSchema] = Field(
        None, description="Integration preferences to update"
    )
    privacy: Optional[PrivacyPreferencesSchema] = Field(
        None, description="Privacy preferences to update"
    )

    model_config = ConfigDict(from_attributes=True)


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""

    success: bool = Field(..., description="Whether operation was successful")
    preferences: Optional[UserPreferences] = Field(
        None, description="User preferences data"
    )
    message: Optional[str] = Field(None, description="Response message")
    error: Optional[str] = Field(None, description="Error message if failed")

    model_config = ConfigDict(from_attributes=True)
