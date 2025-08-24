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
    GEMINI_FLASH = "gemini-flash"


class UIPreferences(BaseModel):
    """User interface preferences."""

    theme: ThemeMode = Field(default=ThemeMode.SYSTEM, description="Theme preference")
    language: Language = Field(default=Language.EN, description="Language preference")
    timezone: Timezone = Field(default=Timezone.UTC, description="Timezone preference")
    date_format: DateFormat = Field(default=DateFormat.ISO, description="Date format preference")
    time_format: TimeFormat = Field(default=TimeFormat.TWENTY_FOUR_HOUR, description="Time format preference")
    compact_mode: bool = Field(default=False, description="Use compact UI mode")
    show_tutorials: bool = Field(default=True, description="Show tutorial tooltips")
    auto_save: bool = Field(default=True, description="Auto-save form changes")


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    email_notifications: bool = Field(default=True, description="Enable email notifications")
    push_notifications: bool = Field(default=True, description="Enable push notifications")
    sms_notifications: bool = Field(default=False, description="Enable SMS notifications")
    frequency: NotificationFrequency = Field(default=NotificationFrequency.IMMEDIATE, description="Notification frequency")
    quiet_hours_start: Optional[str] = Field(default=None, description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(default=None, description="Quiet hours end time (HH:MM)")
    meeting_reminders: bool = Field(default=True, description="Meeting reminder notifications")
    task_reminders: bool = Field(default=True, description="Task reminder notifications")
    integration_alerts: bool = Field(default=True, description="Integration status alerts")

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_time_format(cls: type["NotificationPreferences"], v: Optional[str]) -> Optional[str]:
        """Validate time format."""
        if v is None:
            return v
        
        # Basic time format validation (HH:MM)
        if not isinstance(v, str):
            raise ValueError("Time must be a string")
        
        try:
            hour, minute = v.split(":")
            if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                raise ValueError("Invalid time values")
        except (ValueError, AttributeError):
            raise ValueError("Time must be in HH:MM format")
        
        return v


class AIPreferences(BaseModel):
    """User AI and automation preferences."""

    preferred_provider: AIModelProvider = Field(default=AIModelProvider.ANTHROPIC, description="Preferred AI provider")
    preferred_model: AIModelType = Field(default=AIModelType.CLAUDE_3_SONNET, description="Preferred AI model")
    auto_summarize_emails: bool = Field(default=True, description="Auto-summarize incoming emails")
    auto_categorize_tasks: bool = Field(default=True, description="Auto-categorize tasks")
    smart_scheduling: bool = Field(default=True, description="Enable smart scheduling suggestions")
    ai_assistant_enabled: bool = Field(default=True, description="Enable AI assistant features")
    privacy_level: str = Field(default="balanced", description="AI privacy level (minimal, balanced, strict)")


class IntegrationPreferences(BaseModel):
    """User integration preferences."""

    auto_sync_calendar: bool = Field(default=True, description="Auto-sync calendar events")
    auto_sync_contacts: bool = Field(default=True, description="Auto-sync contacts")
    auto_sync_tasks: bool = Field(default=True, description="Auto-sync tasks")
    sync_frequency: str = Field(default="15min", description="Sync frequency")
    conflict_resolution: str = Field(default="newest_wins", description="Conflict resolution strategy")
    backup_enabled: bool = Field(default=True, description="Enable data backup")


class PrivacyPreferences(BaseModel):
    """User privacy and data preferences."""

    data_sharing: bool = Field(default=False, description="Allow data sharing for analytics")
    personalized_ads: bool = Field(default=False, description="Allow personalized advertisements")
    third_party_access: bool = Field(default=False, description="Allow third-party data access")
    data_retention_days: int = Field(default=365, description="Data retention period in days")
    export_data: bool = Field(default=True, description="Allow data export")
    delete_data: bool = Field(default=True, description="Allow data deletion")


class UserPreferences(BaseModel):
    """Complete user preferences model."""

    ui: UIPreferences = Field(default_factory=UIPreferences, description="UI preferences")
    notifications: NotificationPreferences = Field(default_factory=NotificationPreferences, description="Notification preferences")
    ai: AIPreferences = Field(default_factory=AIPreferences, description="AI preferences")
    integrations: IntegrationPreferences = Field(default_factory=IntegrationPreferences, description="Integration preferences")
    privacy: PrivacyPreferences = Field(default_factory=PrivacyPreferences, description="Privacy preferences")
    created_at: datetime = Field(..., description="When preferences were created")
    updated_at: datetime = Field(..., description="When preferences were last updated")

    model_config = ConfigDict(from_attributes=True)


class PreferencesUpdateRequest(BaseModel):
    """Request model for updating user preferences."""

    ui: Optional[UIPreferences] = Field(None, description="UI preferences to update")
    notifications: Optional[NotificationPreferences] = Field(None, description="Notification preferences to update")
    ai: Optional[AIPreferences] = Field(None, description="AI preferences to update")
    integrations: Optional[IntegrationPreferences] = Field(None, description="Integration preferences to update")
    privacy: Optional[PrivacyPreferences] = Field(None, description="Privacy preferences to update")


class PreferencesResponse(BaseModel):
    """Response model for user preferences."""

    user_id: int = Field(..., description="User ID")
    preferences: UserPreferences = Field(..., description="User preferences")
    last_updated: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)
