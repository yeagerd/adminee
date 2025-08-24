"""
Tests for the Contact model class.

Tests contact model functionality, event handling, and relevance scoring.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from services.contacts.models.contact import Contact, EmailContactEventCount


@pytest.fixture
def sample_contact():
    """Create a sample Contact instance for testing."""
    return Contact(
        id="contact_123",
        user_id="test_user_123",
        email_address="test@example.com",
        display_name="Test User",
        given_name="Test",
        family_name="User",
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc),
        tags=["test", "example"],
        notes="A test contact",
    )


@pytest.fixture
def sample_event_count():
    """Create a sample EmailContactEventCount instance for testing."""
    return EmailContactEventCount(
        event_type="email",
        count=5,
        last_seen=datetime.now(timezone.utc),
        first_seen=datetime.now(timezone.utc),
    )


class TestContactModel:
    """Test cases for Contact model."""

    def test_contact_creation(self, sample_contact):
        """Test contact creation with all fields."""
        assert sample_contact.id == "contact_123"
        assert sample_contact.user_id == "test_user_123"
        assert sample_contact.email_address == "test@example.com"
        assert sample_contact.display_name == "Test User"
        assert sample_contact.given_name == "Test"
        assert sample_contact.family_name == "User"
        assert sample_contact.tags == ["test", "example"]
        assert sample_contact.notes == "A test contact"
        assert sample_contact.total_event_count == 0
        assert sample_contact.relevance_score == 0.0
        assert sample_contact.source_services == []

    def test_contact_defaults(self):
        """Test contact creation with minimal fields."""
        contact = Contact(
            user_id="test_user_123",
            email_address="test@example.com",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
        )

        assert contact.id is None  # Will be set by database
        assert contact.display_name is None
        assert contact.given_name is None
        assert contact.family_name is None
        assert contact.tags == []
        assert contact.notes is None
        assert contact.total_event_count == 0
        assert contact.relevance_score == 0.0
        assert contact.source_services == []
        assert contact.event_counts == {}

    def test_add_event_new_event_type(self, sample_contact):
        """Test adding a new event type."""
        event_timestamp = datetime.now(timezone.utc)
        original_count = sample_contact.total_event_count

        sample_contact.add_event("email", event_timestamp)

        # Check event count was created
        assert "email" in sample_contact.event_counts
        assert sample_contact.event_counts["email"].event_type == "email"
        assert sample_contact.event_counts["email"].count == 1
        assert sample_contact.event_counts["email"].first_seen == event_timestamp
        assert sample_contact.event_counts["email"].last_seen == event_timestamp

        # Check total count increased
        assert sample_contact.total_event_count == original_count + 1

        # Check last_seen was updated
        assert sample_contact.last_seen == event_timestamp

    def test_add_event_existing_event_type(self, sample_contact):
        """Test adding an event to an existing event type."""
        # Add first event
        first_timestamp = datetime.now(timezone.utc)
        sample_contact.add_event("email", first_timestamp)

        # Add second event
        second_timestamp = datetime.now(timezone.utc)
        sample_contact.add_event("email", second_timestamp)

        # Check event count increased
        assert sample_contact.event_counts["email"].count == 2
        assert sample_contact.event_counts["email"].first_seen == first_timestamp
        assert sample_contact.event_counts["email"].last_seen == second_timestamp

        # Check total count
        assert sample_contact.total_event_count == 2

    def test_add_event_multiple_types(self, sample_contact):
        """Test adding events of multiple types."""
        timestamp = datetime.now(timezone.utc)

        sample_contact.add_event("email", timestamp)
        sample_contact.add_event("calendar", timestamp)
        sample_contact.add_event("document", timestamp)

        # Check all event types were created
        assert "email" in sample_contact.event_counts
        assert "calendar" in sample_contact.event_counts
        assert "document" in sample_contact.event_counts

        # Check total count
        assert sample_contact.total_event_count == 3

    def test_calculate_relevance_score_basic(self, sample_contact):
        """Test basic relevance score calculation."""
        # Set up contact with some events
        timestamp = datetime.now(timezone.utc)
        sample_contact.add_event("email", timestamp)
        sample_contact.add_event("calendar", timestamp)

        # Calculate relevance score
        score = sample_contact.calculate_relevance_score()

        # Check score is between 0 and 1
        assert 0.0 <= score <= 1.0

        # Check relevance factors were set
        assert "recency" in sample_contact.relevance_factors
        assert "frequency" in sample_contact.relevance_factors
        assert "diversity" in sample_contact.relevance_factors
        assert "name_completeness" in sample_contact.relevance_factors
        assert "total_score" in sample_contact.relevance_factors

    def test_calculate_relevance_score_with_names(self, sample_contact):
        """Test relevance score calculation with complete names."""
        # Set up contact with complete names
        sample_contact.display_name = "John Doe"
        sample_contact.given_name = "John"
        sample_contact.family_name = "Doe"

        # Add some events
        timestamp = datetime.now(timezone.utc)
        sample_contact.add_event("email", timestamp)

        # Calculate relevance score
        score = sample_contact.calculate_relevance_score()

        # Check score is reasonable
        assert score > 0.0

        # Check name completeness factor
        name_factor = sample_contact.relevance_factors["name_completeness"]
        assert name_factor > 0.0

    def test_calculate_relevance_score_old_contact(self, sample_contact):
        """Test relevance score calculation for old contacts."""
        # Set up contact with old last_seen
        old_timestamp = datetime.now(timezone.utc)
        old_timestamp = old_timestamp.replace(day=old_timestamp.day - 60)  # 60 days ago
        sample_contact.last_seen = old_timestamp

        # Add some events
        timestamp = datetime.now(timezone.utc)
        sample_contact.add_event("email", timestamp)

        # Calculate relevance score
        score = sample_contact.calculate_relevance_score()

        # Check score is lower due to age
        assert score < 0.5  # Should be lower due to recency factor

    def test_get_primary_name_display_name(self, sample_contact):
        """Test getting primary name when display_name is set."""
        sample_contact.display_name = "John Doe"

        result = sample_contact.get_primary_name()
        assert result == "John Doe"

    def test_get_primary_name_given_family(self, sample_contact):
        """Test getting primary name from given and family names."""
        sample_contact.given_name = "John"
        sample_contact.family_name = "Doe"

        result = sample_contact.get_primary_name()
        assert result == "John Doe"

    def test_get_primary_name_given_only(self, sample_contact):
        """Test getting primary name when only given name is set."""
        sample_contact.given_name = "John"

        result = sample_contact.get_primary_name()
        assert result == "John"

    def test_get_primary_name_family_only(self, sample_contact):
        """Test getting primary name when only family name is set."""
        sample_contact.family_name = "Doe"

        result = sample_contact.get_primary_name()
        assert result == "Doe"

    def test_get_primary_name_email_fallback(self, sample_contact):
        """Test getting primary name falls back to email when no names are set."""
        sample_contact.display_name = None
        sample_contact.given_name = None
        sample_contact.family_name = None

        result = sample_contact.get_primary_name()
        assert result == "test@example.com"

    def test_to_vespa_document(self, sample_contact):
        """Test conversion to Vespa document format."""
        # Set up contact with some data
        sample_contact.add_event("email", datetime.now(timezone.utc))

        vespa_doc = sample_contact.to_vespa_document()

        # Check required fields
        assert (
            vespa_doc["doc_id"]
            == f"contact_{sample_contact.user_id}_{sample_contact.email_address}"
        )
        assert vespa_doc["user_id"] == sample_contact.user_id
        assert vespa_doc["content_type"] == "contact"
        assert vespa_doc["title"] == sample_contact.get_primary_name()
        assert vespa_doc["content"] == sample_contact.notes or ""
        assert (
            vespa_doc["search_text"]
            == f"{sample_contact.get_primary_name()} {sample_contact.email_address}"
        )

        # Check metadata
        metadata = vespa_doc["metadata"]
        assert metadata["email_address"] == sample_contact.email_address
        assert metadata["given_name"] == sample_contact.given_name
        assert metadata["family_name"] == sample_contact.family_name
        assert metadata["relevance_score"] == sample_contact.relevance_score
        assert metadata["source_services"] == sample_contact.source_services


class TestEmailContactEventCount:
    """Test cases for EmailContactEventCount model."""

    def test_event_count_creation(self, sample_event_count):
        """Test EmailContactEventCount creation."""
        assert sample_event_count.event_type == "email"
        assert sample_event_count.count == 5
        assert isinstance(sample_event_count.last_seen, datetime)
        assert isinstance(sample_event_count.first_seen, datetime)

    def test_event_count_defaults(self):
        """Test EmailContactEventCount with minimal fields."""
        event_count = EmailContactEventCount(
            event_type="calendar",
            last_seen=datetime.now(timezone.utc),
            first_seen=datetime.now(timezone.utc),
        )

        assert event_count.count == 0
