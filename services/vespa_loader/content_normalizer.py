#!/usr/bin/env python3
"""
Content normalizer for processing HTML and other content formats
"""

import re
import logging
from typing import Optional
from html import unescape

logger = logging.getLogger(__name__)

class ContentNormalizer:
    """Normalizes content for better search indexing"""
    
    def __init__(self):
        # Common HTML tags to remove
        self.html_tags = [
            'html', 'head', 'body', 'div', 'span', 'p', 'br', 'hr',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
            'table', 'tr', 'td', 'th', 'thead', 'tbody', 'form', 'input',
            'button', 'select', 'option', 'textarea', 'label', 'fieldset',
            'legend', 'img', 'a', 'strong', 'b', 'em', 'i', 'u', 's',
            'blockquote', 'pre', 'code', 'kbd', 'samp', 'var', 'cite',
            'abbr', 'acronym', 'address', 'article', 'aside', 'footer',
            'header', 'main', 'nav', 'section', 'time', 'mark', 'small'
        ]
        
        # Email-specific patterns to clean
        self.email_patterns = [
            r'From:.*?\n',
            r'To:.*?\n',
            r'Subject:.*?\n',
            r'Date:.*?\n',
            r'Reply-To:.*?\n',
            r'CC:.*?\n',
            r'BCC:.*?\n',
            r'Message-ID:.*?\n',
            r'In-Reply-To:.*?\n',
            r'References:.*?\n',
            r'X-Mailer:.*?\n',
            r'X-Priority:.*?\n',
            r'X-MSMail-Priority:.*?\n',
            r'Importance:.*?\n',
            r'X-OriginalArrivalTime:.*?\n',
            r'Content-Type:.*?\n',
            r'Content-Transfer-Encoding:.*?\n',
            r'MIME-Version:.*?\n',
            r'X-.*?\n',  # Remove other X- headers
        ]
        
        # Compile regex patterns
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                                 for pattern in self.email_patterns]
    
    def normalize(self, content: str) -> str:
        """Normalize content by removing HTML, cleaning email headers, etc."""
        if not content:
            return ""
        
        try:
            # Convert to string if needed
            content = str(content)
            
            # Remove HTML tags
            content = self._remove_html_tags(content)
            
            # Clean email headers
            content = self._clean_email_headers(content)
            
            # Decode HTML entities
            content = unescape(content)
            
            # Clean up whitespace
            content = self._clean_whitespace(content)
            
            # Remove excessive newlines
            content = self._remove_excessive_newlines(content)
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error normalizing content: {e}")
            # Return original content if normalization fails
            return str(content)
    
    def _remove_html_tags(self, content: str) -> str:
        """Remove HTML tags from content"""
        # Remove script and style tags and their content
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML comments
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # Remove HTML tags
        for tag in self.html_tags:
            # Remove opening and closing tags
            content = re.sub(rf'<{tag}[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(rf'</{tag}[^>]*>', '', content, flags=re.IGNORECASE)
        
        # Remove any remaining HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        return content
    
    def _clean_email_headers(self, content: str) -> str:
        """Clean email headers from content"""
        for pattern in self.compiled_patterns:
            content = pattern.sub('', content)
        
        return content
    
    def _clean_whitespace(self, content: str) -> str:
        """Clean up whitespace in content"""
        # Replace multiple spaces with single space
        content = re.sub(r' +', ' ', content)
        
        # Replace multiple tabs with single space
        content = re.sub(r'\t+', ' ', content)
        
        # Replace multiple newlines with single newline
        content = re.sub(r'\n\s*\n', '\n', content)
        
        return content
    
    def _remove_excessive_newlines(self, content: str) -> str:
        """Remove excessive newlines"""
        # Replace 3 or more consecutive newlines with 2 newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def extract_text_from_html(self, html_content: str) -> str:
        """Extract plain text from HTML content"""
        if not html_content:
            return ""
        
        try:
            # Remove HTML tags
            text = self._remove_html_tags(html_content)
            
            # Decode HTML entities
            text = unescape(text)
            
            # Clean up whitespace
            text = self._clean_whitespace(text)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from HTML: {e}")
            return str(html_content)
    
    def normalize_for_search(self, content: str) -> str:
        """Normalize content specifically for search indexing"""
        if not content:
            return ""
        
        try:
            # Basic normalization
            normalized = self.normalize(content)
            
            # Convert to lowercase for better search matching
            normalized = normalized.lower()
            
            # Remove common punctuation that might interfere with search
            normalized = re.sub(r'[^\w\s]', ' ', normalized)
            
            # Clean up whitespace again
            normalized = self._clean_whitespace(normalized)
            
            return normalized.strip()
            
        except Exception as e:
            logger.error(f"Error normalizing content for search: {e}")
            return str(content)
    
    def truncate_content(self, content: str, max_length: int = 1000) -> str:
        """Truncate content to specified length while preserving word boundaries"""
        if not content or len(content) <= max_length:
            return content
        
        try:
            # Truncate to max_length
            truncated = content[:max_length]
            
            # Find the last complete word
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.8:  # Only truncate at word boundary if it's not too far back
                truncated = truncated[:last_space]
            
            # Add ellipsis
            truncated += "..."
            
            return truncated
            
        except Exception as e:
            logger.error(f"Error truncating content: {e}")
            return content[:max_length] + "..."
