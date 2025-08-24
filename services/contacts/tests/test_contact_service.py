"""
Tests for the ContactService class.

Tests contact CRUD operations, search, filtering, and statistics.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from services.contacts.models.contact import Contact
from services.contacts.schemas.contact import ContactCreate, EmailContactUpdate
from services.contacts.services.contact_service import ContactService


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)

    # Create a proper mock for execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_result.scalars.return_value.all.return_value = []

    session.execute = AsyncMock(return_value=mock_result)
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def contact_service():
    """Create a ContactService instance."""
    return ContactService()


@pytest.fixture
def sample_contact_data():
    """Sample contact data for testing."""
    return ContactCreate(
        user_id="test_user_123",
        email_address="test@example.com",
        display_name="Test User",
        given_name="Test",
        family_name="User",
        tags=["test", "example"],
        notes="A test contact",
    )


@pytest.fixture
def sample_contact():
    """Sample Contact model instance."""
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


class TestContactService:
    """Test cases for ContactService."""

    async def test_create_contact_success(
        self, contact_service, mock_session, sample_contact_data
    ):
        """Test successful contact creation."""
        # Mock that no existing contact exists for get_contact_by_email
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Mock the created contact
        created_contact = Contact(
            id="new_contact_123",
            user_id=sample_contact_data.user_id,
            email_address=sample_contact_data.email_address,
            display_name=sample_contact_data.display_name,
            given_name=sample_contact_data.given_name,
            family_name=sample_contact_data.family_name,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            tags=sample_contact_data.tags or [],
            notes=sample_contact_data.notes,
        )

        # Mock session operations
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        # Create contact
        result = await contact_service.create_contact(mock_session, sample_contact_data)

        # Verify result
        assert result is not None
        assert result.user_id == sample_contact_data.user_id
        assert result.email_address == sample_contact_data.email_address.lower()
        assert result.display_name == sample_contact_data.display_name

        # Verify session operations were called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_create_contact_already_exists(
        self, contact_service, mock_session, sample_contact_data
    ):
        """Test contact creation when contact already exists."""
        # Mock that contact already exists
        existing_contact = Contact(
            id="existing_contact_123",
            user_id=sample_contact_data.user_id,
            email_address=sample_contact_data.email_address,
            display_name="Existing User",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            existing_contact
        )

        # Should raise ValidationError
        with pytest.raises(Exception):  # Should raise ValidationError
            await contact_service.create_contact(mock_session, sample_contact_data)

    async def test_get_contact_by_id_success(
        self, contact_service, mock_session, sample_contact
    ):
        """Test successful contact retrieval by ID."""
        # Mock session execute result
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_contact
        )

        # Get contact
        result = await contact_service.get_contact_by_id(
            mock_session, sample_contact.id, sample_contact.user_id
        )

        # Verify result
        assert result is not None
        assert result.id == sample_contact.id
        assert result.email_address == sample_contact.email_address

    async def test_get_contact_by_id_not_found(self, contact_service, mock_session):
        """Test contact retrieval when contact doesn't exist."""
        # Mock session execute result
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Get contact
        result = await contact_service.get_contact_by_id(
            mock_session, "nonexistent_id", "test_user_123"
        )

        # Verify result
        assert result is None

    async def test_get_contact_by_email_success(
        self, contact_service, mock_session, sample_contact
    ):
        """Test successful contact retrieval by email."""
        # Mock session execute result
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_contact
        )

        # Get contact
        result = await contact_service.get_contact_by_email(
            mock_session, sample_contact.user_id, sample_contact.email_address
        )

        # Verify result
        assert result is not None
        assert result.email_address == sample_contact.email_address

    async def test_list_contacts_success(self, contact_service, mock_session):
        """Test successful contact listing."""
        # Create sample contacts
        contacts = [
            Contact(
                id=f"contact_{i}",
                user_id="test_user_123",
                email_address=f"user{i}@example.com",
                display_name=f"User {i}",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        # Mock session execute result
        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            contacts
        )

        # List contacts
        result = await contact_service.list_contacts(
            mock_session, "test_user_123", limit=10, offset=0
        )

        # Verify result
        assert len(result) == 3
        assert all(contact.user_id == "test_user_123" for contact in result)

    async def test_search_contacts_success(self, contact_service, mock_session):
        """Test successful contact search."""
        # Create sample contacts
        contacts = [
            Contact(
                id="contact_123",
                user_id="test_user_123",
                email_address="john@example.com",
                display_name="John Doe",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
            )
        ]

        # Mock session execute result
        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            contacts
        )

        # Search contacts
        result = await contact_service.search_contacts(
            mock_session, "test_user_123", "john", limit=20
        )

        # Verify result
        assert len(result) == 1
        assert result[0].email_address == "john@example.com"

    async def test_update_contact_success(
        self, contact_service, mock_session, sample_contact
    ):
        """Test successful contact update."""
        # Mock session execute result for getting existing contact
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_contact
        )

        # Mock session operations
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        # Update data
        update_data = EmailContactUpdate(
            display_name="Updated Name", notes="Updated notes"
        )

        # Update contact
        result = await contact_service.update_contact(
            mock_session, sample_contact.id, sample_contact.user_id, update_data
        )

        # Verify result
        assert result is not None
        assert result.display_name == "Updated Name"
        assert result.notes == "Updated notes"

        # Verify session operations were called
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_update_contact_not_found(
        self, contact_service, mock_session, sample_contact
    ):
        """Test contact update when contact doesn't exist."""
        # Mock session execute result
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Update data
        update_data = EmailContactUpdate(display_name="Updated Name")

        # Update contact
        result = await contact_service.update_contact(
            mock_session, "nonexistent_id", sample_contact.user_id, update_data
        )

        # Verify result
        assert result is None

    async def test_delete_contact_success(
        self, contact_service, mock_session, sample_contact
    ):
        """Test successful contact deletion."""
        # Mock session execute result for getting existing contact
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            sample_contact
        )

        # Mock session operations
        mock_session.commit.return_value = None

        # Delete contact
        result = await contact_service.delete_contact(
            mock_session, sample_contact.id, sample_contact.user_id
        )

        # Verify result
        assert result is True

        # Verify session operations were called
        mock_session.delete.assert_called_once_with(sample_contact)
        mock_session.commit.assert_called_once()

    async def test_delete_contact_not_found(self, contact_service, mock_session):
        """Test contact deletion when contact doesn't exist."""
        # Mock session execute result
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        # Delete contact
        result = await contact_service.delete_contact(
            mock_session, "nonexistent_id", "test_user_123"
        )

        # Verify result
        assert result is False

    async def test_get_contact_stats_success(self, contact_service, mock_session):
        """Test successful contact statistics retrieval."""
        # Create sample contacts
        contacts = [
            Contact(
                id=f"contact_{i}",
                user_id="test_user_123",
                email_address=f"user{i}@example.com",
                display_name=f"User {i}",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                total_event_count=5,
                source_services=["email_sync", "calendar_sync"],
            )
            for i in range(2)
        ]

        # Mock session execute results for different calls
        # First call: count_contacts (returns 2)
        # Second call: total_events calculation (returns 10)
        # Third call: get contacts for source services (returns contacts list)
        mock_session.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=2)),  # count_contacts
            MagicMock(scalar=MagicMock(return_value=10)),  # total_events
            MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=contacts))
                )
            ),  # source_services
        ]

        # Get stats
        result = await contact_service.get_contact_stats(mock_session, "test_user_123")

        # Verify result
        assert result["total_contacts"] == 2
        assert result["total_events"] == 10
        assert "email_sync" in result["by_service"]
        assert "calendar_sync" in result["by_service"]

    async def test_extract_given_name(self, contact_service):
        """Test given name extraction from full name."""
        assert contact_service._extract_given_name("John Doe") == "John"
        assert contact_service._extract_given_name("John") == "John"
        assert contact_service._extract_given_name("") is None
        assert contact_service._extract_given_name("   ") is None

    async def test_extract_family_name(self, contact_service):
        """Test family name extraction from full name."""
        assert contact_service._extract_family_name("John Doe") == "Doe"
        assert contact_service._extract_family_name("John Doe Smith") == "Doe Smith"
        assert contact_service._extract_family_name("John") is None
        assert contact_service._extract_family_name("") is None
