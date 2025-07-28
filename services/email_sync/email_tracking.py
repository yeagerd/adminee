"""
Email processing state tracking for Gmail and Microsoft providers.

This module handles tracking which emails have been processed to avoid
duplicate processing and enable incremental sync.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.common.settings import BaseSettings, Field


class EmailTrackingSettings(BaseSettings):
    """Settings for email tracking database."""

    DATABASE_URL: str = Field(
        "sqlite:///email_tracking.db", description="Database URL for tracking"
    )
    GOOGLE_CLOUD_PROJECT: str = Field("test-project", description="GCP project ID")


class EmailProcessingState:
    """Tracks email processing state for a user and provider."""

    def __init__(self, user_email: str, provider: str):
        self.user_email = user_email
        self.provider = provider  # 'gmail' or 'microsoft'
        self.last_processed_id: Optional[str] = None
        self.last_processed_timestamp: Optional[datetime] = None
        self.history_id: Optional[str] = None  # Gmail specific
        self.delta_link: Optional[str] = None  # Microsoft specific
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_email": self.user_email,
            "provider": self.provider,
            "last_processed_id": self.last_processed_id,
            "last_processed_timestamp": (
                self.last_processed_timestamp.isoformat()
                if self.last_processed_timestamp
                else None
            ),
            "history_id": self.history_id,
            "delta_link": self.delta_link,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailProcessingState":
        """Create from dictionary."""
        state = cls(data["user_email"], data["provider"])
        state.last_processed_id = data.get("last_processed_id")
        state.last_processed_timestamp = (
            datetime.fromisoformat(data["last_processed_timestamp"])
            if data.get("last_processed_timestamp")
            else None
        )
        state.history_id = data.get("history_id")
        state.delta_link = data.get("delta_link")
        state.created_at = datetime.fromisoformat(data["created_at"])
        state.updated_at = datetime.fromisoformat(data["updated_at"])
        return state


class EmailTrackingService:
    """Service for managing email processing state."""

    def __init__(self):
        self.settings = EmailTrackingSettings()
        self._init_database()

    def _init_database(self):
        """Initialize the tracking database."""
        # For now, use a simple file-based storage
        # In production, this would be a proper database
        self.db_file = "email_tracking.json"
        self._ensure_db_file()

    def _ensure_db_file(self):
        """Ensure the database file exists."""
        if not os.path.exists(self.db_file):
            with open(self.db_file, "w") as f:
                json.dump({}, f)

    def _load_states(self) -> Dict[str, EmailProcessingState]:
        """Load all processing states from storage."""
        try:
            with open(self.db_file, "r") as f:
                data = json.load(f)
                states = {}
                for key, state_data in data.items():
                    states[key] = EmailProcessingState.from_dict(state_data)
                return states
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_states(self, states: Dict[str, EmailProcessingState]):
        """Save all processing states to storage."""
        data = {}
        for key, state in states.items():
            data[key] = state.to_dict()
        with open(self.db_file, "w") as f:
            json.dump(data, f, indent=2)

    def _get_state_key(self, user_email: str, provider: str) -> str:
        """Get the key for a user/provider combination."""
        return f"{user_email}:{provider}"

    def get_processing_state(
        self, user_email: str, provider: str
    ) -> Optional[EmailProcessingState]:
        """Get the processing state for a user and provider."""
        states = self._load_states()
        key = self._get_state_key(user_email, provider)
        return states.get(key)

    def update_processing_state(
        self,
        user_email: str,
        provider: str,
        last_processed_id: Optional[str] = None,
        last_processed_timestamp: Optional[datetime] = None,
        history_id: Optional[str] = None,
        delta_link: Optional[str] = None,
    ):
        """Update the processing state for a user and provider."""
        states = self._load_states()
        key = self._get_state_key(user_email, provider)

        if key not in states:
            states[key] = EmailProcessingState(user_email, provider)

        state = states[key]
        if last_processed_id is not None:
            state.last_processed_id = last_processed_id
        if last_processed_timestamp is not None:
            state.last_processed_timestamp = last_processed_timestamp
        if history_id is not None:
            state.history_id = history_id
        if delta_link is not None:
            state.delta_link = delta_link

        state.updated_at = datetime.now(timezone.utc)
        self._save_states(states)
        logging.info(
            f"Updated processing state for {user_email} ({provider}): {state.to_dict()}"
        )

    def get_gmail_history_id(self, user_email: str) -> Optional[str]:
        """Get the last processed history ID for Gmail."""
        state = self.get_processing_state(user_email, "gmail")
        return state.history_id if state else None

    def get_microsoft_delta_link(self, user_email: str) -> Optional[str]:
        """Get the last processed delta link for Microsoft."""
        state = self.get_processing_state(user_email, "microsoft")
        return state.delta_link if state else None

    def mark_email_processed(
        self,
        user_email: str,
        provider: str,
        email_id: str,
        email_timestamp: Optional[datetime] = None,
    ):
        """Mark an email as processed."""
        self.update_processing_state(
            user_email=user_email,
            provider=provider,
            last_processed_id=email_id,
            last_processed_timestamp=email_timestamp or datetime.now(timezone.utc),
        )

    def is_email_processed(self, user_email: str, provider: str, email_id: str) -> bool:
        """Check if an email has been processed."""
        state = self.get_processing_state(user_email, provider)
        if not state or not state.last_processed_id:
            return False
        return email_id == state.last_processed_id


# Global instance
email_tracking_service = EmailTrackingService()
