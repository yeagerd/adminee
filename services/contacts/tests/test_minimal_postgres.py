"""
Minimal test to verify PostgreSQL testing setup works.
"""

import pytest

from services.common.test_util import PostgresTestDB


class TestMinimalPostgres(PostgresTestDB):
    """Minimal test to verify PostgreSQL setup works."""

    @pytest.mark.asyncio
    async def test_basic_setup(self):
        """Test that basic setup works."""
        # Create the test database
        await self.__class__.create_test_database()

        assert self.__class__._db_name is not None
        assert self.__class__._database_url is not None
        print(f"Database name: {self.__class__._db_name}")
        print(f"Database URL: {self.__class__._database_url}")

    def test_metadata_access(self):
        """Test that metadata can be accessed."""
        # This should work without errors
        assert self.metadata is not None
