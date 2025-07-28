"""
Tests for email tracking service.
"""

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from services.email_sync.email_tracking import (
    EmailProcessingState,
    EmailTrackingService,
)


class TestEmailProcessingState:
    """Test EmailProcessingState class."""

    def test_initialization(self):
        """Test EmailProcessingState initialization."""
        state = EmailProcessingState("user@example.com", "gmail")
        assert state.user_email == "user@example.com"
        assert state.provider == "gmail"
        assert state.last_processed_id is None
        assert state.last_processed_timestamp is None
        assert state.history_id is None
        assert state.delta_link is None
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = EmailProcessingState("user@example.com", "gmail")
        state.last_processed_id = "email123"
        state.last_processed_timestamp = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )
        state.history_id = "history456"

        data = state.to_dict()
        assert data["user_email"] == "user@example.com"
        assert data["provider"] == "gmail"
        assert data["last_processed_id"] == "email123"
        assert data["last_processed_timestamp"] == "2024-01-15T10:30:00+00:00"
        assert data["history_id"] == "history456"
        assert data["delta_link"] is None

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "user_email": "user@example.com",
            "provider": "microsoft",
            "last_processed_id": "email789",
            "last_processed_timestamp": "2024-01-15T11:00:00+00:00",
            "history_id": None,
            "delta_link": "delta_link_123",
            "created_at": "2024-01-15T09:00:00+00:00",
            "updated_at": "2024-01-15T11:00:00+00:00",
        }

        state = EmailProcessingState.from_dict(data)
        assert state.user_email == "user@example.com"
        assert state.provider == "microsoft"
        assert state.last_processed_id == "email789"
        assert state.last_processed_timestamp == datetime(
            2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc
        )
        assert state.history_id is None
        assert state.delta_link == "delta_link_123"


class TestEmailTrackingService:
    """Test EmailTrackingService class."""

    @pytest.fixture
    def temp_db_file(self):
        """Create a temporary database file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            temp_file = f.name

        yield temp_file

        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    @pytest.fixture
    def tracking_service(self, temp_db_file):
        """Create EmailTrackingService with temporary database."""
        service = EmailTrackingService()
        service.db_file = temp_db_file
        service._ensure_db_file()
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
            history_id="history456",
        )

        state = tracking_service.get_processing_state("user@example.com", "gmail")
        assert state is not None
        assert state.user_email == "user@example.com"
        assert state.provider == "gmail"
        assert state.last_processed_id == "email123"
        assert state.history_id == "history456"

    def test_update_processing_state_existing(self, tracking_service):
        """Test updating processing state for existing user."""
        # Create initial state
        tracking_service.update_processing_state(
            user_email="user@example.com",
            provider="gmail",
            last_processed_id="email123",
            history_id="history456",
        )

        # Update state
        tracking_service.update_processing_state(
            user_email="user@example.com",
            provider="gmail",
            last_processed_id="email789",
            history_id="history999",
        )

        state = tracking_service.get_processing_state("user@example.com", "gmail")
        assert state.last_processed_id == "email789"
        assert state.history_id == "history999"

    def test_get_gmail_history_id(self, tracking_service):
        """Test getting Gmail history ID."""
        tracking_service.update_processing_state(
            user_email="user@example.com", provider="gmail", history_id="history123"
        )

        history_id = tracking_service.get_gmail_history_id("user@example.com")
        assert history_id == "history123"

    def test_get_microsoft_delta_link(self, tracking_service):
        """Test getting Microsoft delta link."""
        tracking_service.update_processing_state(
            user_email="user@example.com",
            provider="microsoft",
            delta_link="delta_link_456",
        )

        delta_link = tracking_service.get_microsoft_delta_link("user@example.com")
        assert delta_link == "delta_link_456"

    def test_mark_email_processed(self, tracking_service):
        """Test marking email as processed."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        tracking_service.mark_email_processed(
            user_email="user@example.com",
            provider="gmail",
            email_id="email123",
            email_timestamp=timestamp,
        )

        state = tracking_service.get_processing_state("user@example.com", "gmail")
        assert state.last_processed_id == "email123"
        assert state.last_processed_timestamp == timestamp

    def test_is_email_processed_true(self, tracking_service):
        """Test checking if email is processed (true case)."""
        tracking_service.mark_email_processed(
            user_email="user@example.com", provider="gmail", email_id="email123"
        )

        assert (
            tracking_service.is_email_processed("user@example.com", "gmail", "email123")
            is True
        )

    def test_is_email_processed_false(self, tracking_service):
        """Test checking if email is processed (false case)."""
        tracking_service.mark_email_processed(
            user_email="user@example.com", provider="gmail", email_id="email123"
        )

        assert (
            tracking_service.is_email_processed("user@example.com", "gmail", "email456")
            is False
        )

    def test_multiple_users_and_providers(self, tracking_service):
        """Test tracking multiple users and providers."""
        # User 1 with Gmail
        tracking_service.update_processing_state(
            user_email="user1@example.com",
            provider="gmail",
            last_processed_id="gmail_email_1",
            history_id="gmail_history_1",
        )

        # User 1 with Microsoft
        tracking_service.update_processing_state(
            user_email="user1@example.com",
            provider="microsoft",
            last_processed_id="ms_email_1",
            delta_link="ms_delta_1",
        )

        # User 2 with Gmail
        tracking_service.update_processing_state(
            user_email="user2@example.com",
            provider="gmail",
            last_processed_id="gmail_email_2",
            history_id="gmail_history_2",
        )

        # Verify states are independent
        gmail_state_1 = tracking_service.get_processing_state(
            "user1@example.com", "gmail"
        )
        ms_state_1 = tracking_service.get_processing_state(
            "user1@example.com", "microsoft"
        )
        gmail_state_2 = tracking_service.get_processing_state(
            "user2@example.com", "gmail"
        )

        assert gmail_state_1.last_processed_id == "gmail_email_1"
        assert gmail_state_1.history_id == "gmail_history_1"
        assert ms_state_1.last_processed_id == "ms_email_1"
        assert ms_state_1.delta_link == "ms_delta_1"
        assert gmail_state_2.last_processed_id == "gmail_email_2"
        assert gmail_state_2.history_id == "gmail_history_2"

    def test_persistence(self, temp_db_file):
        """Test that data persists between service instances."""
        # Create first service instance
        service1 = EmailTrackingService()
        service1.db_file = temp_db_file
        service1._ensure_db_file()

        service1.update_processing_state(
            user_email="user@example.com",
            provider="gmail",
            last_processed_id="email123",
            history_id="history456",
        )

        # Create second service instance
        service2 = EmailTrackingService()
        service2.db_file = temp_db_file
        service2._ensure_db_file()

        state = service2.get_processing_state("user@example.com", "gmail")
        assert state is not None
        assert state.last_processed_id == "email123"
        assert state.history_id == "history456"
