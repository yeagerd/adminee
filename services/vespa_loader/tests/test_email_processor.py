#!/usr/bin/env python3
"""
Tests for the EmailContentProcessor
"""

import pytest

from services.vespa_loader.email_processor import EmailContentProcessor


class TestEmailContentProcessor:
    """Test the EmailContentProcessor functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = EmailContentProcessor()

    def test_process_email_basic(self):
        """Test basic email processing"""
        email_data = {
            "id": "test_001",
            "user_id": "user@example.com",
            "provider": "gmail",
            "subject": "Test Email",
            "body": "This is a test email body with some content.",
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
            "thread_id": "thread_123",
            "folder": "INBOX",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        result = self.processor.process_email(email_data)

        assert result["id"] == "test_001"
        assert result["user_id"] == "user@example.com"
        assert result["subject"] == "Test Email"
        assert result["body"] == "This is a test email body with some content."
        assert result["from"] == "sender@example.com"
        assert result["to"] == ["recipient@example.com"]
        assert result["thread_id"] == "thread_123"
        assert result["folder"] == "INBOX"
        assert "content_chunks" in result
        assert "quoted_content" in result
        assert "thread_summary" in result
        assert "search_text" in result

    def test_process_email_with_quoted_content(self):
        """Test email processing with quoted content"""
        email_data = {
            "id": "test_002",
            "user_id": "user@example.com",
            "provider": "gmail",
            "subject": "Re: Test Email",
            "body": """This is my reply.

> On Jan 1, 2023, sender@example.com wrote:
> This is the original email.
> 
> Thanks,
> Sender""",
            "from": "user@example.com",
            "to": ["sender@example.com"],
        }

        result = self.processor.process_email(email_data)

        # Check that quoted content is separated
        assert "This is my reply." in result["body"]
        assert "On Jan 1, 2023, sender@example.com wrote:" in result["quoted_content"]
        assert "This is the original email." in result["quoted_content"]

    def test_process_email_content_splitting(self):
        """Test that email content is properly split into chunks"""
        # Create a long email body
        long_body = "\n\n".join(
            [f"Paragraph {i} with some content." * 20 for i in range(10)]
        )

        email_data = {
            "id": "test_003",
            "user_id": "user@example.com",
            "provider": "gmail",
            "subject": "Long Email",
            "body": long_body,
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
        }

        result = self.processor.process_email(email_data)

        # Should have multiple chunks
        assert len(result["content_chunks"]) > 1

        # Each chunk should be within size limits
        for chunk in result["content_chunks"]:
            assert len(chunk) <= self.processor.max_chunk_size
            assert len(chunk) >= self.processor.min_chunk_size

    def test_process_email_empty_body(self):
        """Test email processing with empty body"""
        email_data = {
            "id": "test_004",
            "user_id": "user@example.com",
            "provider": "gmail",
            "subject": "Empty Email",
            "body": "",
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
        }

        result = self.processor.process_email(email_data)

        assert result["body"] == ""
        assert result["content_chunks"] == []
        assert result["quoted_content"] == ""

    def test_process_email_with_thread_summary(self):
        """Test that thread summary is generated for emails with thread_id"""
        email_data = {
            "id": "test_005",
            "user_id": "user@example.com",
            "provider": "gmail",
            "subject": "Thread Email",
            "body": "This is part of a thread.",
            "from": "sender@example.com",
            "to": ["recipient@example.com"],
            "thread_id": "thread_456",
        }

        result = self.processor.process_email(email_data)

        assert "thread_summary" in result
        thread_summary = result["thread_summary"]
        assert thread_summary["thread_id"] == "thread_456"
        assert thread_summary["subject"] == "Thread Email"
        assert "sender@example.com" in thread_summary["participants"]
        assert "recipient@example.com" in thread_summary["participants"]

    def test_process_email_search_text_generation(self):
        """Test that search text is properly generated"""
        email_data = {
            "id": "test_006",
            "user_id": "user@example.com",
            "provider": "gmail",
            "subject": "Search Test",
            "body": "This email contains important information for searching.",
            "from": "sender@example.com",
            "to": ["recipient1@example.com", "recipient2@example.com"],
        }

        result = self.processor.process_email(email_data)

        search_text = result["search_text"]
        assert "Search Test" in search_text
        assert "This email contains important information for searching." in search_text
        assert "From: sender@example.com" in search_text
        assert "To: recipient1@example.com, recipient2@example.com" in search_text

    def test_process_email_error_handling(self):
        """Test that processing errors are handled gracefully"""
        # Test with malformed data
        email_data = None

        result = self.processor.process_email(email_data)

        # Should return the original data if processing fails
        assert result == email_data

    def test_quote_detection_patterns(self):
        """Test various quote detection patterns"""
        patterns = [
            "> This is a quoted line",
            "On Jan 1, 2023, user@example.com wrote:",
            "From: user@example.com",
            "Sent: January 1, 2023",
            "To: recipient@example.com",
            "Subject: Re: Test",
        ]

        for pattern in patterns:
            assert self.processor._is_quote_start(
                pattern
            ), f"Failed to detect quote: {pattern}"

        # Test non-quote lines
        non_quotes = [
            "This is not a quote",
            "Hello there!",
            "Best regards,",
        ]

        for line in non_quotes:
            assert not self.processor._is_quote_start(
                line
            ), f"False positive on: {line}"

    def test_content_cleaning(self):
        """Test that content is properly cleaned"""
        dirty_content = """
        This is the main content.
        
        -- 
        Best regards,
        Sender
        
        > Quoted content here
        """

        clean_content = self.processor._clean_content(dirty_content)

        # Should remove excessive whitespace and signature
        assert "This is the main content." in clean_content
        assert "--" not in clean_content
        assert "Best regards," not in clean_content
        assert "> Quoted content here" not in clean_content
