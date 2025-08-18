#!/usr/bin/env python3
"""
Email crawling logic for backfill functionality
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from services.common.logging_config import get_logger

logger = get_logger(__name__)


class EmailCrawler:
    """Crawls emails from email providers for backfill operations"""

    def __init__(self, user_id: str, provider: str, max_email_count: int = 10):
        self.user_id = user_id
        self.provider = provider
        self.max_email_count = max_email_count  # Add max email count parameter
        self.rate_limit_delay = 1.0  # Default 1 second between batches

    async def get_total_email_count(self) -> int:
        """Get the total number of emails to process"""
        try:
            if self.provider == "microsoft":
                return await self._get_microsoft_email_count()
            elif self.provider == "google":
                return await self._get_google_email_count()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to get email count for user {self.user_id}: {e}")
            raise

    async def crawl_emails(
        self,
        batch_size: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        folders: Optional[List[str]] = None,
        resume_from: int = 0,
        max_emails: Optional[int] = None,
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Crawl emails in batches with optional maximum limit"""
        try:
            total_processed = 0

            if self.provider == "microsoft":
                async for batch in self._crawl_microsoft_emails(
                    batch_size, start_date, end_date, folders, resume_from
                ):
                    # Check if we've reached the max_emails limit
                    if max_emails and total_processed >= max_emails:
                        break

                    # Limit batch size if it would exceed max_emails
                    if max_emails and total_processed + len(batch) > max_emails:
                        remaining = max_emails - total_processed
                        batch = batch[:remaining]

                    yield batch
                    total_processed += len(batch)

                    # Check if we've reached the limit after this batch
                    if max_emails and total_processed >= max_emails:
                        break

            elif self.provider == "google":
                async for batch in self._crawl_google_emails(
                    batch_size, start_date, end_date, folders, resume_from
                ):
                    # Check if we've reached the max_emails limit
                    if max_emails and total_processed >= max_emails:
                        break

                    # Limit batch size if it would exceed max_emails
                    if max_emails and total_processed + len(batch) > max_emails:
                        remaining = max_emails - total_processed
                        batch = batch[:remaining]

                    yield batch
                    total_processed += len(batch)

                    # Check if we've reached the limit after this batch
                    if max_emails and total_processed >= max_emails:
                        break
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            logger.error(f"Failed to crawl emails for user {self.user_id}: {e}")
            raise

    async def _get_microsoft_email_count(self) -> int:
        """Get email count from Microsoft Graph API"""
        # This would integrate with the existing Microsoft Graph client
        # For now, return a placeholder count
        logger.info(
            f"Getting Microsoft email count for user {self.user_id}",
            extra={
                "user_id": self.user_id,
                "provider": self.provider,
                "operation": "email_count",
            },
        )

        # Simulate API call delay
        await asyncio.sleep(0.1)

        # Placeholder: in real implementation, this would query Microsoft Graph
        # from ..clients.microsoft_graph import MicrosoftGraphClient
        # client = MicrosoftGraphClient(self.user_id)
        # return await client.get_email_count()

        return self.max_email_count  # Use parameter instead of hardcoded value

    async def _get_google_email_count(self) -> int:
        """Get email count from Gmail API"""
        # This would integrate with the existing Gmail client
        # For now, return a placeholder count
        logger.info(f"Getting Gmail email count for user {self.user_id}")

        # Simulate API call delay
        await asyncio.sleep(0.1)

        # Placeholder: in real implementation, this would query Gmail API
        # from ..clients.gmail import GmailClient
        # client = GmailClient(self.user_id)
        # return await client.get_email_count()

        return self.max_email_count  # Use parameter instead of hardcoded value

    async def _crawl_microsoft_emails(
        self,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]],
        resume_from: int,
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Crawl emails from Microsoft Graph API"""
        logger.info(
            f"Starting Microsoft email crawl for user {self.user_id}",
            extra={
                "user_id": self.user_id,
                "provider": self.provider,
                "operation": "email_crawl",
                "batch_size": batch_size,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        # Calculate total batches
        total_emails = await self._get_microsoft_email_count()
        total_batches = (total_emails + batch_size - 1) // batch_size

        # Skip completed batches
        start_batch = resume_from // batch_size

        for batch_num in range(start_batch, total_batches):
            try:
                # Get batch of emails
                emails = await self._get_microsoft_email_batch(
                    batch_num, batch_size, start_date, end_date, folders
                )

                # Apply rate limiting
                if batch_num > start_batch:
                    await asyncio.sleep(self.rate_limit_delay)

                yield emails

                logger.debug(
                    f"Processed Microsoft email batch {batch_num + 1}/{total_batches}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to process Microsoft email batch {batch_num}: {e}"
                )
                # Continue with next batch
                continue

    async def _crawl_google_emails(
        self,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]],
        resume_from: int,
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Crawl emails from Gmail API"""
        logger.info(f"Starting Gmail email crawl for user {self.user_id}")

        # Calculate total batches
        total_emails = await self._get_google_email_count()
        total_batches = (total_emails + batch_size - 1) // batch_size

        # Skip completed batches
        start_batch = resume_from // batch_size

        for batch_num in range(start_batch, total_batches):
            try:
                # Get batch of emails
                emails = await self._get_gmail_email_batch(
                    batch_num, batch_size, start_date, end_date, folders
                )

                # Apply rate limiting
                if batch_num > start_batch:
                    await asyncio.sleep(self.rate_limit_delay)

                yield emails

                logger.debug(
                    f"Processed Gmail email batch {batch_num + 1}/{total_batches}"
                )

            except Exception as e:
                logger.error(f"Failed to process Gmail email batch {batch_num}: {e}")
                # Continue with next batch
                continue

    async def _get_email_batch(
        self,
        provider: str,
        batch_num: int,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Get a batch of emails from the specified provider using the office service's unified API"""
        try:
            import httpx

            # Call the office service's unified /email/messages endpoint
            # This is the same endpoint the frontend uses
            office_service_url = "http://localhost:8003"

            # Build query parameters
            params = {
                "providers": [provider],
                "limit": batch_size,
                "include_body": True,
                "no_cache": True,  # Always get fresh data for backfill
            }

            # Add folder filtering if specified
            if folders:
                # For both providers, folders are typically labels
                params["labels"] = folders

            # Add date filtering if specified
            if start_date or end_date:
                # Build search query with date filters
                query_parts = []
                if start_date:
                    query_parts.append(f"after:{start_date.strftime('%Y/%m/%d')}")
                if end_date:
                    query_parts.append(f"before:{end_date.strftime('%Y/%m/%d')}")
                if query_parts:
                    params["q"] = " ".join(query_parts)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{office_service_url}/v1/email/messages",
                    params=params,
                    headers={
                        "X-User-Id": self.user_id,
                        "X-API-Key": "test-BACKFILL-OFFICE-KEY",  # Use backfill API key
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("data", {}).get("messages"):
                        # The office service already provides normalized data - convert to backfill format
                        emails = []
                        for msg in data["data"]["messages"]:
                            # Convert normalized EmailMessage to backfill format
                            email = {
                                "id": msg.get("provider_message_id", msg.get("id")),
                                "user_id": self.user_id,
                                "provider": provider,
                                "type": "email",
                                "subject": msg.get("subject", ""),
                                "body": msg.get("body_text", msg.get("snippet", "")),
                                "from": (
                                    msg.get("from_address", {}).get("email", "")
                                    if msg.get("from_address")
                                    else ""
                                ),
                                "to": [
                                    addr.get("email", "")
                                    for addr in msg.get("to_addresses", [])
                                ],
                                "thread_id": msg.get("thread_id", ""),
                                "folder": (
                                    msg.get("labels", ["inbox"])[0]
                                    if msg.get("labels")
                                    else "inbox"
                                ),
                                "created_at": msg.get("date"),
                                "updated_at": msg.get("date"),
                                "metadata": {
                                    "has_attachments": msg.get(
                                        "has_attachments", False
                                    ),
                                    "is_read": msg.get("is_read", True),
                                },
                            }
                            emails.append(email)

                        logger.info(
                            f"Retrieved {len(emails)} real emails from {provider} using office service unified API"
                        )
                        return emails
                    else:
                        logger.warning("Office service returned no emails or error")
                        if not data.get("success"):
                            logger.error(
                                f"Office service error: {data.get('error', 'Unknown error')}"
                            )
                        return []
                else:
                    logger.error(
                        f"Office service returned status {response.status_code}: {response.text}"
                    )
                    return []

        except Exception as e:
            logger.error(
                f"Failed to get real emails from office service unified API for {provider}: {e}"
            )
            logger.error("This could be due to:")
            logger.error("1. Office service not running")
            logger.error("2. Invalid API key")
            logger.error("3. Network connectivity issues")
            logger.error("4. Office service internal errors")
            raise Exception(
                f"Failed to retrieve real emails from {provider} via office service: {e}"
            )

        # Return empty list if no emails found
        return []

    async def _get_microsoft_email_batch(
        self,
        batch_num: int,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Get a batch of emails from Microsoft using the office service's unified API"""
        return await self._get_email_batch(
            "microsoft", batch_num, batch_size, start_date, end_date, folders
        )

    async def _get_gmail_email_batch(
        self,
        batch_num: int,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Get a batch of emails from Gmail using the office service's unified API"""
        return await self._get_email_batch(
            "google", batch_num, batch_size, start_date, end_date, folders
        )

    # Note: Normalization methods removed - we now use the already-normalized data
    # from the office service's /v1/email/messages endpoint

    def set_rate_limit(self, emails_per_second: int):
        """Set the rate limit for email crawling"""
        if emails_per_second > 0:
            self.rate_limit_delay = 1.0 / emails_per_second
        else:
            self.rate_limit_delay = 0.0

        logger.info(f"Set email crawl rate limit to {emails_per_second} emails/second")
