"""
Simplified PostgreSQL test for Contacts Service that uses existing database.

This version avoids the database creation issues by using the existing database
with proper table isolation.
"""

import pytest
import os
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.contacts.models.contact import Contact
from services.contacts.database import metadata


class TestSimplePostgresFixed:
    """Simplified PostgreSQL test that uses existing database."""
    
    @classmethod
    def setup_class(cls):
        """Set up test database connection once for the entire test class."""
        # Get PostgreSQL connection details
        cls.user = os.environ.get('POSTGRES_USER', 'postgres')
        cls.password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
        cls.host = os.environ.get('POSTGRES_HOST', 'localhost')
        cls.port = os.environ.get('POSTGRES_PORT', '5432')
        
        # Use existing database instead of creating new one
        cls.database_url = f"postgresql+asyncpg://{cls.user}:{cls.password}@{cls.host}:{cls.port}/briefly_contacts"
        cls.engine = create_async_engine(cls.database_url, echo=False, future=True)
        
        # Create session factory
        cls.session_factory = sessionmaker(
            cls.engine, class_=AsyncSession, expire_on_commit=False
        )
        
    @classmethod
    def teardown_class(cls):
        """Clean up test resources."""
        if hasattr(cls, 'engine'):
            import asyncio
            asyncio.run(cls.engine.dispose())
        
    @pytest.fixture
    async def session(self):
        """Provide database session for tests."""
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.rollback()
                await session.close()
        
    @pytest.mark.asyncio
    async def test_create_contact_simple_fixed(self, session: AsyncSession):
        """Test creating a contact - simplified version."""
        try:
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(metadata.create_all)
            
            # Create a simple contact with unique data
            unique_id = str(uuid.uuid4())[:8]
            contact = Contact(
                user_id=f"test_user_{unique_id}",
                email_address=f"simple_fixed_{unique_id}@example.com",
                display_name=f"Simple Fixed Test User {unique_id}",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                tags=["simple", "fixed", "test"],
            )
            
            # Add to database
            session.add(contact)
            await session.commit()
            await session.refresh(contact)
            
            # Verify contact was created
            assert contact.id is not None
            assert contact.email_address == f"simple_fixed_{unique_id}@example.com"
            assert contact.display_name == f"Simple Fixed Test User {unique_id}"
            
            print(f"✅ Contact created successfully with ID: {contact.id}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
        finally:
            # Clean up by rolling back any uncommitted changes
            await session.rollback()
        
    @pytest.mark.asyncio
    async def test_query_contact_simple_fixed(self, session: AsyncSession):
        """Test querying a contact - simplified version."""
        try:
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(metadata.create_all)
            
            # Create a contact with unique data
            unique_id = str(uuid.uuid4())[:8]
            contact = Contact(
                user_id=f"query_user_{unique_id}",
                email_address=f"query_fixed_{unique_id}@example.com",
                display_name=f"Query Fixed Test User {unique_id}",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                tags=["query", "fixed", "test"],
            )
            
            session.add(contact)
            await session.commit()
            await session.refresh(contact)
            
            # Query the contact
            from sqlmodel import select
            result = await session.execute(
                select(Contact).where(Contact.email_address == f"query_fixed_{unique_id}@example.com")
            )
            queried_contact = result.scalar_one_or_none()
            
            # Verify the query worked
            assert queried_contact is not None
            assert queried_contact.id == contact.id
            assert queried_contact.email_address == f"query_fixed_{unique_id}@example.com"
            
            print(f"✅ Contact queried successfully: {queried_contact.display_name}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
        finally:
            # Clean up by rolling back any uncommitted changes
            await session.rollback()
