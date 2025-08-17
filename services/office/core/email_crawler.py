#!/usr/bin/env python3
"""
Email crawling logic for backfill functionality
"""

import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import time

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
        max_emails: Optional[int] = None
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
        logger.info(f"Getting Microsoft email count for user {self.user_id}", extra={
            "user_id": self.user_id,
            "provider": self.provider,
            "operation": "email_count"
        })
        
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
        resume_from: int
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Crawl emails from Microsoft Graph API"""
        logger.info(f"Starting Microsoft email crawl for user {self.user_id}", extra={
            "user_id": self.user_id,
            "provider": self.provider,
            "operation": "email_crawl",
            "batch_size": batch_size,
            "start_date": start_date,
            "end_date": end_date
        })
        
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
                
                logger.debug(f"Processed Microsoft email batch {batch_num + 1}/{total_batches}")
                
            except Exception as e:
                logger.error(f"Failed to process Microsoft email batch {batch_num}: {e}")
                # Continue with next batch
                continue
    
    async def _crawl_google_emails(
        self,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]],
        resume_from: int
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
                
                logger.debug(f"Processed Gmail email batch {batch_num + 1}/{total_batches}")
                
            except Exception as e:
                logger.error(f"Failed to process Gmail email batch {batch_num}: {e}")
                # Continue with next batch
                continue
    
    async def _get_microsoft_email_batch(
        self,
        batch_num: int,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Get a batch of emails from Microsoft Graph API"""
        # This would integrate with the existing Microsoft Graph client
        # For now, return placeholder data
        
        # Simulate API call delay
        await asyncio.sleep(0.05)
        
        # Placeholder: in real implementation, this would query Microsoft Graph
        # from ..clients.microsoft_graph import MicrosoftGraphClient
        # client = MicrosoftGraphClient(self.user_id)
        # 
        # query_params = {
        #     "$top": batch_size,
        #     "$skip": batch_num * batch_size,
        #     "$orderby": "receivedDateTime desc"
        # }
        # 
        # if start_date:
        #     query_params["$filter"] = f"receivedDateTime ge {start_date.isoformat()}"
        # if end_date:
        #     if query_params.get("$filter"):
        #         query_params["$filter"] += f" and receivedDateTime le {end_date.isoformat()}"
        #     else:
        #         query_params["$filter"] = f"receivedDateTime le {end_date.isoformat()}"
        # 
        # emails = await client.get_emails(query_params)
        # return [self._normalize_microsoft_email(email) for email in emails]
        
        # Generate placeholder emails
        start_idx = batch_num * batch_size
        emails = []
        
        for i in range(batch_size):
            email_id = f"ms_{start_idx + i}"
            emails.append({
                "id": email_id,
                "user_id": self.user_id,
                "provider": "microsoft",
                "type": "email",
                "subject": f"Microsoft Email {start_idx + i}",
                "body": f"This is the body of Microsoft email {start_idx + i}",
                "from": f"sender{i}@microsoft.com",
                "to": [f"recipient{i}@example.com"],
                "thread_id": f"thread_{start_idx + i}",
                "folder": "inbox",
                "created_at": datetime.now(timezone.utc) - timedelta(days=i),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=i),
                "metadata": {
                    "has_attachments": False,
                    "is_read": True
                }
            })
        
        return emails
    
    async def _get_gmail_email_batch(
        self,
        batch_num: int,
        batch_size: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        folders: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Get a batch of emails from Gmail API"""
        # This would integrate with the existing Gmail client
        # For now, return placeholder data
        
        # Simulate API call delay
        await asyncio.sleep(0.05)
        
        # Placeholder: in real implementation, this would query Gmail API
        # from ..clients.gmail import GmailClient
        # client = GmailClient(self.user_id)
        # 
        # query_params = {
        #     "maxResults": batch_size,
        #     "pageToken": self._get_gmail_page_token(batch_num),
        #     "q": self._build_gmail_query(start_date, end_date, folders)
        # }
        # 
        # emails = await client.get_emails(query_params)
        # return [self._normalize_gmail_email(email) for email in emails]
        
        # Generate placeholder emails
        start_idx = batch_num * batch_size
        emails = []
        
        for i in range(batch_size):
            email_id = f"gmail_{start_idx + i}"
            emails.append({
                "id": email_id,
                "user_id": self.user_id,
                "provider": "google",
                "type": "email",
                "subject": f"Gmail Email {start_idx + i}",
                "body": f"This is the body of Gmail email {start_idx + i}",
                "from": f"sender{i}@gmail.com",
                "to": [f"recipient{i}@example.com"],
                "thread_id": f"thread_{start_idx + i}",
                "folder": "inbox",
                "created_at": datetime.now(timezone.utc) - timedelta(days=i),
                "updated_at": datetime.now(timezone.utc) - timedelta(days=i),
                "metadata": {
                    "has_attachments": False,
                    "is_read": True
                }
            })
        
        return emails
    
    def _normalize_microsoft_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Microsoft Graph email format to internal format"""
        return {
            "id": email.get("id"),
            "user_id": self.user_id,
            "provider": "microsoft",
            "type": "email",
            "subject": email.get("subject", ""),
            "body": email.get("body", {}).get("content", ""),
            "from": email.get("from", {}).get("emailAddress", {}).get("address", ""),
            "to": [recipient.get("emailAddress", {}).get("address", "") 
                   for recipient in email.get("toRecipients", [])],
            "thread_id": email.get("conversationId"),
            "folder": email.get("parentFolderId", "inbox"),
            "created_at": email.get("receivedDateTime"),
            "updated_at": email.get("lastModifiedDateTime"),
            "metadata": {
                "has_attachments": bool(email.get("hasAttachments")),
                "is_read": email.get("isRead", False),
                "importance": email.get("importance", "normal")
            }
        }
    
    def _normalize_gmail_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Gmail API email format to internal format"""
        return {
            "id": email.get("id"),
            "user_id": self.user_id,
            "provider": "google",
            "type": "email",
            "subject": email.get("snippet", ""),
            "body": email.get("snippet", ""),  # Gmail API provides snippet, not full body
            "from": email.get("payload", {}).get("headers", {}).get("From", ""),
            "to": [email.get("payload", {}).get("headers", {}).get("To", "")],
            "thread_id": email.get("threadId"),
            "folder": email.get("labelIds", ["inbox"])[0] if email.get("labelIds") else "inbox",
            "created_at": email.get("internalDate"),
            "updated_at": email.get("internalDate"),
            "metadata": {
                "has_attachments": bool(email.get("payload", {}).get("parts")),
                "is_read": "UNREAD" not in email.get("labelIds", []),
                "labels": email.get("labelIds", [])
            }
        }
    
    def set_rate_limit(self, emails_per_second: int):
        """Set the rate limit for email crawling"""
        if emails_per_second > 0:
            self.rate_limit_delay = 1.0 / emails_per_second
        else:
            self.rate_limit_delay = 0.0
        
        logger.info(f"Set email crawl rate limit to {emails_per_second} emails/second")
