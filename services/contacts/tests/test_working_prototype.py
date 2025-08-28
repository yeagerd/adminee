"""
Working PostgreSQL test prototype for Contacts Service.

This demonstrates the core functionality without the cleanup issues.
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


class TestWorkingPrototype:
    """Working PostgreSQL test prototype."""

    @classmethod
    def setup_class(cls):
        """Set up test database once for the entire test class."""
        # Get PostgreSQL connection details
        cls.user = os.environ.get("POSTGRES_USER", "postgres")
        cls.password = os.environ.get("POSTGRES_PASSWORD", "postgres")
        cls.host = os.environ.get("POSTGRES_HOST", "localhost")
        cls.port = os.environ.get("POSTGRES_PORT", "5432")

        # Create unique test database name
        cls.db_name = f"testdb_proto_{id(cls)}"

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
    async def test_create_contact_working(self, session: AsyncSession):
        """Test creating a contact - working version."""
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

        # Create a simple contact
        contact = Contact(
            user_id="test_user_123",
            email_address="working@example.com",
            display_name="Working Test User",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            tags=["working", "test"],
        )

        # Add to database
        session.add(contact)
        await session.commit()
        await session.refresh(contact)

        # Verify contact was created
        assert contact.id is not None
        assert contact.email_address == "working@example.com"
        assert contact.display_name == "Working Test User"

        print(f"✅ Contact created successfully with ID: {contact.id}")

        # Note: We skip table cleanup for now to avoid timeout issues
        # In production, you'd want proper cleanup, but this demonstrates the core functionality

    @pytest.mark.asyncio
    async def test_query_contact_working(self, session: AsyncSession):
        """Test querying a contact - working version."""
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

        # Create a contact
        contact = Contact(
            user_id="query_user_456",
            email_address="query@example.com",
            display_name="Query Test User",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            tags=["query", "test"],
        )

        session.add(contact)
        await session.commit()
        await session.refresh(contact)

        # Query the contact
        from sqlmodel import select

        result = await session.execute(
            select(Contact).where(Contact.email_address == "query@example.com")
        )
        queried_contact = result.scalar_one_or_none()

        # Verify the query worked
        assert queried_contact is not None
        assert queried_contact.id == contact.id
        assert queried_contact.email_address == "query@example.com"

        print(f"✅ Contact queried successfully: {queried_contact.display_name}")

        # Note: We skip table cleanup for now to avoid timeout issues
