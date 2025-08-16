#!/usr/bin/env python3
"""
Demo-specific settings for Vespa and other demo scripts.

This module provides configuration that's appropriate for demo/development
use without requiring production service settings.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path


class DemoSettings:
    """Settings for demo scripts with sensible defaults."""
    
    def __init__(self):
        # Load from .env file if it exists
        self._load_env_file()
    
    def _load_env_file(self):
        """Load environment variables from .env file in project root."""
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        os.environ[key] = value
    
    @property
    def office_service_url(self) -> str:
        """Office service URL for demos."""
        return os.getenv("OFFICE_SERVICE_URL", "http://localhost:8003")
    
    @property
    def user_service_url(self) -> str:
        """User service URL for demos."""
        return os.getenv("USER_SERVICE_URL", "http://localhost:8001")
    
    @property
    def chat_service_url(self) -> str:
        """Chat service URL for demos."""
        return os.getenv("CHAT_SERVICE_URL", "http://localhost:8002")
    
    @property
    def vespa_endpoint(self) -> str:
        """Vespa endpoint for demos."""
        return os.getenv("VESPA_ENDPOINT", "http://localhost:8080")
    
    @property
    def vespa_loader_url(self) -> str:
        """Vespa loader service URL."""
        return os.getenv("VESPA_LOADER_URL", "http://localhost:9001")
    
    @property
    def vespa_query_url(self) -> str:
        """Vespa query service URL."""
        return os.getenv("VESPA_QUERY_URL", "http://localhost:9002")
    
    @property
    def pubsub_project_id(self) -> str:
        """Pub/Sub project ID for demos."""
        return os.getenv("PUBSUB_PROJECT_ID", "briefly-dev")
    
    @property
    def pubsub_emulator_host(self) -> str:
        """Pub/Sub emulator host for demos."""
        return os.getenv("PUBSUB_EMULATOR_HOST", "localhost:8085")
    
    @property
    def api_frontend_office_key(self) -> str:
        """Frontend API key for office service access."""
        return os.getenv("API_FRONTEND_OFFICE_KEY", "test-FRONTEND_OFFICE_KEY")
    
    @property
    def api_frontend_user_key(self) -> str:
        """Frontend API key for user service access."""
        return os.getenv("API_FRONTEND_USER_KEY", "test-FRONTEND_USER_KEY")
    
    @property
    def api_frontend_chat_key(self) -> str:
        """Frontend API key for chat service access."""
        return os.getenv("API_FRONTEND_CHAT_KEY", "test-FRONTEND_CHAT_KEY")
    
    @property
    def demo_user_id(self) -> str:
        """Default demo user ID."""
        return os.getenv("DEMO_USER_ID", "demo_user_1")
    
    @property
    def demo_user_email(self) -> str:
        """Default demo user email."""
        return os.getenv("DEMO_USER_EMAIL", "trybriefly@outlook.com")
    
    @property
    def demo_providers(self) -> list[str]:
        """Default demo providers."""
        providers = os.getenv("DEMO_PROVIDERS", "microsoft,google")
        return [p.strip() for p in providers.split(",")]
    
    @property
    def demo_batch_size(self) -> int:
        """Default demo batch size."""
        return int(os.getenv("DEMO_BATCH_SIZE", "100"))
    
    @property
    def demo_rate_limit(self) -> float:
        """Default demo rate limit (seconds between batches)."""
        return float(os.getenv("DEMO_RATE_LIMIT", "1.0"))
    
    @property
    def demo_max_emails(self) -> int:
        """Default demo max emails per user."""
        return int(os.getenv("DEMO_MAX_EMAILS", "1000"))
    
    @property
    def demo_folders(self) -> list[str]:
        """Default demo email folders."""
        folders = os.getenv("DEMO_FOLDERS", "INBOX,SENT,DRAFTS")
        return [f.strip() for f in folders.split(",")]
    
    @property
    def nextauth_test_server_url(self) -> str:
        """NextAuth test server URL for demos."""
        return os.getenv("NEXTAUTH_TEST_SERVER_URL", "http://localhost:3001")
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get all API keys as a dictionary."""
        return {
            "office": self.api_frontend_office_key,
            "user": self.api_frontend_user_key,
            "chat": self.api_frontend_chat_key,
        }
    
    def get_demo_config(self) -> Dict[str, Any]:
        """Get demo configuration as a dictionary."""
        return {
            "demo_users": [self.demo_user_id],
            "providers": self.demo_providers,
            "batch_size": self.demo_batch_size,
            "rate_limit": self.demo_rate_limit,
            "max_emails_per_user": self.demo_max_emails,
            "folders": self.demo_folders,
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
