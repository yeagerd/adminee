#!/usr/bin/env python3
"""
Unit tests for email normalizer functions.

These tests ensure that the normalizer functions correctly handle different content types
and populate the appropriate fields based on the actual content type, not just the presence
of body_html.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.api.v1.office import Provider
from services.office.core.normalizer import (
    _is_html_content,
    normalize_google_email,
    normalize_microsoft_email,
)


class TestHTMLContentDetection:
    """Tests for the _is_html_content helper function."""

    def test_html_content_detection(self):
        """Test that HTML content is correctly identified."""
        # Test HTML content
        assert _is_html_content("<p>Hello <strong>world</strong>!</p>") is True
        assert _is_html_content("<html><body>Content</body></html>") is True
        assert _is_html_content("<div>Text</div>") is True

        # Test text content
        assert _is_html_content("Hello world!") is False
        assert _is_html_content("Plain text email") is False
        assert _is_html_content("") is False

        # Test edge cases
        assert _is_html_content("Hello <world>!") is True  # Contains HTML-like tags
        assert (
            _is_html_content("Hello &amp; world!") is False
        )  # HTML entities but no tags


class TestGoogleEmailNormalizer:
    """Tests for the Google email normalizer function."""

    def test_gmail_with_html_content_and_html_visible_content(self):
        """Test Gmail normalization when both body_html and visible_content are HTML."""
        # Mock Gmail API response with HTML content
        raw_data = {
            "id": "gmail_123",
            "threadId": "thread_456",
            "snippet": "Test email",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                ],
                "body": {"data": "SGVsbG8gd29ybGQ="},  # Base64 encoded "Hello world"
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": "PHA+SGVsbG8gPHN0cm9uZz53b3JsZDwvc3Ryb25nPiE8L3A+"  # Base64 encoded "<p>Hello <strong>world</strong>!</p>"
                        },
                    }
                ],
            },
        }

        # Mock the email content splitter to return HTML content
        with patch(
            "services.office.core.email_content_splitter.split_email_content"
        ) as mock_split:
            mock_split.return_value = {
                "visible_content": "<p>Hello <strong>world</strong>!</p>",
                "quoted_content": "",
                "thread_summary": {},
            }

            result = normalize_google_email(raw_data, "account@example.com")

            # Verify that body_html_unquoted is populated with HTML content
            assert result.body_html_unquoted == "<p>Hello <strong>world</strong>!</p>"
            # Verify that body_text_unquoted is populated with text content
            assert result.body_text_unquoted == "Hello world!"
            # Verify that body_html is present
            assert result.body_html is not None

    def test_gmail_with_html_content_but_text_visible_content(self):
        """Test Gmail normalization when body_html exists but visible_content is text (the bug case)."""
        # Mock Gmail API response with HTML content
        raw_data = {
            "id": "gmail_123",
            "threadId": "thread_456",
            "snippet": "Test email",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                ],
                "body": {"data": "SGVsbG8gd29ybGQ="},  # Base64 encoded "Hello world"
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": "PHA+SGVsbG8gPHN0cm9uZz53b3JsZDwvc3Ryb25nPiE8L3A+"  # Base64 encoded "<p>Hello <strong>world</strong>!</p>"
                        },
                    }
                ],
            },
        }

        # Mock the email content splitter to return TEXT content (this was the bug!)
        with patch(
            "services.office.core.email_content_splitter.split_email_content"
        ) as mock_split:
            mock_split.return_value = {
                "visible_content": "Hello world!",  # Text content, not HTML
                "quoted_content": "",
                "thread_summary": {},
            }

            result = normalize_google_email(raw_data, "account@example.com")

            # Verify that body_html_unquoted is NOT populated (this was the bug!)
            assert result.body_html_unquoted is None
            # Verify that body_text_unquoted is populated with the text content
            assert result.body_text_unquoted == "Hello world!"
            # Verify that body_html is still present
            assert result.body_html is not None

    def test_gmail_with_text_content_only(self):
        """Test Gmail normalization when only text content is available."""
        # Mock Gmail API response with text content only
        raw_data = {
            "id": "gmail_123",
            "threadId": "thread_456",
            "snippet": "Test email",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                ],
                "body": {"data": "SGVsbG8gd29ybGQ="},  # Base64 encoded "Hello world"
            },
        }

        # Mock the email content splitter to return text content
        with patch(
            "services.office.core.email_content_splitter.split_email_content"
        ) as mock_split:
            mock_split.return_value = {
                "visible_content": "Hello world!",
                "quoted_content": "",
                "thread_summary": {},
            }

            result = normalize_google_email(raw_data, "account@example.com")

            # Verify that body_html_unquoted is NOT populated
            assert result.body_html_unquoted is None
            # Verify that body_text_unquoted is populated with the text content
            assert result.body_text_unquoted == "Hello world!"
            # Verify that body_html is None
            assert result.body_html is None


class TestMicrosoftEmailNormalizer:
    """Tests for the Microsoft email normalizer function."""

    def test_microsoft_with_html_content_and_html_visible_content(self):
        """Test Microsoft normalization when both body_html and visible_content are HTML."""
        # Mock Microsoft Graph API response with HTML content
        raw_data = {
            "id": "outlook_123",
            "conversationId": "conv_456",
            "subject": "Test Subject",
            "bodyPreview": "Test email preview",
            "receivedDateTime": "2024-01-01T12:00:00Z",
            "isRead": False,
            "hasAttachments": False,
            "categories": [],
            "importance": "normal",
            "from": {
                "emailAddress": {"address": "sender@example.com", "name": "Sender"}
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": "recipient@example.com",
                        "name": "Recipient",
                    }
                }
            ],
            "body": {
                "contentType": "html",
                "content": "<p>Hello <strong>world</strong>!</p>",
            },
        }

        # Mock the email content splitter to return HTML content
        with patch(
            "services.office.core.email_content_splitter.split_email_content"
        ) as mock_split:
            mock_split.return_value = {
                "visible_content": "<p>Hello <strong>world</strong>!</p>",
                "quoted_content": "",
                "thread_summary": {},
            }

            result = normalize_microsoft_email(raw_data, "account@example.com")

            # Verify that body_html_unquoted is populated with HTML content
            assert result.body_html_unquoted == "<p>Hello <strong>world</strong>!</p>"
            # Verify that body_text_unquoted is populated with text content
            assert result.body_text_unquoted == "Hello world!"
            # Verify that body_html is present
            assert result.body_html is not None

    def test_microsoft_with_html_content_but_text_visible_content(self):
        """Test Microsoft normalization when body_html exists but visible_content is text (the bug case)."""
        # Mock Microsoft Graph API response with HTML content
        raw_data = {
            "id": "outlook_123",
            "conversationId": "conv_456",
            "subject": "Test Subject",
            "bodyPreview": "Test email preview",
            "receivedDateTime": "2024-01-01T12:00:00Z",
            "isRead": False,
            "hasAttachments": False,
            "categories": [],
            "importance": "normal",
            "from": {
                "emailAddress": {"address": "sender@example.com", "name": "Sender"}
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": "recipient@example.com",
                        "name": "Recipient",
                    }
                }
            ],
            "body": {
                "contentType": "html",
                "content": "<p>Hello <strong>world</strong>!</p>",
            },
        }

        # Mock the email content splitter to return TEXT content (this was the bug!)
        with patch(
            "services.office.core.email_content_splitter.split_email_content"
        ) as mock_split:
            mock_split.return_value = {
                "visible_content": "Hello world!",  # Text content, not HTML
                "quoted_content": "",
                "thread_summary": {},
            }

            result = normalize_microsoft_email(raw_data, "account@example.com")

            # Verify that body_html_unquoted is NOT populated (this was the bug!)
            assert result.body_html_unquoted is None
            # Verify that body_text_unquoted is populated with the text content
            assert result.body_text_unquoted == "Hello world!"
            # Verify that body_html is still present
            assert result.body_html is not None

    def test_microsoft_with_text_content_only(self):
        """Test Microsoft normalization when only text content is available."""
        # Mock Microsoft Graph API response with text content only
        raw_data = {
            "id": "outlook_123",
            "conversationId": "conv_456",
            "subject": "Test Subject",
            "bodyPreview": "Test email preview",
            "receivedDateTime": "2024-01-01T12:00:00Z",
            "isRead": False,
            "hasAttachments": False,
            "categories": [],
            "importance": "normal",
            "from": {
                "emailAddress": {"address": "sender@example.com", "name": "Sender"}
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": "recipient@example.com",
                        "name": "Recipient",
                    }
                }
            ],
            "body": {"contentType": "text", "content": "Hello world!"},
        }

        # Mock the email content splitter to return text content
        with patch(
            "services.office.core.email_content_splitter.split_email_content"
        ) as mock_split:
            mock_split.return_value = {
                "visible_content": "Hello world!",
                "quoted_content": "",
                "thread_summary": {},
            }

            result = normalize_microsoft_email(raw_data, "account@example.com")

            # Verify that body_html_unquoted is NOT populated
            assert result.body_html_unquoted is None
            # Verify that body_text_unquoted is populated with the text content
            assert result.body_text_unquoted == "Hello world!"
            # Verify that body_html is None
            assert result.body_html is None


class TestNormalizerEdgeCases:
    """Tests for edge cases in the normalizer functions."""

    def test_empty_visible_content(self):
        """Test that empty visible content is handled correctly."""
        # Mock Gmail API response
        raw_data = {
            "id": "gmail_123",
            "threadId": "thread_456",
            "snippet": "Test email",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                ],
                "body": {"data": "SGVsbG8gd29ybGQ="},  # Base64 encoded "Hello world"
            },
        }

        # Mock the email content splitter to return empty content
        with patch(
            "services.office.core.email_content_splitter.split_email_content"
        ) as mock_split:
            mock_split.return_value = {
                "visible_content": "",
                "quoted_content": "",
                "thread_summary": {},
            }

            result = normalize_google_email(raw_data, "account@example.com")

            # Verify that fallback content is used
            assert result.body_text_unquoted == "Test email"  # Falls back to snippet
            assert result.body_html_unquoted is None

    def test_mixed_content_handling(self):
        """Test that mixed content (HTML-like but not valid HTML) is handled correctly."""
        # Mock Gmail API response
        raw_data = {
            "id": "gmail_123",
            "threadId": "thread_456",
            "snippet": "Test email",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                ],
                "body": {"data": "SGVsbG8gd29ybGQ="},  # Base64 encoded "Hello world"
            },
        }

        # Mock the email content splitter to return mixed content
        with patch(
            "services.office.core.email_content_splitter.split_email_content"
        ) as mock_split:
            mock_split.return_value = {
                "visible_content": "Hello <world>!",  # Contains HTML-like characters
                "quoted_content": "",
                "thread_summary": {},
            }

            result = normalize_google_email(raw_data, "account@example.com")

            # Since the content contains HTML-like characters, it should be treated as HTML
            # But since there's no body_html, it should still go to body_text_unquoted
            assert result.body_html_unquoted is None
            assert result.body_text_unquoted == "Hello <world>!"
