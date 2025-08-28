"""
Final working PostgreSQL test prototype for Contacts Service.

This demonstrates the core functionality with a single, reliable test.
"""

import asyncio
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.contacts.database import metadata
from services.contacts.models.contact import Contact


class TestFinalPrototype:
    """Final working PostgreSQL test prototype."""

    @classmethod
    def setup_class(cls):
        """Set up test database once for the entire test class."""
        # Get PostgreSQL connection details
        cls.user = os.environ.get("POSTGRES_USER", "postgres")
        cls.password = os.environ.get("POSTGRES_PASSWORD", "postgres")
        cls.host = os.environ.get("POSTGRES_HOST", "localhost")
        cls.port = os.environ.get("POSTGRES_PORT", "5432")

        # Create unique test database name
        cls.db_name = f"testdb_final_{id(cls)}"

        # Create the test database
        asyncio.run(cls._create_test_database())

        # Create engine for the test database
        cls.database_url = f"postgresql+asyncpg://{cls.user}:{cls.password}@{cls.host}:{cls.port}/{cls.db_name}"
        cls.engine = create_async_engine(cls.database_url, echo=False, future=True)

        # Create session factory
        cls.session_factory = sessionmaker(
            cls.engine, class_=AsyncSession, expire_on_commit=False
        )

    @classmethod
    def teardown_class(cls):
        """Clean up test database."""
        if hasattr(cls, "engine"):
            asyncio.run(cls.engine.dispose())

        # Drop the test database
        asyncio.run(cls._drop_test_database())

    @classmethod
    async def _create_test_database(cls):
        """Create the test database."""
        try:
            # Connect to default database to create test database
            temp_engine = create_async_engine(
                f"postgresql+asyncpg://{cls.user}:{cls.password}@{cls.host}:{cls.port}/postgres",
                echo=False,
                future=True,
                isolation_level="AUTOCOMMIT",
            )

            async with temp_engine.connect() as conn:
                await conn.execute(text(f"CREATE DATABASE {cls.db_name}"))

            await temp_engine.dispose()

        except Exception as e:
            if "already exists" not in str(e):
                raise

    @classmethod
    async def _drop_test_database(cls):
        """Drop the test database."""
        try:
            # Connect to default database to drop test database
            temp_engine = create_async_engine(
                f"postgresql+asyncpg://{cls.user}:{cls.password}@{cls.host}:{cls.port}/postgres",
                echo=False,
                future=True,
                isolation_level="AUTOCOMMIT",
            )

            async with temp_engine.connect() as conn:
                # Terminate connections and drop database
                await conn.execute(
                    text(
                        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{cls.db_name}'"
                    )
                )
                await conn.execute(text(f"DROP DATABASE IF EXISTS {cls.db_name}"))

            await temp_engine.dispose()

        except Exception:
            pass  # Ignore cleanup errors

    @pytest.fixture
    async def session(self):
        """Provide database session for tests."""
        async with self.session_factory() as session:
            yield session

    @pytest.mark.asyncio
    async def test_contact_crud_operations(self, session: AsyncSession):
        """
        Test complete CRUD operations for contacts in real PostgreSQL database.

        This test demonstrates:
        1. Creating tables from SQLModel metadata
        2. Creating a contact record
        3. Querying the contact record
        4. Updating the contact record
        5. Deleting the contact record

        All operations use the real database, not mocks.
        """
        # Create tables from the contacts service metadata
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

        try:
            # 1. CREATE - Create a contact
            contact = Contact(
                user_id="prototype_user_123",
                email_address="prototype@example.com",
                display_name="Prototype Test User",
                given_name="Prototype",
                family_name="User",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                tags=["prototype", "test", "postgres"],
                notes="This is a test contact for the PostgreSQL prototype",
            )

            # Add to database and commit
            session.add(contact)
            await session.commit()
            await session.refresh(contact)

            # Verify contact was created
            assert contact.id is not None
            assert contact.email_address == "prototype@example.com"
            assert contact.display_name == "Prototype Test User"
            assert contact.tags == ["prototype", "test", "postgres"]

            print(f"✅ Contact created successfully with ID: {contact.id}")

            # 2. READ - Query the contact
            from sqlmodel import select

            result = await session.execute(
                select(Contact).where(Contact.email_address == "prototype@example.com")
            )
            queried_contact = result.scalar_one_or_none()

            # Verify the query worked
            assert queried_contact is not None
            assert queried_contact.id == contact.id
            assert queried_contact.email_address == "prototype@example.com"
            assert queried_contact.display_name == "Prototype Test User"

            print(f"✅ Contact queried successfully: {queried_contact.display_name}")

            # 3. UPDATE - Update the contact
            original_tags = queried_contact.tags.copy()
            queried_contact.display_name = "Updated Prototype User"
            # Create a new tags list instead of modifying the existing one
            queried_contact.tags = original_tags + ["updated"]
            queried_contact.notes = "This contact has been updated"

            await session.commit()
            await session.refresh(queried_contact)

            # Verify the update worked
            assert queried_contact.display_name == "Updated Prototype User"
            assert "updated" in queried_contact.tags
            assert queried_contact.notes == "This contact has been updated"

            print(f"✅ Contact updated successfully: {queried_contact.display_name}")
            print(f"✅ Tags updated: {queried_contact.tags}")

            # 4. DELETE - Delete the contact
            contact_id = queried_contact.id
            await session.delete(queried_contact)
            await session.commit()

            # Verify the contact was deleted
            result = await session.execute(
                select(Contact).where(Contact.id == contact_id)
            )
            deleted_contact = result.scalar_one_or_none()
            assert deleted_contact is None

            print(f"✅ Contact deleted successfully")

            print("🎉 All CRUD operations completed successfully!")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise

        # Note: We skip table cleanup to avoid timeout issues
        # In production, you'd want proper cleanup, but this demonstrates the core functionality
