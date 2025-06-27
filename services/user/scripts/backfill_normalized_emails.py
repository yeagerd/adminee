#!/usr/bin/env python3
"""
Script to backfill normalized_email field for existing users.

This script should be run after the database migration that adds the normalized_email column.
It will populate the normalized_email field for all existing users using the email-normalize library.
"""

import asyncio
import logging

from sqlalchemy import select

from services.user.database import get_async_session
from services.user.models.user import User
from services.user.utils.email_collision import EmailCollisionDetector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_normalized_emails(batch_size: int = 100) -> None:
    """
    Backfill normalized_email for existing users.

    Args:
        batch_size: Number of users to process in each batch
    """
    detector = EmailCollisionDetector()
    async_session = get_async_session()

    async with async_session() as session:
        # Get total count of users
        total_result = await session.execute(select(User))
        total_users = len(total_result.scalars().all())
        logger.info(f"Found {total_users} users to process")

        # Process users in batches
        offset = 0
        processed = 0
        errors = 0

        while offset < total_users:
            # Get batch of users
            result = await session.execute(
                select(User)
                .where(
                    User.normalized_email.is_(None)
                )  # Only process users without normalized_email
                .limit(batch_size)
                .offset(offset)
            )
            users = result.scalars().all()

            if not users:
                break

            logger.info(f"Processing batch of {len(users)} users (offset: {offset})")

            for user in users:
                try:
                    # Normalize the email
                    normalized_email = await detector.normalize_email_async(user.email)
                    user.normalized_email = normalized_email
                    processed += 1

                    if processed % 10 == 0:
                        logger.info(f"Processed {processed} users...")

                except Exception as e:
                    logger.error(
                        f"Failed to normalize email for user {user.id} ({user.email}): {e}"
                    )
                    errors += 1
                    # Set a fallback value
                    user.normalized_email = user.email.lower()

            # Commit the batch
            await session.commit()
            offset += batch_size

        logger.info(f"Backfill completed. Processed: {processed}, Errors: {errors}")


async def verify_backfill() -> None:
    """Verify that all users have normalized_email populated."""
    async_session = get_async_session()

    async with async_session() as session:
        # Count users without normalized_email
        result = await session.execute(
            select(User).where(User.normalized_email.is_(None))
        )
        users_without_normalized = len(result.scalars().all())

        # Count total users
        total_result = await session.execute(select(User))
        total_users = len(total_result.scalars().all())

        logger.info(
            f"Verification: {total_users - users_without_normalized}/{total_users} users have normalized_email"
        )

        if users_without_normalized > 0:
            logger.warning(
                f"{users_without_normalized} users still missing normalized_email"
            )
        else:
            logger.info("All users have normalized_email populated!")


async def main():
    """Main function to run the backfill."""
    logger.info("Starting normalized_email backfill...")

    try:
        await backfill_normalized_emails()
        await verify_backfill()
        logger.info("Backfill completed successfully!")
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
