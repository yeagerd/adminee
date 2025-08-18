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
    service_port: int = Field(default=8006, env="OFFICE_ROUTER_PORT")
    service_host: str = Field(default="0.0.0.0", env="OFFICE_ROUTER_HOST")

    # API Keys
    api_frontend_office_router_key: str = get_secret("API_FRONTEND_OFFICE_ROUTER_KEY")
    api_office_router_user_key: str = get_secret("API_OFFICE_ROUTER_USER_KEY")
    api_office_router_office_key: str = get_secret("API_OFFICE_ROUTER_OFFICE_KEY")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Downstream service endpoints
    vespa_endpoint: str = Field(default="http://localhost:8080", env="VESPA_ENDPOINT")
    vespa_enabled: bool = Field(default=True, env="VESPA_ENABLED")
    vespa_timeout: int = Field(default=30, env="VESPA_TIMEOUT")

    shipments_endpoint: str = Field(
        default="http://localhost:8001", env="SHIPMENTS_ENDPOINT"
    )
    shipments_enabled: bool = Field(default=True, env="SHIPMENTS_ENABLED")
    shipments_timeout: int = Field(default=30, env="SHIPMENTS_TIMEOUT")

    contacts_endpoint: str = Field(
        default="http://localhost:8002", env="CONTACTS_ENDPOINT"
    )
    contacts_enabled: bool = Field(default=True, env="CONTACTS_ENABLED")
    contacts_timeout: int = Field(default=30, env="CONTACTS_TIMEOUT")

    notifications_endpoint: str = Field(
        default="http://localhost:8003", env="NOTIFICATIONS_ENDPOINT"
    )
    notifications_enabled: bool = Field(default=True, env="NOTIFICATIONS_ENABLED")
    notifications_timeout: int = Field(default=30, env="NOTIFICATIONS_TIMEOUT")

    # PubSub configuration
    pubsub_project_id: str = Field(default="briefly-dev", env="PUBSUB_PROJECT_ID")
    pubsub_emulator_host: str = Field(
        default="localhost:8085", env="PUBSUB_EMULATOR_HOST"
    )
    pubsub_email_topic: str = Field(default="email-backfill", env="PUBSUB_EMAIL_TOPIC")
    pubsub_email_subscription: str = Field(
        default="email-router-subscription", env="PUBSUB_EMAIL_SUBSCRIPTION"
    )
    pubsub_calendar_topic: str = Field(
        default="calendar-updates", env="PUBSUB_CALENDAR_TOPIC"
    )
    pubsub_calendar_subscription: str = Field(
        default="calendar-router-subscription", env="PUBSUB_CALENDAR_SUBSCRIPTION"
    )

    # Retry configuration
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay_seconds: float = Field(default=1.0, env="RETRY_DELAY_SECONDS")

    # Rate limiting
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    requests_per_second: float = Field(default=100.0, env="REQUESTS_PER_SECOND")

    # Health check configuration
    health_check_interval_seconds: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout_seconds: int = Field(default=5, env="HEALTH_CHECK_TIMEOUT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
