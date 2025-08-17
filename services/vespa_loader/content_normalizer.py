#!/usr/bin/env python3
"""
Content normalizer for processing HTML and other content formats
"""

import re
from typing import Optional
from html import unescape
from services.common.logging_config import get_logger

logger = get_logger(__name__)

class ContentNormalizer:
    """Normalizes content for better search indexing"""
    
    def __init__(self) -> None:
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
        
        return content
    
    def _remove_excessive_newlines(self, content: str) -> str:
        """Remove excessive newlines from content"""
        # Replace multiple newlines with double newline
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def normalize_html(self, html_content: str) -> str:
        """Normalize HTML content specifically"""
        if not html_content:
            return ""
        
        try:
            # Remove HTML tags
            content = self._remove_html_tags(html_content)
            
            # Decode HTML entities
            content = unescape(content)
            
            # Clean up whitespace
            content = self._clean_whitespace(content)
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error normalizing HTML content: {e}")
            return str(html_content)
    
    def normalize_email(self, email_content: str) -> str:
        """Normalize email content specifically"""
        if not email_content:
            return ""
        
        try:
            # Clean email headers
            content = self._clean_email_headers(email_content)
            
            # Remove HTML tags if present
            content = self._remove_html_tags(content)
            
            # Decode HTML entities
            content = unescape(content)
            
            # Clean up whitespace
            content = self._clean_whitespace(content)
            
            # Remove excessive newlines
            content = self._remove_excessive_newlines(content)
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error normalizing email content: {e}")
            return str(email_content)
    
    def normalize_text(self, text_content: str) -> str:
        """Normalize plain text content"""
        if not text_content:
            return ""
        
        try:
            # Clean up whitespace
            content = self._clean_whitespace(text_content)
            
            # Remove excessive newlines
            content = self._remove_excessive_newlines(content)
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error normalizing text content: {e}")
            return str(text_content)
    
    def get_normalization_stats(self, original_content: str, normalized_content: str) -> dict:
        """Get statistics about the normalization process"""
        if not original_content:
            return {
                "original_length": 0,
                "normalized_length": len(normalized_content),
                "reduction_percentage": 0.0
            }
        
        original_length = len(original_content)
        normalized_length = len(normalized_content)
        
        if original_length == 0:
            reduction_percentage = 0.0
        else:
            reduction_percentage = ((original_length - normalized_length) / original_length) * 100
        
        return {
            "original_length": original_length,
            "normalized_length": normalized_length,
            "reduction_percentage": round(reduction_percentage, 2)
        }
