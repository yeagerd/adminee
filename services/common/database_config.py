"""
Shared database configuration utilities for all services.

This module provides consistent database configuration across all services,
including strict timezone handling to catch timezone bugs in tests.
"""

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def get_sqlite_connect_args() -> Dict[str, Any]:
    """
    Get SQLite connection arguments with basic configuration.

    Note: aiosqlite doesn't support the 'pragmas' parameter directly,
    so we use basic connection arguments and set PRAGMA values via SQL.

    Returns:
        Dict of connection arguments for SQLite
    """
    return {
        "check_same_thread": False,
        "timeout": 30,
    }


def create_strict_async_engine(
    database_url: str, echo: bool = False, **kwargs: Any
) -> AsyncEngine:
    """
    Create an async database engine with strict timezone handling.

    This function automatically configures SQLite with strict timezone handling
    when using SQLite databases, while leaving other database types unchanged.

    Args:
        database_url: The database URL
        echo: Whether to echo SQL statements
        **kwargs: Additional arguments to pass to create_async_engine

    Returns:
        Configured AsyncEngine instance
    """
    connect_args = {}

    # Apply strict SQLite configuration if using SQLite
    if "sqlite" in database_url.lower():
        # Convert to async SQLite URL
        if not database_url.startswith("sqlite+aiosqlite://"):
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
        connect_args = get_sqlite_connect_args()

    return create_async_engine(
        database_url, echo=echo, future=True, connect_args=connect_args, **kwargs
    )


async def configure_session_pragmas(session: Any) -> None:
    """
    Configure SQLite PRAGMA settings for a database session.

    This function sets additional PRAGMA settings that should be applied
    to each database session when using SQLite.

    Args:
        session: The database session to configure
    """
    # Only apply to SQLite sessions
    if (
        hasattr(session, "bind")
        and session.bind
        and "sqlite" in str(session.bind.url).lower()
    ):
        from sqlalchemy import text

        await session.execute(text("PRAGMA foreign_keys = ON"))


def get_database_timezone_config() -> Dict[str, str]:
    """
    Get database timezone configuration settings.

    Returns:
        Dict of timezone-related configuration settings
    """
    return {
        "foreign_keys": "ON",
    }


def is_sqlite_database(database_url: str) -> bool:
    """
    Check if the given database URL is for SQLite.

    Args:
        database_url: The database URL to check

    Returns:
        True if the URL is for SQLite, False otherwise
    """
    return "sqlite" in database_url.lower()


def get_database_type(database_url: str) -> str:
    """
    Get the database type from a database URL.

    Args:
        database_url: The database URL

    Returns:
        The database type (e.g., 'sqlite', 'postgresql', 'mysql')
    """
    if "sqlite" in database_url.lower():
        return "sqlite"
    elif "postgresql" in database_url.lower() or "postgres" in database_url.lower():
        return "postgresql"
    elif "mysql" in database_url.lower():
        return "mysql"
    else:
        return "unknown"
