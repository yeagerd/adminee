#!/usr/bin/env python3
"""
Configuration settings for the office router service
"""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings
from services.common.config_secrets import get_secret


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    service_name: str = "office-router"
    service_port: int = Field(default=8006)
    service_host: str = Field(default="0.0.0.0")

    # API Keys
    api_frontend_office_router_key: str = get_secret("API_FRONTEND_OFFICE_ROUTER_KEY")
    api_office_router_user_key: str = get_secret("API_OFFICE_ROUTER_USER_KEY")
    api_office_router_office_key: str = get_secret("API_OFFICE_ROUTER_OFFICE_KEY")

    # Logging
    log_level: str = Field(default="INFO")

    # Downstream service endpoints
    vespa_endpoint: str = Field(default="http://localhost:8080")
    vespa_enabled: bool = Field(default=True)
    vespa_timeout: int = Field(default=30)

    shipments_endpoint: str = Field(default="http://localhost:8001")
    shipments_enabled: bool = Field(default=True)
    shipments_timeout: int = Field(default=30)

    contacts_endpoint: str = Field(default="http://localhost:8002")
    contacts_enabled: bool = Field(default=True)
    contacts_timeout: int = Field(default=30)

    notifications_endpoint: str = Field(default="http://localhost:8003")
    notifications_enabled: bool = Field(default=True)
    notifications_timeout: int = Field(default=30)

    # PubSub configuration
    pubsub_project_id: str = Field(default="briefly-dev")
    pubsub_emulator_host: str = Field(default="localhost:8085")
    pubsub_email_topic: str = Field(default="email-backfill")
    pubsub_email_subscription: str = Field(default="email-router-subscription")
    pubsub_calendar_topic: str = Field(default="calendar-updates")
    pubsub_calendar_subscription: str = Field(default="calendar-router-subscription")

    # Retry configuration
    max_retries: int = Field(default=3)
    retry_delay_seconds: float = Field(default=1.0)

    # Rate limiting
    max_concurrent_requests: int = Field(default=10)
    requests_per_second: float = Field(default=100.0)

    # Health check configuration
    health_check_interval_seconds: int = Field(default=30)
    health_check_timeout_seconds: int = Field(default=5)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
