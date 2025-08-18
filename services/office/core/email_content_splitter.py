#!/usr/bin/env python3
"""
Email Content Splitter - Intelligently separates email content from quoted/thread content

This module provides functionality to split email content into:
- visible_content: The new part of the email
- quoted_content: Thread history, forwarded content, etc.

Based on the logic from the frontend EmailThreadCard component.
"""

import re
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup
from bs4.element import Tag


class EmailContentSplitter:
    """Splits email content into visible and quoted parts"""
    
    def __init__(self):
                            # Common patterns for detecting quoted content (based on frontend logic)
                    self.quote_patterns = [
                        # Separator lines with newline boundaries (most reliable)
                        r'\n[-_=*]{5,}\n',
                        r'\n-{5,}\s*Original Message\s*-{5,}\n',
                        r'\nBegin forwarded message:\n',
                        r'\nForwarded message:\n',
                        r'\nOn .{0,200}?wrote:\n',
                        # Outlook-style quoted headers with newline boundaries
                        r'\nFrom:\s.+\s+Sent:\s.+\s+To:\s.+\n',
                        # More flexible Outlook pattern (From: followed by other headers)
                        r'\nFrom:\s+[^<]+(?:Sent:\s+[^<]+)?(?:To:\s+[^<]+)?(?:Subject:\s+[^<]+)?',
                        # Simple From: pattern that's common in Outlook
                        r'\nFrom:\s+[^<]+',
                        # Compact Outlook format (no newlines) - this is what we're actually seeing
                        r'From:\s+[^<]+(?:Sent:\s+[^<]+)?(?:To:\s+[^<]+)?(?:Subject:\s+[^<]+)?',
                        # Simple From: pattern for compact format
                        r'From:\s+[^<]+',
                        # Separator lines without newline boundaries (fallback)
                        r'[-_=*]{5,}',
                    ]
                    
                    # HTML selectors for quoted content
                    self.quote_selectors = [
            '.gmail_quote',
            'blockquote.gmail_quote',
            'blockquote[type="cite"]',
            'div.yahoo_quoted',
            'div[id^="yiv"] blockquote',
            'div[id^="yui_"] blockquote',
        ]
    
    def split_content(self, html_content: Optional[str] = None, text_content: Optional[str] = None) -> Dict[str, str]:
        """
        Split email content into visible and quoted parts
        
        Args:
            html_content: HTML content of the email
            text_content: Plain text content of the email
            
        Returns:
            Dict with keys: visible_content, quoted_content, thread_summary
        """
        result = {
            'visible_content': '',
            'quoted_content': '',
            'thread_summary': {}
        }
        
        # Try HTML splitting first if available
        if html_content:
            html_result = self._split_html_content(html_content)
            if html_result:
                result['visible_content'] = html_result['visible']
                result['quoted_content'] = html_result['quoted']
                result['thread_summary'] = self._extract_thread_summary(html_result['visible'], html_result['quoted'])
                return result
        
        # Fall back to text-based splitting
        if text_content:
            text_result = self._split_text_content(text_content)
            if text_result:
                result['visible_content'] = text_result['visible']
                result['quoted_content'] = text_result['quoted']
                result['thread_summary'] = self._extract_thread_summary(text_result['visible'], text_result['quoted'])
                return result
        
        # If no splitting possible, use original content as visible
        if html_content:
            result['visible_content'] = self._html_to_text(html_content)
        elif text_content:
            result['visible_content'] = text_content
        
        return result
    
    def _split_html_content(self, html_content: str) -> Optional[Dict[str, str]]:
        """Split HTML content using DOM parsing with string-based fallback"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Try to find quoted content using selectors
            quoted_node: Optional[Tag] = None
            for selector in self.quote_selectors:
                quoted_node = soup.select_one(selector)
                if quoted_node:
                    break

            # Try horizontal rule as boundary
            if not quoted_node:
                hr_node = soup.find('hr')
                if hr_node:
                    quoted_node = hr_node

            # Try pattern-based detection in text content
            if not quoted_node:
                text_content = soup.get_text()
                for pattern in self.quote_patterns:
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        # Find the element containing this text
                        quoted_node = self._find_element_containing_text(soup, match.group())
                        if quoted_node:
                            break

            if not quoted_node:
                return None

            # Compute visible and quoted parts using string split around the quoted node HTML
            quoted_html = str(quoted_node)

            # Visible HTML: try splitting the original HTML
            visible_html = ""
            remaining_html = ""
            if quoted_html and quoted_html in html_content:
                parts = html_content.split(quoted_html, 1)
                visible_html = parts[0]
                remaining_html = parts[1] if len(parts) > 1 else ""
            else:
                # Fallback: remove the quoted node from a fresh soup
                visible_soup = BeautifulSoup(html_content, 'html.parser')
                fallback_node = None
                for selector in self.quote_selectors:
                    fallback_node = visible_soup.select_one(selector)
                    if fallback_node:
                        break
                if not fallback_node:
                    fallback_node = visible_soup.find('hr')
                if fallback_node:
                    fallback_node.extract()
                visible_html = str(visible_soup)
                remaining_html = quoted_html

            visible_text = self._html_to_text(visible_html)
            quoted_text = self._html_to_text(remaining_html)

            # Validate split
            if not visible_text.strip() and not quoted_text.strip():
                return None

            return {
                'visible': visible_text.strip(),
                'quoted': quoted_text.strip(),
            }

        except Exception as e:
            print(f"HTML splitting failed: {e}")
            return None
    
    def _split_text_content(self, text_content: str) -> Optional[Dict[str, str]]:
        """Split text content using regex patterns (based on frontend logic)"""
        try:
            # Try patterns in order of specificity
            for pattern in self.quote_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
                if match:
                    split_index = match.start()
                    
                    # For patterns with newline boundaries, try to find the actual content boundary
                    if pattern.startswith(r'\n'):
                        # Look for the start of the quoted content (after the newline)
                        quoted_start = split_index + 1  # Skip the leading newline
                        visible = text_content[:split_index].strip()
                        quoted = text_content[quoted_start:].strip()
                    else:
                        # For patterns without newline boundaries, use the match start
                        visible = text_content[:split_index].strip()
                        quoted = text_content[split_index:].strip()
                    
                    # Validate split - ensure we have meaningful content on both sides
                    if visible and quoted and len(visible) > 5 and len(quoted) > 20:
                        # Additional validation: make sure we're not splitting in the middle of a sentence
                        if not visible.endswith(('.', '!', '?')):
                            # Try to find a better break point
                            last_sentence_end = max(
                                visible.rfind('.'),
                                visible.rfind('!'),
                                visible.rfind('?')
                            )
                            if last_sentence_end > len(visible) * 0.7:  # If sentence end is in last 30%
                                visible = visible[:last_sentence_end + 1].strip()
                                quoted = text_content[last_sentence_end + 1:].strip()
                        
                        return {
                            'visible': visible,
                            'quoted': quoted
                        }
            
            return None
            
        except Exception as e:
            print(f"Text splitting failed: {e}")
            return None
    
    def _find_element_containing_text(self, soup: BeautifulSoup, text: str) -> Optional[Tag]:
        """Find the element containing specific text"""
        for element in soup.find_all():
            if text in element.get_text():
                return element
        return None
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except:
            # Fallback: basic HTML tag removal
            return re.sub(r'<[^>]+>', '', html)
    
    def _extract_thread_summary(self, visible_content: str, quoted_content: str) -> Dict[str, str]:
        """Extract thread summary information"""
        summary = {}
        
        # Count participants (simple heuristic)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, visible_content + quoted_content)
        unique_emails = list(set(emails))
        
        # Also look for email addresses in From: and To: patterns
        from_pattern = r'From:\s*[^<]*<([^>]+)>'
        to_pattern = r'To:\s*[^<]*<([^>]+)>'
        
        from_emails = re.findall(from_pattern, visible_content + quoted_content, re.IGNORECASE)
        to_emails = re.findall(to_pattern, visible_content + quoted_content, re.IGNORECASE)
        
        all_emails = emails + from_emails + to_emails
        unique_all_emails = list(set(all_emails))
        
        if unique_all_emails:
            summary['participant_count'] = str(len(unique_all_emails))
            summary['participants'] = ', '.join(unique_all_emails[:3])  # Limit to first 3
        
        # Estimate thread length based on quoted content
        if quoted_content:
            # Count email-like patterns in quoted content
            quoted_emails = re.findall(email_pattern, quoted_content)
            if quoted_emails:
                summary['thread_length'] = str(len(set(quoted_emails)) + 1)  # +1 for current email
        
        # Extract subject if present
        subject_pattern = r'Subject:\s*([^\n\r]+)'
        subject_match = re.search(subject_pattern, visible_content + quoted_content, re.IGNORECASE)
        if subject_match:
            summary['subject'] = subject_match.group(1).strip()
        
        return summary


def split_email_content(html_content: Optional[str] = None, text_content: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience function to split email content
    
    Args:
        html_content: HTML content of the email
        text_content: Plain text content of the email
        
    Returns:
        Dict with keys: visible_content, quoted_content, thread_summary
    """
    splitter = EmailContentSplitter()
    return splitter.split_content(html_content, text_content)
