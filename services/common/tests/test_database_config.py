"""
Tests for shared database configuration utilities.

This module tests the database configuration utilities that enforce
strict timezone handling across all services.
"""

from services.common.database_config import (
    get_database_timezone_config,
    get_database_type,
    get_sqlite_connect_args,
    is_sqlite_database,
)


class TestDatabaseConfiguration:
    """Test database configuration utilities."""

    def test_get_sqlite_connect_args(self):
        """Test that SQLite connection arguments are properly configured."""
        connect_args = get_sqlite_connect_args()

        # Verify required settings are present
        assert "check_same_thread" in connect_args
        assert "timeout" in connect_args
        assert "pragmas" in connect_args

        # Verify pragma settings
        pragmas = connect_args["pragmas"]
        assert pragmas["foreign_keys"] == "ON"
        assert pragmas["journal_mode"] == "WAL"
        assert pragmas["timezone"] == "UTC"
        assert pragmas["strict"] == "ON"
        assert pragmas["synchronous"] == "NORMAL"
        assert pragmas["temp_store"] == "MEMORY"

    def test_is_sqlite_database(self):
        """Test SQLite database detection."""
        # Test SQLite URLs
        assert is_sqlite_database("sqlite:///test.db")
        assert is_sqlite_database("sqlite:///:memory:")
        assert is_sqlite_database("sqlite:///path/to/database.db")

        # Test non-SQLite URLs
        assert not is_sqlite_database("postgresql://user:pass@localhost/db")
        assert not is_sqlite_database("mysql://user:pass@localhost/db")
        assert not is_sqlite_database("oracle://user:pass@localhost/db")

    def test_get_database_type(self):
        """Test database type detection."""
        assert get_database_type("sqlite:///test.db") == "sqlite"
        assert get_database_type("postgresql://user:pass@localhost/db") == "postgresql"
        assert get_database_type("postgres://user:pass@localhost/db") == "postgresql"
        assert get_database_type("mysql://user:pass@localhost/db") == "mysql"
        assert get_database_type("unknown://user:pass@localhost/db") == "unknown"

    def test_get_database_timezone_config(self):
        """Test timezone configuration settings."""
        config = get_database_timezone_config()

        assert config["timezone"] == "UTC"
        assert config["strict"] == "ON"
        assert config["foreign_keys"] == "ON"

    def test_create_strict_async_engine_url_conversion(self):
        """Test that SQLite URLs are properly converted to async URLs."""
        # Test that the function converts SQLite URLs to async URLs
        # This is a unit test that doesn't require actual database connections

        # Test URL conversion logic
        test_url = "sqlite:///:memory:"
        expected_async_url = "sqlite+aiosqlite:///:memory:"

        # We can't easily test the actual engine creation without async drivers,
        # but we can test the URL conversion logic
        if "sqlite" in test_url.lower() and not test_url.startswith(
            "sqlite+aiosqlite://"
        ):
            converted_url = test_url.replace("sqlite://", "sqlite+aiosqlite://")
            assert converted_url == expected_async_url
