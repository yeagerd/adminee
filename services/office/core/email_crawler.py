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

    def __init__(self, user_id: str, provider: str, user_email: str, max_email_count: int = 10):
        self.user_id = user_id
        self.provider = provider
        self.user_email = user_email  # Add user_email for normalizer calls
        self.max_email_count = max_email_count  # Add max email count parameter
        self.rate_limit_delay = 1.0  # Default 1 second between batches

    async def get_total_email_count(self) -> int:
        """Get the total number of emails to process"""
        try:
            # Use the unified email count method
            return await self._get_email_count()

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
            async for batch in self._crawl_emails(
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

        except Exception as e:
            logger.error(f"Failed to crawl emails for user {self.user_id}: {e}")
            raise


    async def _get_email_count(self) -> int:
        """Get email count from the specified provider using the office service's unified API"""
        try:
            import httpx

            # Call the office service's internal /internal/messages/count endpoint
            office_service_url = "http://localhost:8003"

            # Ensure provider is a lowercase string - handle both enum and string cases
            if hasattr(self.provider, 'value'):
                # It's an enum, get the value
                provider_str = self.provider.value.lower()
            else:
                # It's already a string
                provider_str = str(self.provider).lower()

            # Build query parameters for count
            params = {
                "user_id": self.user_id,
                "providers": [provider_str],
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{office_service_url}/internal/messages/count",
                    params=params,
                    headers={
                        "X-API-Key": "test-BACKFILL-OFFICE-KEY",  # Use backfill API key
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    count = data.get("total_count", 0)
                    logger.info(
                        f"Got email count for user {self.user_id} with provider {provider_str}: {count}",
                        extra={
                            "user_id": self.user_id,
                            "provider": provider_str,
                            "operation": "email_count",
                            "count": count,
                        },
                    )
                    return min(count, self.max_email_count)  # Respect max_email_count limit
                else:
                    logger.warning(
                        f"Failed to get email count: {response.status_code} - {response.text}"
                    )
                    return 0  # Return 0 instead of max_email_count to avoid false positives

        except Exception as e:
            logger.error(f"Error getting email count: {e}")
            return 0  # Return 0 instead of max_email_count to avoid false positives

    async def _crawl_emails(
        self,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]],
        resume_from: int,
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Crawl emails from the specified provider"""
        logger.info(
            f"Starting email crawl for user {self.user_id} with provider {self.provider}",
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
        total_emails = await self._get_email_count()
        total_batches = (total_emails + batch_size - 1) // batch_size

        # Skip completed batches
        start_batch = resume_from // batch_size

        for batch_num in range(start_batch, total_batches):
            try:
                # Get batch of emails
                emails = await self._get_email_batch(
                    self.provider, batch_num, batch_size, start_date, end_date, folders
                )

                # Apply rate limiting
                if batch_num > start_batch:
                    await asyncio.sleep(self.rate_limit_delay)

                yield emails

                logger.debug(
                    f"Processed email batch {batch_num + 1}/{total_batches} for provider {self.provider}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to process email batch {batch_num} for provider {self.provider}: {e}"
                )
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

            # Call the office service's internal /internal/messages endpoint
            # This is the same endpoint the frontend uses
            office_service_url = "http://localhost:8003"

            # Ensure provider is a lowercase string - handle both enum and string cases
            if hasattr(provider, 'value'):
                # It's an enum, get the value
                provider_str = provider.value.lower()
            else:
                # It's already a string
                provider_str = str(provider).lower()

            # Build query parameters
            params = {
                "user_id": self.user_id,  # Pass user_id as query parameter for internal endpoint
                "email": self.user_email,  # Pass email for normalizer
                "providers": [provider_str],
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
                    f"{office_service_url}/internal/messages",
                    params=params,
                    headers={
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
                            # Use content splitting to separate visible from quoted content
                            from services.office.core.email_content_splitter import split_email_content
                            
                            # Split content into visible and quoted parts
                            split_result = split_email_content(
                                html_content=msg.get("body_html"),
                                text_content=msg.get("body_text")
                            )
                            
                            # Use visible content as primary body, quoted content for context
                            visible_content = split_result.get("visible_content", "")
                            quoted_content = split_result.get("quoted_content", "")
                            thread_summary = split_result.get("thread_summary", {})
                            
                            # Fallback to original content if splitting failed
                            if not visible_content:
                                if msg.get("body_html"):
                                    # Simple HTML to text extraction as fallback
                                    import re
                                    html_content = msg.get("body_html", "")
                                    visible_content = re.sub(r'<[^>]+>', '', html_content)
                                    visible_content = visible_content.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                                    visible_content = re.sub(r'\s+', ' ', visible_content).strip()
                                else:
                                    visible_content = msg.get("body_text", "")
                            
                            # Ensure we have some content
                            if not visible_content:
                                visible_content = msg.get("snippet", "No content available")
                            
                            # Extract sender email
                            sender_email = ""
                            if msg.get("from_address"):
                                sender_email = msg.get("from_address", {}).get("email", "")
                            
                            # Extract recipient emails
                            recipient_emails = []
                            if msg.get("to_addresses"):
                                recipient_emails = [addr.get("email", "") for addr in msg.get("to_addresses", []) if addr.get("email")]
                            
                            # Convert normalized EmailMessage to backfill format with content splitting
                            email = {
                                "id": msg.get("provider_message_id", msg.get("id")),
                                "user_id": self.user_id,
                                "provider": provider_str,
                                "type": "email",
                                "subject": msg.get("subject", "No Subject"),
                                "body": visible_content,  # Use visible content only
                                "from": sender_email,
                                "to": recipient_emails,
                                "thread_id": msg.get("thread_id", ""),
                                "folder": (
                                    msg.get("labels", ["inbox"])[0]
                                    if msg.get("labels")
                                    else "inbox"
                                ),
                                "created_at": msg.get("date"),
                                "updated_at": msg.get("date"),
                                "quoted_content": quoted_content,  # Add quoted content for context
                                "thread_summary": thread_summary,  # Add thread summary
                                "metadata": {
                                    "has_attachments": msg.get(
                                        "has_attachments", False
                                    ),
                                    "is_read": msg.get("is_read", True),
                                },
                            }
                            emails.append(email)

                        logger.info(
                            f"Retrieved {len(emails)} real emails from {provider_str} using office service internal API"
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
                f"Failed to get real emails from office service internal API for {provider_str if 'provider_str' in locals() else provider}: {e}"
            )
            logger.error("This could be due to:")
            logger.error("1. Office service not running")
            logger.error("2. Invalid API key")
            logger.error("3. Network connectivity issues")
            logger.error("4. Office service internal errors")
            raise Exception(
                f"Failed to retrieve real emails from {provider_str if 'provider_str' in locals() else provider} via office service: {e}"
            )

        # Return empty list if no emails found
        return []



    def set_rate_limit(self, emails_per_second: int):
        """Set the rate limit for email crawling"""
        if emails_per_second > 0:
            self.rate_limit_delay = 1.0 / emails_per_second
        else:
            self.rate_limit_delay = 0.0

        logger.info(f"Set email crawl rate limit to {emails_per_second} emails/second")
