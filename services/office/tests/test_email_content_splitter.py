#!/usr/bin/env python3
"""
Unit tests for EmailContentSplitter

Tests various email content scenarios including:
- Outlook-style quoted text
- Gmail quoted content
- Plain text emails
- HTML emails
- Mixed content
"""

import pytest
from services.office.core.email_content_splitter import EmailContentSplitter, split_email_content


class TestEmailContentSplitter:
    """Test cases for EmailContentSplitter"""

    def setup_method(self):
        """Set up test fixtures"""
        self.splitter = EmailContentSplitter()

    def test_outlook_style_quoted_text(self):
        """Test splitting Outlook-style quoted text"""
        text_content = """Awesome! Let me know how it goes!

From: Dan . <danstrashbin@hotmail.com>
Sent: Wednesday, July 30, 2025 5:03 PM
To: Try Briefly <trybriefly@outlook.com>
Subject: Re: Hello from Briefly

I can't wait to try it out!

From: Try Briefly <trybriefly@outlook.com>
Sent: Wednesday, July 30, 2025 5:02 PM
To: Dan . <danstrashbin@hotmail.com>
Subject: Hello from Briefly

Try it out today!"""

        result = self.splitter.split_content(text_content=text_content)
        
        assert result['visible_content'] == "Awesome! Let me know how it goes!"
        assert "From: Dan . <danstrashbin@hotmail.com>" in result['quoted_content']
        assert "Sent: Wednesday, July 30, 2025 5:03 PM" in result['quoted_content']
        assert "I can't wait to try it out!" in result['quoted_content']
        assert "Try it out today!" in result['quoted_content']
        assert result['thread_summary']['participant_count'] == "2"
        assert "danstrashbin@hotmail.com" in result['thread_summary']['participants']
        assert "trybriefly@outlook.com" in result['thread_summary']['participants']

    def test_outlook_style_quoted_text_compact(self):
        """Test splitting compact Outlook-style quoted text"""
        text_content = """I can't wait to try it out! From: Try Briefly Sent: Wednesday, July 30, 2025 5:02 PM To: Dan . <danstrashbin@hotmail.com> Subject: Hello from Briefly Try it out today!"""

        result = self.splitter.split_content(text_content=text_content)
        
        # Should split at "From:" pattern
        assert result['visible_content'] == "I can't wait to try it out!"
        assert "From: Try Briefly" in result['quoted_content']
        assert "Sent: Wednesday, July 30, 2025 5:02 PM" in result['quoted_content']
        assert "To: Dan . <danstrashbin@hotmail.com>" in result['quoted_content']
        assert "Subject: Hello from Briefly" in result['quoted_content']
        assert "Try it out today!" in result['quoted_content']

    def test_gmail_quoted_content(self):
        """Test splitting Gmail-style quoted content"""
        html_content = """
        <div>This is my new message</div>
        <blockquote class="gmail_quote">
            <div>This is quoted content</div>
            <div>From: sender@example.com</div>
            <div>Sent: Monday, January 1, 2024</div>
        </blockquote>
        """

        result = self.splitter.split_content(html_content=html_content)
        
        assert result['visible_content'] == "This is my new message"
        assert "This is quoted content" in result['quoted_content']
        assert "From: sender@example.com" in result['quoted_content']
        assert "Sent: Monday, January 1, 2024" in result['quoted_content']

    def test_forwarded_message_pattern(self):
        """Test splitting forwarded message pattern"""
        text_content = """Here's what I think about this.

Begin forwarded message:
From: Original Sender <original@example.com>
Date: January 1, 2024
Subject: Original Subject
To: recipient@example.com

Original message content here."""

        result = self.splitter.split_content(text_content=text_content)
        
        assert result['visible_content'] == "Here's what I think about this."
        assert "Begin forwarded message:" in result['quoted_content']
        assert "From: Original Sender <original@example.com>" in result['quoted_content']
        assert "Original message content here." in result['quoted_content']

    def test_on_wrote_pattern(self):
        """Test splitting 'On ... wrote:' pattern"""
        text_content = """My response to your question.

On Mon, Jan 1, 2024 at 2:00 PM, John Doe <john@example.com> wrote:
> Here's my question
> 
> Can you help me with this?

Yes, I can help!"""

        result = self.splitter.split_content(text_content=text_content)
        
        assert result['visible_content'] == "My response to your question."
        assert "On Mon, Jan 1, 2024 at 2:00 PM, John Doe <john@example.com> wrote:" in result['quoted_content']
        assert "Here's my question" in result['quoted_content']
        assert "Can you help me with this?" in result['quoted_content']
        assert "Yes, I can help!" in result['quoted_content']

    def test_separator_line_pattern(self):
        """Test splitting on separator lines"""
        text_content = """New content here.

-----------
Original message below:
From: sender@example.com
Content: old message"""

        result = self.splitter.split_content(text_content=text_content)
        
        assert result['visible_content'] == "New content here."
        assert "-----------" in result['quoted_content']
        assert "Original message below:" in result['quoted_content']
        assert "From: sender@example.com" in result['quoted_content']

    def test_no_quoted_content(self):
        """Test email with no quoted content"""
        text_content = "This is a simple email with no quoted content."
        
        result = self.splitter.split_content(text_content=text_content)
        
        assert result['visible_content'] == "This is a simple email with no quoted content."
        assert result['quoted_content'] == ""
        assert result['thread_summary'] == {}

    def test_html_without_quotes(self):
        """Test HTML email without quoted content"""
        html_content = "<div>Hello world!</div><p>This is a test.</p>"
        
        result = self.splitter.split_content(html_content=html_content)
        
        assert result['visible_content'] == "Hello world! This is a test."
        assert result['quoted_content'] == ""

    def test_mixed_html_and_text(self):
        """Test with both HTML and text content"""
        html_content = "<div>HTML content</div>"
        text_content = "Text content with From: pattern"
        
        result = self.splitter.split_content(html_content=html_content, text_content=text_content)
        
        # Should prefer HTML splitting
        assert result['visible_content'] == "HTML content"
        assert result['quoted_content'] == ""

    def test_html_fallback_to_text(self):
        """Test HTML splitting failure falls back to text"""
        html_content = "<invalid>html<content>"
        text_content = "Valid text with From: sender@example.com"
        
        result = self.splitter.split_content(html_content=html_content, text_content=text_content)
        
        # Should fall back to text splitting
        assert result['visible_content'] == "Valid text with"
        assert "From: sender@example.com" in result['quoted_content']

    def test_thread_summary_extraction(self):
        """Test thread summary extraction"""
        text_content = """New message

From: user1@example.com
Sent: Monday
To: user2@example.com
Subject: Test

Old content

From: user3@example.com
Sent: Sunday
To: user1@example.com"""

        result = self.splitter.split_content(text_content=text_content)
        
        summary = result['thread_summary']
        assert summary['participant_count'] == "3"
        assert "user1@example.com" in summary['participants']
        assert "user2@example.com" in summary['participants']
        assert "user3@example.com" in summary['participants']
        assert summary['subject'] == "Test"

    def test_convenience_function(self):
        """Test the convenience function"""
        text_content = "Message From: sender@example.com"
        
        result = split_email_content(text_content=text_content)
        
        assert result['visible_content'] == "Message"
        assert "From: sender@example.com" in result['quoted_content']

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Empty content
        result = self.splitter.split_content()
        assert result['visible_content'] == ""
        assert result['quoted_content'] == ""
        
        # None content
        result = self.splitter.split_content(html_content=None, text_content=None)
        assert result['visible_content'] == ""
        assert result['quoted_content'] == ""
        
        # Very short content
        result = self.splitter.split_content(text_content="Hi")
        assert result['visible_content'] == "Hi"
        assert result['quoted_content'] == ""

    def test_real_world_examples(self):
        """Test with real-world examples from our emails"""
        # Example 1: The "Re: Hello from Briefly" email
        text_content = """I can't wait to try it out! From: Try Briefly Sent: Wednesday, July 30, 2025 5:02 PM To: Dan . <danstrashbin@hotmail.com> Subject: Hello from Briefly Try it out today!"""
        
        result = self.splitter.split_content(text_content=text_content)
        assert result['visible_content'] == "I can't wait to try it out!"
        assert "From: Try Briefly" in result['quoted_content']
        assert "Sent: Wednesday, July 30, 2025 5:02 PM" in result['quoted_content']
        assert "To: Dan . <danstrashbin@hotmail.com>" in result['quoted_content']
        assert "Subject: Hello from Briefly" in result['quoted_content']
        assert "Try it out today!" in result['quoted_content']

        # Example 2: The "Awesome! Let me know how it goes!" email
        text_content = """Awesome!  Let me know how it goes! From: Dan . <danstrashbin@hotmail.com> Sent: Wednesday, July 30, 2025 5:03 PM To: Try Briefly Subject: Re: Hello from Briefly I can't wait to try it out! From: Try Briefly Sent: Wednesday, July 30, 2025 5:02 PM To: Dan . <danstrashbin@hotmail.com> Subject: Hello from Briefly Try it out today!"""
        
        result = self.splitter.split_content(text_content=text_content)
        assert result['visible_content'] == "Awesome!  Let me know how it goes!"
        assert "From: Dan . <danstrashbin@hotmail.com>" in result['quoted_content']
        assert "Sent: Wednesday, July 30, 2025 5:03 PM" in result['quoted_content']
        assert "To: Try Briefly" in result['quoted_content']
        assert "Subject: Re: Hello from Briefly" in result['quoted_content']
        assert "I can't wait to try it out!" in result['quoted_content']
        assert "From: Try Briefly" in result['quoted_content']
        assert "Try it out today!" in result['quoted_content']


if __name__ == "__main__":
    pytest.main([__file__])
