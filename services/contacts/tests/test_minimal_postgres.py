"""
Minimal test to verify PostgreSQL testing setup works.
"""

import asyncio

import pytest

from services.common.test_util import PostgresTestDB
from services.contacts.database import metadata


class TestMinimalPostgres(PostgresTestDB):
    """Minimal test to verify PostgreSQL setup works."""

    @classmethod
    def setup_class(cls):
        """Set up test database and create tables."""
        super().setup_class()
        cls.metadata = metadata
        # Create the test database once for the entire test class
        asyncio.run(cls.create_test_database())

    @classmethod
    def teardown_class(cls):
        """Clean up test database."""
        super().teardown_class()

    async def async_setup(self):
        """Async setup - create tables."""
        await self.create_tables()

    async def async_teardown(self):
        """Async teardown - drop tables."""
        await self.drop_tables()

    @pytest.mark.asyncio
    async def test_basic_setup(self):
        """Test that basic setup works."""
        # Setup tables for this test
        await self.async_setup()

        try:
            # Database should already be created by setup_class
            assert self.__class__._db_name is not None
            assert self.__class__._database_url is not None
            print(f"Database name: {self.__class__._db_name}")
            print(f"Database URL: {self.__class__._database_url}")

        finally:
            await self.async_teardown()

    def test_metadata_access(self):
        """Test that metadata can be accessed."""
        # This should work without errors
        assert self.metadata is not None
