"""
Pydantic schemas for user preferences management.

This module defines request and response models for user preferences,
including UI settings, notification preferences, AI configuration,
integration settings, and privacy controls.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.user.utils.validation import (
    check_sql_injection_patterns,
    sanitize_text_input,
    validate_enum_value,
    validate_time_format,
)


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


class DataRetentionPeriod(str, Enum):
    """Data retention period options."""

    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    DAYS_180 = "180_days"
    YEAR_1 = "1_year"
    YEARS_2 = "2_years"
    INDEFINITE = "indefinite"


# UI Preferences Schema
class UIPreferencesSchema(BaseModel):
    """UI preferences schema."""

    theme: ThemeMode = Field(
        default=ThemeMode.SYSTEM, description="Theme mode preference"
    )
    language: Language = Field(default=Language.EN, description="Display language")
    # timezone: Timezone = Field(default=Timezone.UTC, description="User timezone")  # DEPRECATED: use top-level timezone_mode/manual_timezone
    date_format: DateFormat = Field(
        default=DateFormat.US, description="Date format preference"
    )
    time_format: TimeFormat = Field(
        default=TimeFormat.TWELVE_HOUR, description="Time format preference"
    )
    compact_mode: bool = Field(default=False, description="Use compact UI layout")
    show_tooltips: bool = Field(default=True, description="Show helpful tooltips")
    animations_enabled: bool = Field(default=True, description="Enable UI animations")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "theme": "dark",
                "language": "en",
                # "timezone": "America/New_York",  # DEPRECATED
                "date_format": "MM/DD/YYYY",
                "time_format": "12h",
                "compact_mode": False,
                "show_tooltips": True,
                "animations_enabled": True,
            }
        }
    )


# Notification Preferences Schema
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
    summary_frequency: NotificationFrequency = Field(
        default=NotificationFrequency.DAILY,
        description="Frequency for summary notifications",
    )
    activity_frequency: NotificationFrequency = Field(
        default=NotificationFrequency.IMMEDIATE,
        description="Frequency for activity notifications",
    )

    # Specific notification types
    document_updates: bool = Field(
        default=True, description="Notify on document updates"
    )
    system_updates: bool = Field(default=True, description="Notify on system updates")
    security_alerts: bool = Field(default=True, description="Notify on security alerts")
    integration_status: bool = Field(
        default=True, description="Notify on integration status changes"
    )

    # Quiet hours
    quiet_hours_enabled: bool = Field(default=False, description="Enable quiet hours")
    quiet_hours_start: str = Field(
        default="22:00", description="Quiet hours start time (HH:MM)"
    )
    quiet_hours_end: str = Field(
        default="08:00", description="Quiet hours end time (HH:MM)"
    )

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_time_format_enhanced(cls, v: str) -> str:
        """Enhanced time format validation."""
        if not v:
            return v

        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "time")

        # Use comprehensive time validation
        return validate_time_format(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email_notifications": True,
                "push_notifications": True,
                "sms_notifications": False,
                "summary_frequency": "daily",
                "activity_frequency": "immediate",
                "document_updates": True,
                "system_updates": True,
                "security_alerts": True,
                "integration_status": True,
                "quiet_hours_enabled": True,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00",
            }
        }
    )


# AI Preferences Schema
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
        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "response_style")

        # Sanitize the input
        sanitized = sanitize_text_input(v, max_length=50)
        if sanitized is None:
            raise ValueError("Value cannot be empty after sanitization")

        # Use enum validation
        valid_styles = ["concise", "balanced", "detailed", "creative", "technical"]
        return validate_enum_value(sanitized, valid_styles, "response_style")

    @field_validator("response_length")
    @classmethod
    def validate_response_length(cls, v: str) -> str:
        """Enhanced response length validation."""
        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "response_length")

        # Sanitize the input
        sanitized = sanitize_text_input(v, max_length=50)
        if sanitized is None:
            raise ValueError("Value cannot be empty after sanitization")

        # Use enum validation
        valid_lengths = ["short", "medium", "long"]
        return validate_enum_value(sanitized, valid_lengths, "response_length")

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


# Integration Preferences Schema
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
        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "conflict_resolution")

        # Sanitize the input
        sanitized = sanitize_text_input(v, max_length=50)
        if sanitized is None:
            raise ValueError("Value cannot be empty after sanitization")

        # Use enum validation
        valid_strategies = ["prompt", "local_wins", "remote_wins", "create_copy"]
        return validate_enum_value(sanitized, valid_strategies, "conflict_resolution")

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


# Privacy Preferences Schema
class PrivacyPreferencesSchema(BaseModel):
    """Privacy preferences schema."""

    data_collection: bool = Field(
        default=True, description="Allow data collection for improvements"
    )
    analytics: bool = Field(default=True, description="Allow analytics tracking")
    personalization: bool = Field(
        default=True, description="Allow personalization based on usage"
    )

    # Data retention
    data_retention_period: DataRetentionPeriod = Field(
        default=DataRetentionPeriod.YEAR_1, description="Data retention period"
    )

    # Sharing settings
    share_anonymous_usage: bool = Field(
        default=False, description="Share anonymous usage statistics"
    )
    marketing_communications: bool = Field(
        default=False, description="Receive marketing communications"
    )

    # Advanced privacy
    secure_deletion: bool = Field(
        default=True, description="Use secure deletion methods"
    )
    encrypt_sensitive_data: bool = Field(
        default=True, description="Encrypt sensitive data"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data_collection": True,
                "analytics": True,
                "personalization": True,
                "data_retention_period": "1_year",
                "share_anonymous_usage": False,
                "marketing_communications": False,
                "secure_deletion": True,
                "encrypt_sensitive_data": True,
            }
        }
    )


# Complete Preferences Response Schema
class UserPreferencesResponse(BaseModel):
    """Complete user preferences response schema."""

    user_id: str = Field(description="User ID")
    version: str = Field(default="1.0", description="Preferences schema version")
    ui: UIPreferencesSchema = Field(description="UI preferences")
    notifications: NotificationPreferencesSchema = Field(
        description="Notification preferences"
    )
    ai: AIPreferencesSchema = Field(description="AI preferences")
    integrations: IntegrationPreferencesSchema = Field(
        description="Integration preferences"
    )
    privacy: PrivacyPreferencesSchema = Field(description="Privacy preferences")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    # New timezone fields
    timezone_mode: str = Field(
        default="auto", description="Timezone mode: 'auto' or 'manual'"
    )
    manual_timezone: str = Field(
        default="",
        description="Manual timezone override (IANA name, or empty if not set)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_123",
                "ui": {
                    "theme": "dark",
                    "language": "en",
                    # "timezone": "America/New_York",  # DEPRECATED
                },
                "timezone_mode": "manual",
                "manual_timezone": "America/New_York",
                "notifications": {
                    "email_notifications": True,
                    "summary_frequency": "daily",
                },
                "ai": {"preferred_provider": "openai", "preferred_model": "gpt-4"},
                "integrations": {"auto_sync": True, "google_drive_enabled": True},
                "privacy": {"data_collection": True, "analytics": True},
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
            }
        }
    )


# Preferences Update Schema
class UserPreferencesUpdate(BaseModel):
    """User preferences update schema for partial updates."""

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
    # New timezone fields (optional for partial update)
    timezone_mode: Optional[str] = Field(
        None, description="Timezone mode: 'auto' or 'manual'"
    )
    manual_timezone: Optional[str] = Field(
        None, description="Manual timezone override (IANA name, or empty if not set)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ui": {"theme": "dark", "language": "en"},
                "timezone_mode": "manual",
                "manual_timezone": "America/New_York",
                "notifications": {"email_notifications": False},
            }
        }
    )


# Preferences Reset Schema
class PreferencesResetRequest(BaseModel):
    """Preferences reset request schema."""

    categories: Optional[List[str]] = Field(
        None, description="Categories to reset (if None, reset all)"
    )

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate category names."""
        if v is None:
            return v

        valid_categories = ["ui", "notifications", "ai", "integrations", "privacy"]
        for category in v:
            if category not in valid_categories:
                raise ValueError(
                    f"Invalid category: {category}. Valid categories: {', '.join(valid_categories)}"
                )
        return v

    model_config = ConfigDict(
        json_schema_extra={"example": {"categories": ["ui", "notifications"]}}
    )


