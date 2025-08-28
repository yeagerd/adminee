"""
Integration tests for ContactService using real PostgreSQL database.

This test file demonstrates how to use gocept.testdb to test the ContactService
with a real PostgreSQL database instead of mocks.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from services.common.test_util import PostgresTestDB
from services.contacts.database import metadata
from services.contacts.models.contact import Contact
from services.contacts.services.contact_service import ContactService

# Module-level database name for consistency
_db_name = None


def setup_module():
    """Set up module-level test database name."""
    global _db_name
    # Create a unique database name for this test module
    import uuid

    _db_name = f"test_contact_service_{uuid.uuid4().hex[:8]}"


def teardown_module():
    """Clean up module-level test database."""
    global _db_name
    if _db_name:
        # Clean up database - create a temporary instance just for cleanup
        cleanup_db = PostgresTestDB()
        cleanup_db._db_name = _db_name
        cleanup_db.teardown_class()


@pytest.fixture
async def test_db():
    """Create a fresh database instance for each test."""
    # Create a new PostgresTestDB instance for this test
    db = PostgresTestDB()
    db.metadata = metadata
    db._db_name = _db_name

    # Setup the database connection within the current event loop
    db.setup_class()

    # Ensure the test database exists
    await db.create_test_database()

    yield db

    # Cleanup: dispose of the engine to close connections
    if hasattr(db, "_engine") and db._engine:
        await db._engine.dispose()


@pytest.fixture
async def session(test_db):
    """Provide database session for tests."""
    # Create tables for this test
    await test_db.create_tables()

    try:
        # Provide session
        async with test_db.get_session() as session:
            yield session
    finally:
        # Drop tables after test
        await test_db.drop_tables()


class TestContactServicePostgres:
    """Test ContactService with real PostgreSQL database."""

    @pytest.fixture
    def contact_service(self):
        """Create ContactService instance."""
        return ContactService()

    @pytest.fixture
    def sample_contact_data(self):
        """Sample contact data for testing."""
        return {
            "user_id": "test_user_123",
            "email_address": "test@example.com",
            "display_name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "tags": ["test", "example"],
            "notes": "A test contact",
        }

    @pytest.mark.asyncio
    async def test_create_contact_real_database(
        self,
        session: AsyncSession,
        contact_service: ContactService,
        sample_contact_data: dict,
    ):
        """Test creating a contact in the real database."""
        # Create contact data
        contact = Contact(
            user_id=sample_contact_data["user_id"],
            email_address=sample_contact_data["email_address"],
            display_name=sample_contact_data["display_name"],
            given_name=sample_contact_data["given_name"],
            family_name=sample_contact_data["family_name"],
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            tags=sample_contact_data["tags"],
            notes=sample_contact_data["notes"],
        )

        # Add to database
        session.add(contact)
        await session.commit()
        await session.refresh(contact)

        # Verify contact was created
        assert contact.id is not None
        assert contact.user_id == sample_contact_data["user_id"]
        assert contact.email_address == sample_contact_data["email_address"]
        assert contact.display_name == sample_contact_data["display_name"]

        # Query from database to verify persistence
        result = await session.execute(
            select(Contact).where(
                Contact.email_address == sample_contact_data["email_address"]
            )
        )
        db_contact = result.scalar_one_or_none()

        assert db_contact is not None
        assert db_contact.id == contact.id
        assert db_contact.email_address == sample_contact_data["email_address"]

    @pytest.mark.asyncio
    async def test_get_contact_by_email_real_database(
        self,
        session: AsyncSession,
        contact_service: ContactService,
        sample_contact_data: dict,
    ):
        """Test retrieving a contact by email from the real database."""
        # Create and save a contact
        contact = Contact(
            user_id=sample_contact_data["user_id"],
            email_address=sample_contact_data["email_address"],
            display_name=sample_contact_data["display_name"],
            given_name=sample_contact_data["given_name"],
            family_name=sample_contact_data["family_name"],
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            tags=sample_contact_data["tags"],
            notes=sample_contact_data["notes"],
        )

        session.add(contact)
        await session.commit()
        await session.refresh(contact)

        # Test the service method with real database
        retrieved_contact = await contact_service.get_contact_by_email(
            session,
            sample_contact_data["user_id"],
            sample_contact_data["email_address"],
        )

        # Verify the contact was retrieved correctly
        assert retrieved_contact is not None
        assert retrieved_contact.id == contact.id
        assert retrieved_contact.email_address == sample_contact_data["email_address"]
        assert retrieved_contact.display_name == sample_contact_data["display_name"]

    @pytest.mark.asyncio
    async def test_update_contact_real_database(
        self,
        session: AsyncSession,
        contact_service: ContactService,
        sample_contact_data: dict,
    ):
        """Test updating a contact in the real database."""
        # Create test data
        # Create initial contact
        contact = Contact(
            user_id=sample_contact_data["user_id"],
            email_address=sample_contact_data["email_address"],
            display_name=sample_contact_data["display_name"],
            given_name=sample_contact_data["given_name"],
            family_name=sample_contact_data["family_name"],
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            tags=sample_contact_data["tags"],
            notes=sample_contact_data["notes"],
        )

        session.add(contact)
        await session.commit()
        await session.refresh(contact)

        # Update the contact
        new_display_name = "Updated Test User"
        contact.display_name = new_display_name
        contact.notes = "Updated notes"

        await session.commit()
        await session.refresh(contact)

        # Verify the update
        assert contact.display_name == new_display_name
        assert contact.notes == "Updated notes"

        # Query from database to verify persistence
        result = await session.execute(select(Contact).where(Contact.id == contact.id))
        updated_contact = result.scalar_one_or_none()

        assert updated_contact is not None
        assert updated_contact.display_name == new_display_name
        assert updated_contact.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_delete_contact_real_database(
        self,
        session: AsyncSession,
        contact_service: ContactService,
        sample_contact_data: dict,
    ):
        """Test deleting a contact from the real database."""
        # Create test data
        # Create a contact
        contact = Contact(
            user_id=sample_contact_data["user_id"],
            email_address=sample_contact_data["email_address"],
            display_name=sample_contact_data["display_name"],
            given_name=sample_contact_data["given_name"],
            family_name=sample_contact_data["family_name"],
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            tags=sample_contact_data["tags"],
            notes=sample_contact_data["notes"],
        )

        session.add(contact)
        await session.commit()
        await session.refresh(contact)

        contact_id = contact.id
        assert contact_id is not None

        # Delete the contact
        await session.delete(contact)
        await session.commit()

        # Verify the contact was deleted
        result = await session.execute(select(Contact).where(Contact.id == contact_id))
        deleted_contact = result.scalar_one_or_none()

        assert deleted_contact is None

    @pytest.mark.asyncio
    async def test_contact_search_real_database(
        self, session: AsyncSession, contact_service: ContactService
    ):
        """Test searching contacts in the real database."""
        # Create test data
        # Create multiple contacts
        contacts_data = [
            {
                "user_id": "user1",
                "email_address": "alice@example.com",
                "display_name": "Alice Smith",
                "given_name": "Alice",
                "family_name": "Smith",
                "tags": ["work", "colleague"],
            },
            {
                "user_id": "user2",
                "email_address": "bob@example.com",
                "display_name": "Bob Johnson",
                "given_name": "Bob",
                "family_name": "Johnson",
                "tags": ["personal", "friend"],
            },
            {
                "user_id": "user3",
                "email_address": "charlie@example.com",
                "display_name": "Charlie Brown",
                "given_name": "Charlie",
                "family_name": "Brown",
                "tags": ["work", "manager"],
            },
        ]

        for data in contacts_data:
            contact = Contact(
                user_id=data["user_id"],
                email_address=data["email_address"],
                display_name=data["display_name"],
                given_name=data["given_name"],
                family_name=data["family_name"],
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                tags=data["tags"],
            )
            session.add(contact)

        await session.commit()

        # Search for contacts with "work" tag
        result = await session.execute(
            select(Contact).where(Contact.tags.contains(["work"]))
        )
        work_contacts = result.scalars().all()

        assert len(work_contacts) == 2
        work_emails = {c.email_address for c in work_contacts}
        assert "alice@example.com" in work_emails
        assert "charlie@example.com" in work_emails

        # Search by display name
        result = await session.execute(
            select(Contact).where(Contact.display_name.contains("Alice"))
        )
        alice_contacts = result.scalars().all()

        assert len(alice_contacts) == 1
        assert alice_contacts[0].email_address == "alice@example.com"
