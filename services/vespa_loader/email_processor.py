#!/usr/bin/env python3
"""
Email Content Processor for Vespa Loader Service

This module handles sophisticated email content processing including:
- Content splitting into manageable chunks
- Thread summary generation
- Quoted content extraction and handling
- Content normalization for better search
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.common.logging_config import get_logger

logger = get_logger(__name__)


class EmailContentProcessor:
    """Processes email content for optimal Vespa indexing"""

    def __init__(self) -> None:
        self.max_chunk_size = 1000  # Maximum characters per chunk
        self.min_chunk_size = 200   # Minimum characters per chunk
        self.quote_patterns = [
            r'^>.*$',  # Lines starting with >
            r'^On .* wrote:$',  # "On [date] [person] wrote:"
            r'^From:.*$',  # "From: [email]"
            r'^Sent:.*$',  # "Sent: [date]"
            r'^To:.*$',    # "To: [email]"
            r'^Subject:.*$', # "Subject: [text]"
        ]

    def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email data for optimal Vespa indexing"""
        try:
            # Validate input
            if not email_data or not isinstance(email_data, dict):
                logger.error("Invalid email data provided")
                return email_data
            
            # Extract basic email information
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            from_address = email_data.get('from', '')
            to_addresses = email_data.get('to', [])
            thread_id = email_data.get('thread_id', '')
            folder = email_data.get('folder', '')
            
            # Process the email body
            processed_body = self._process_body(body)
            
            # Generate thread summary if thread_id exists
            thread_summary = {}
            if thread_id:
                thread_summary = self._generate_thread_summary(email_data)
            
            # Create the processed email document
            processed_email = {
                "id": email_data.get('id'),
                "user_id": email_data.get('user_id'),
                "provider": email_data.get('provider'),
                "type": "email",
                "subject": subject,
                "body": processed_body['clean_content'],
                "body_text": processed_body['clean_content'],  # For backward compatibility
                "from": from_address,
                "to": to_addresses,
                "thread_id": thread_id,
                "folder": folder,
                "created_at": email_data.get('created_at'),
                "updated_at": email_data.get('updated_at'),
                "metadata": email_data.get('metadata', {}),
                # Add processed content fields
                "content_chunks": processed_body['chunks'],
                "quoted_content": processed_body['quoted_content'],
                "thread_summary": thread_summary,
                "search_text": self._generate_search_text(subject, processed_body['clean_content'], from_address, to_addresses),
            }
            
            logger.info(f"Processed email {email_data.get('id')} with {len(processed_body['chunks'])} chunks")
            return processed_email
            
        except Exception as e:
            logger.error(f"Error processing email {email_data.get('id')}: {e}")
            # Return original data if processing fails
            return email_data

    def _process_body(self, body: str) -> Dict[str, Any]:
        """Process email body content"""
        if not body:
            return {
                'clean_content': '',
                'chunks': [],
                'quoted_content': ''
            }
        
        # Split content and quoted content
        clean_content, quoted_content = self._separate_quoted_content(body)
        
        # Split clean content into chunks
        chunks = self._split_content_into_chunks(clean_content)
        
        # Clean up the content
        clean_content = self._clean_content(clean_content)
        
        return {
            'clean_content': clean_content,
            'chunks': chunks,
            'quoted_content': quoted_content
        }

    def _separate_quoted_content(self, body: str) -> Tuple[str, str]:
        """Separate quoted content from the main email content"""
        lines = body.split('\n')
        clean_lines = []
        quoted_lines = []
        in_quoted_section = False
        
        for line in lines:
            # Check if this line starts a quoted section
            if self._is_quote_start(line):
                in_quoted_section = True
            
            if in_quoted_section:
                quoted_lines.append(line)
            else:
                clean_lines.append(line)
        
        clean_content = '\n'.join(clean_lines).strip()
        quoted_content = '\n'.join(quoted_lines).strip()
        
        return clean_content, quoted_content

    def _is_quote_start(self, line: str) -> bool:
        """Check if a line starts a quoted section"""
        line = line.strip()
        for pattern in self.quote_patterns:
            if re.match(pattern, line):
                return True
        return False

    def _split_content_into_chunks(self, content: str) -> List[str]:
        """Split content into manageable chunks for Vespa indexing"""
        if not content:
            return []
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # If adding this paragraph would exceed max chunk size, start a new chunk
            if len(current_chunk) + len(paragraph) > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Ensure minimum chunk size by merging small chunks
        merged_chunks = self._merge_small_chunks(chunks)
        
        return merged_chunks

    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """Merge chunks that are too small"""
        if not chunks:
            return []
        
        merged = []
        current_chunk = ""
        
        for chunk in chunks:
            if len(current_chunk) + len(chunk) <= self.max_chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + chunk
                else:
                    current_chunk = chunk
            else:
                if current_chunk:
                    merged.append(current_chunk)
                current_chunk = chunk
        
        # Add the last chunk
        if current_chunk:
            merged.append(current_chunk)
        
        return merged

    def _clean_content(self, content: str) -> str:
        """Clean up content for better indexing"""
        if not content:
            return ""
        
        # Remove common email artifacts first (before whitespace normalization)
        # Remove signature lines (-- followed by newline and content)
        content = re.sub(r'--\s*\n.*', '', content, flags=re.DOTALL)
        # Remove quote markers
        content = re.sub(r'^\s*>\s*', '', content, flags=re.MULTILINE)
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()

    def _generate_thread_summary(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the email thread"""
        # This is a placeholder for now - could be enhanced with AI summarization
        return {
            "thread_id": email_data.get('thread_id', ''),
            "subject": email_data.get('subject', ''),
            "participants": self._extract_participants(email_data),
            "message_count": 1,  # Would need thread context to get actual count
            "last_updated": email_data.get('updated_at') or email_data.get('created_at'),
        }

    def _extract_participants(self, email_data: Dict[str, Any]) -> List[str]:
        """Extract participants from email data"""
        participants = set()
        
        # Add sender
        if email_data.get('from'):
            participants.add(email_data['from'])
        
        # Add recipients
        to_addresses = email_data.get('to', [])
        if isinstance(to_addresses, list):
            participants.update(to_addresses)
        elif isinstance(to_addresses, str):
            participants.add(to_addresses)
        
        return list(participants)

    def _generate_search_text(self, subject: str, body: str, from_address: str, to_addresses: List[str]) -> str:
        """Generate searchable text for the email"""
        search_parts = []
        
        if subject:
            search_parts.append(subject)
        
        if body:
            # Add first 500 characters of body for search
            search_parts.append(body[:500])
        
        if from_address:
            search_parts.append(f"From: {from_address}")
        
        if to_addresses:
            if isinstance(to_addresses, list):
                search_parts.append(f"To: {', '.join(to_addresses)}")
            else:
                search_parts.append(f"To: {to_addresses}")
        
        return " ".join(search_parts)