# Preferences Export Schema
class PreferencesExportResponse(BaseModel):
    """Preferences export response schema."""

    user_id: str = Field(description="User ID")
    preferences: Dict = Field(description="Complete preferences data")
    exported_at: datetime = Field(description="Export timestamp")
    version: str = Field(default="1.0", description="Export format version")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_123",
                "preferences": {
                    "ui": {"theme": "dark"},
                    "notifications": {"email_notifications": True},
                },
                "exported_at": "2024-01-01T12:00:00Z",
                "version": "1.0",
            }
        }
    )


# Preferences Import Schema
class PreferencesImportRequest(BaseModel):
    """Preferences import request schema."""

    preferences: Dict = Field(description="Preferences data to import")
    version: str = Field(default="1.0", description="Import format version")
    merge_strategy: str = Field(
        default="replace", description="How to merge imported preferences"
    )

    @field_validator("merge_strategy")
    @classmethod
    def validate_merge_strategy(cls, v: str) -> str:
        """Enhanced merge strategy validation."""
        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "merge_strategy")

        # Sanitize the input
        sanitized = sanitize_text_input(v, max_length=50)
        if sanitized is None:
            raise ValueError("Value cannot be empty after sanitization")

        # Use enum validation
        valid_strategies = ["replace", "merge", "skip_existing"]
        return validate_enum_value(sanitized, valid_strategies, "merge_strategy")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "preferences": {
                    "ui": {"theme": "dark"},
                    "notifications": {"email_notifications": True},
                },
                "version": "1.0",
                "merge_strategy": "merge",
            }
        }
    )
