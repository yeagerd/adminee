#!/usr/bin/env python3
"""Check database schema and add missing columns if needed."""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.user.database import get_async_session
from sqlalchemy import text


async def check_and_fix_schema() -> None:
    """Check if required columns exist and add them if missing."""
    async_session = get_async_session()
    async with async_session() as session:
        # Check users table columns
        result = await session.execute(text("PRAGMA table_info(users)"))
        user_columns = [row[1] for row in result.fetchall()]
        print(f"Users table columns: {user_columns}")

        if "normalized_email" not in user_columns:
            print("Adding normalized_email column to users table...")
            try:
                await session.execute(
                    text("ALTER TABLE users ADD COLUMN normalized_email VARCHAR(255)")
                )
                await session.commit()
                print("Successfully added normalized_email column to users table")
            except Exception as e:
                print(f"Error adding normalized_email column: {e}")
                await session.rollback()

        # Check user_preferences table columns
        result = await session.execute(text("PRAGMA table_info(user_preferences)"))
        pref_columns = [row[1] for row in result.fetchall()]
        print(f"User preferences table columns: {pref_columns}")

        if "timezone" not in pref_columns:
            print("Adding timezone column to user_preferences table...")
            try:
                await session.execute(
                    text(
                        'ALTER TABLE user_preferences ADD COLUMN timezone VARCHAR(50) DEFAULT "UTC"'
                    )
                )
                await session.commit()
                print("Successfully added timezone column to user_preferences table")
            except Exception as e:
                print(f"Error adding timezone column: {e}")
                await session.rollback()


if __name__ == "__main__":
    asyncio.run(check_and_fix_schema())
