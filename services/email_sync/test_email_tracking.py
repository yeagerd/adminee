"""
Tests for email tracking service.
"""

import os
import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine

from services.email_sync.email_tracking import EmailTrackingService
from services.email_sync.models.email_tracking import EmailProcessingState
from sqlmodel import SQLModel


class TestEmailProcessingState:
    """Test EmailProcessingState SQLModel."""

    def test_initialization(self):
        """Test EmailProcessingState initialization."""
        state = EmailProcessingState(
            user_email="user@example.com",
            provider="gmail"
        )
        assert state.user_email == "user@example.com"
        assert state.provider == "gmail"
        assert state.last_processed_id is None
        assert state.last_processed_timestamp is None
        assert state.history_id is None
        assert state.delta_link is None
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime)

    def test_repr(self):
        """Test string representation."""
        state = EmailProcessingState(
            user_email="user@example.com",
            provider="gmail"
        )
        assert "user@example.com" in repr(state)
        assert "gmail" in repr(state)


class TestEmailTrackingService:
    """Test EmailTrackingService class."""

    @pytest.fixture
    def temp_db_engine(self):
        """Create a temporary database engine for testing."""
        # Create a temporary SQLite database
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db.close()
        
        engine = create_engine(f"sqlite:///{temp_db.name}", echo=False, future=True)
        SQLModel.metadata.create_all(bind=engine)
        
        yield engine
        
        # Cleanup
        engine.dispose()
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)

    @pytest.fixture
    def tracking_service(self, temp_db_engine, monkeypatch):
        """Create EmailTrackingService with temporary database."""
        # Patch the database engine to use our temporary one
        def mock_get_engine():
            return temp_db_engine
        
        from services.email_sync import database
        monkeypatch.setattr(database, "get_engine", mock_get_engine)
        
        service = EmailTrackingService()
        return service

    def test_get_processing_state_nonexistent(self, tracking_service):
        """Test getting processing state for non-existent user."""
        state = tracking_service.get_processing_state("user@example.com", "gmail")
        assert state is None

    def test_update_processing_state_new(self, tracking_service):
        """Test updating processing state for new user."""
        tracking_service.update_processing_state(
            user_email="user@example.com",
            provider="gmail",
            last_processed_id="email123",
            history_id="history456"
        )

        state = tracking_service.get_processing_state("user@example.com", "gmail")
        assert state is not None
        assert state.user_email == "user@example.com"
        assert state.provider == "gmail"
        assert state.last_processed_id == "email123"
        assert state.history_id == "history456"
        assert state.delta_link is None

    def test_update_processing_state_existing(self, tracking_service):
        """Test updating processing state for existing user."""
        # First update
        tracking_service.update_processing_state(
            user_email="user@example.com",
            provider="gmail",
            last_processed_id="email123",
            history_id="history456"
        )

        # Second update
        tracking_service.update_processing_state(
            user_email="user@example.com",
            provider="gmail",
            last_processed_id="email789",
            history_id="history999"
        )

        state = tracking_service.get_processing_state("user@example.com", "gmail")
        assert state.last_processed_id == "email789"
        assert state.history_id == "history999"

    def test_get_gmail_history_id(self, tracking_service):
        """Test getting Gmail history ID."""
        tracking_service.update_processing_state(
            user_email="user@example.com",
            provider="gmail",
            history_id="history123"
        )

        history_id = tracking_service.get_gmail_history_id("user@example.com")
        assert history_id == "history123"

    def test_get_microsoft_delta_link(self, tracking_service):
        """Test getting Microsoft delta link."""
        tracking_service.update_processing_state(
            user_email="user@example.com",
            provider="microsoft",
            delta_link="delta_link_123"
        )

        delta_link = tracking_service.get_microsoft_delta_link("user@example.com")
        assert delta_link == "delta_link_123"

    def test_mark_email_processed(self, tracking_service):
        """Test marking email as processed."""
        email_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        
        tracking_service.mark_email_processed(
            user_email="user@example.com",
            provider="gmail",
            email_id="email123",
            email_timestamp=email_timestamp
        )

        state = tracking_service.get_processing_state("user@example.com", "gmail")
        assert state.last_processed_id == "email123"
        # Compare without timezone info since SQLite stores naive datetimes
        assert state.last_processed_timestamp.replace(tzinfo=None) == email_timestamp.replace(tzinfo=None)

    def test_is_email_processed_true(self, tracking_service):
        """Test checking if email is processed (true case)."""
        tracking_service.mark_email_processed(
            user_email="user@example.com",
            provider="gmail",
            email_id="email123"
        )

        assert tracking_service.is_email_processed("user@example.com", "gmail", "email123") is True

    def test_is_email_processed_false(self, tracking_service):
        """Test checking if email is processed (false case)."""
        tracking_service.mark_email_processed(
            user_email="user@example.com",
            provider="gmail",
            email_id="email123"
        )

        assert tracking_service.is_email_processed("user@example.com", "gmail", "email456") is False

    def test_multiple_users_and_providers(self, tracking_service):
        """Test multiple users and providers."""
        # User 1, Gmail
        tracking_service.update_processing_state(
            user_email="user1@example.com",
            provider="gmail",
            last_processed_id="email1",
            history_id="history1"
        )

        # User 1, Microsoft
        tracking_service.update_processing_state(
            user_email="user1@example.com",
            provider="microsoft",
            last_processed_id="email2",
            delta_link="delta1"
        )

        # User 2, Gmail
        tracking_service.update_processing_state(
            user_email="user2@example.com",
            provider="gmail",
            last_processed_id="email3",
            history_id="history2"
        )

        # Verify all states are separate
        state1_gmail = tracking_service.get_processing_state("user1@example.com", "gmail")
        state1_ms = tracking_service.get_processing_state("user1@example.com", "microsoft")
        state2_gmail = tracking_service.get_processing_state("user2@example.com", "gmail")

        assert state1_gmail.last_processed_id == "email1"
        assert state1_gmail.history_id == "history1"
        assert state1_ms.last_processed_id == "email2"
        assert state1_ms.delta_link == "delta1"
        assert state2_gmail.last_processed_id == "email3"
        assert state2_gmail.history_id == "history2"

    def test_persistence(self, temp_db_engine, monkeypatch):
        """Test that data persists between service instances."""
        # Patch the database engine
        def mock_get_engine():
            return temp_db_engine
        
        from services.email_sync import database
        monkeypatch.setattr(database, "get_engine", mock_get_engine)
        
        # Create first service instance
        service1 = EmailTrackingService()
        service1.update_processing_state(
            user_email="user@example.com",
            provider="gmail",
            last_processed_id="email123",
            history_id="history456"
        )

        # Create second service instance
        service2 = EmailTrackingService()
        state = service2.get_processing_state("user@example.com", "gmail")
        
        assert state is not None
        assert state.last_processed_id == "email123"
        assert state.history_id == "history456"
