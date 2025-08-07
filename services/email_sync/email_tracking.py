"""
Email processing state tracking for Gmail and Microsoft providers.

This module handles tracking which emails have been processed to avoid
duplicate processing and enable incremental sync.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from services.common.settings import BaseSettings, Field
from services.email_sync.database import get_session, init_db
from services.email_sync.models.email_tracking import EmailProcessingState


class EmailTrackingSettings(BaseSettings):
    """Settings for email tracking database."""

    db_url_email_sync: str = Field(
        default="sqlite:///email_tracking.db",
        description="Database URL for tracking",
        validation_alias="DB_URL_EMAIL_SYNC",
    )
    GOOGLE_CLOUD_PROJECT: str = Field("test-project", description="GCP project ID")


class EmailTrackingService:
    """Service for managing email processing state."""

    def __init__(self) -> None:
        self.settings = EmailTrackingSettings()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the tracking database."""
        init_db()

    def _get_session(self) -> Session:
        """Get a database session."""
        return get_session()

    def get_processing_state(
        self, user_email: str, provider: str
    ) -> Optional[EmailProcessingState]:
        """Get the processing state for a user and provider."""
        with self._get_session() as session:
            statement = select(EmailProcessingState).where(
                EmailProcessingState.user_email == user_email,
                EmailProcessingState.provider == provider,
            )
            return session.exec(statement).first()

    def update_processing_state(
        self,
        user_email: str,
        provider: str,
        last_processed_id: Optional[str] = None,
        last_processed_timestamp: Optional[datetime] = None,
        history_id: Optional[str] = None,
        delta_link: Optional[str] = None,
    ) -> None:
        """Update the processing state for a user and provider."""
        with self._get_session() as session:
            statement = select(EmailProcessingState).where(
                EmailProcessingState.user_email == user_email,
                EmailProcessingState.provider == provider,
            )
            state = session.exec(statement).first()

            if not state:
                state = EmailProcessingState(user_email=user_email, provider=provider)
                session.add(state)

            if last_processed_id is not None:
                state.last_processed_id = last_processed_id
            if last_processed_timestamp is not None:
                state.last_processed_timestamp = last_processed_timestamp
            if history_id is not None:
                state.history_id = history_id
            if delta_link is not None:
                state.delta_link = delta_link

            state.updated_at = datetime.now(timezone.utc)
            session.commit()

            logging.info(
                f"Updated processing state for {user_email} ({provider}): "
                f"last_processed_id={state.last_processed_id}, "
                f"history_id={state.history_id}, delta_link={state.delta_link}"
            )

    def get_gmail_history_id(self, user_email: str) -> Optional[str]:
        """Get the last processed history ID for Gmail."""
        state = self.get_processing_state(user_email, "gmail")
        return state.history_id if state and state.history_id else None

    def get_microsoft_delta_link(self, user_email: str) -> Optional[str]:
        """Get the last processed delta link for Microsoft."""
        state = self.get_processing_state(user_email, "microsoft")
        return state.delta_link if state and state.delta_link else None

    def mark_email_processed(
        self,
        user_email: str,
        provider: str,
        email_id: str,
        email_timestamp: Optional[datetime] = None,
    ) -> None:
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
