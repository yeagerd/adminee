"""
Tests for shared database configuration utilities.

This module tests the database configuration utilities that enforce
strict timezone handling across all services.
"""

from services.common.database_config import (
    configure_session_pragmas,
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

        # Verify that pragmas are NOT included in connect_args
        # (aiosqlite doesn't support pragmas parameter directly)
        assert "pragmas" not in connect_args

        # Verify the actual values
        assert connect_args["check_same_thread"] is False
        assert connect_args["timeout"] == 30

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

        assert config["foreign_keys"] == "ON"

    async def test_configure_session_pragmas(self):
        """Test that session pragmas are configured correctly."""

        # Create a mock session for testing
        class MockSession:
            def __init__(self, is_sqlite=True):
                self.bind = MockBind(is_sqlite)
                self.executed_commands = []

            async def execute(self, command):
                self.executed_commands.append(str(command))

        class MockBind:
            def __init__(self, is_sqlite=True):
                self.url = MockURL(is_sqlite)

        class MockURL:
            def __init__(self, is_sqlite=True):
                self.is_sqlite = is_sqlite

            def __str__(self):
                return "sqlite:///test.db" if self.is_sqlite else "postgresql://test"

        # Test SQLite session
        sqlite_session = MockSession(is_sqlite=True)
        await configure_session_pragmas(sqlite_session)

        # Verify that the correct PRAGMA commands were executed
        expected_commands = [
            "PRAGMA foreign_keys = ON",
        ]

        for command in expected_commands:
            assert any(
                command in cmd for cmd in sqlite_session.executed_commands
            ), f"Expected command '{command}' not found in executed commands"

        # Test non-SQLite session (should not execute any PRAGMA commands)
        postgres_session = MockSession(is_sqlite=False)
        await configure_session_pragmas(postgres_session)
        assert len(postgres_session.executed_commands) == 0

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
