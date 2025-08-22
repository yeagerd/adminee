#!/usr/bin/env python3
"""
Demo-specific settings for Vespa and other demo scripts.

This module provides configuration that's appropriate for demo/development
use without requiring production service settings.
"""

from typing import Any, Dict, Optional

from services.common.settings import BaseSettings, Field, SettingsConfigDict


class DemoSettings(BaseSettings):
    """Settings for demo scripts with sensible defaults."""

    model_config = SettingsConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Service URLs
    office_service_url: str = Field(..., description="Office service URL for demos")
    user_service_url: str = Field(..., description="User service URL for demos")
    chat_service_url: str = Field(..., description="Chat service URL for demos")
    vespa_endpoint: str = Field(..., description="Vespa endpoint for demos")
    vespa_loader_url: str = Field(..., description="Vespa loader service URL")
    vespa_query_url: str = Field(..., description="Vespa query service URL")

    # Pub/Sub configuration
    pubsub_project_id: str = Field(
        default="briefly-dev", description="Pub/Sub project ID for demos"
    )
    pubsub_emulator_host: str = Field(
        default="localhost:8085", description="Pub/Sub emulator host for demos"
    )

    # API Keys
    api_frontend_office_key: str = Field(
        ...,
        description="Frontend API key for office service access",
    )
    api_frontend_user_key: str = Field(
        ...,
        description="Frontend API key for user service access",
    )
    api_frontend_chat_key: str = Field(
        ...,
        description="Frontend API key for chat service access",
    )
    api_backfill_office_key: str = Field(
        ...,
        description="Backfill API key for internal service communication",
    )

    # Demo configuration
    demo_user_id: str = Field(default="demo_user_1", description="Default demo user ID")
    demo_user_email: str = Field(
        default="trybriefly@outlook.com", description="Default demo user email"
    )
    demo_providers: str = Field(
        default="microsoft,google", description="Default demo providers"
    )
    demo_batch_size: int = Field(default=100, description="Default demo batch size")
    demo_rate_limit: float = Field(
        default=1.0, description="Default demo rate limit (seconds between batches)"
    )
    demo_max_emails: int = Field(
        default=10, description="Default demo max emails per user"
    )
    demo_folders: str = Field(
        default="INBOX,SENT,DRAFTS", description="Default demo email folders"
    )
    nextauth_test_server_url: str = Field(
        default="http://localhost:3001",
        description="NextAuth test server URL for demos",
    )

    def get_api_keys(self) -> Dict[str, str]:
        """Get all API keys as a dictionary."""
        return {
            "office": self.api_frontend_office_key,
            "user": self.api_frontend_user_key,
            "chat": self.api_frontend_chat_key,
            "backfill": self.api_backfill_office_key,  # Add backfill key
        }

    def get_demo_config(self) -> Dict[str, Any]:
        """Get demo configuration as a dictionary."""
        return {
            "demo_users": [self.demo_user_id],
            "providers": [p.strip() for p in self.demo_providers.split(",")],
            "batch_size": self.demo_batch_size,
            "rate_limit": self.demo_rate_limit,
            "max_emails_per_user": self.demo_max_emails,
            "folders": [f.strip() for f in self.demo_folders.split(",")],
            "project_id": self.pubsub_project_id,
            "emulator_host": self.pubsub_emulator_host,
            "vespa_endpoint": self.vespa_endpoint,
            "vespa_loader_url": self.vespa_loader_url,
            "vespa_query_url": self.vespa_query_url,
        }


# Global demo settings instance
_demo_settings: Optional[DemoSettings] = None


def get_demo_settings() -> DemoSettings:
    """Get the global demo settings instance, creating it if necessary."""
    global _demo_settings
    if _demo_settings is None:
        _demo_settings = DemoSettings()
    return _demo_settings
