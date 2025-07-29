"""
Email parser for detecting shipment information in emails
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedEmailData:
    """Data structure for parsed email information"""
    is_shipment_email: bool
    detected_carrier: Optional[str]
    tracking_numbers: List[str]
    confidence: float
    detected_from: str
    suggested_package_data: Optional[Dict]


class EmailParser:
    """Parser for detecting shipment information in emails"""
    
    # Common carrier domains and patterns
    CARRIER_PATTERNS = {
        'amazon': {
            'domains': ['amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de', 'amazon.fr', 'amazon.it', 'amazon.es', 'amazon.co.jp'],
            'keywords': ['shipment', 'package', 'order', 'delivery', 'tracking'],
            'tracking_patterns': [r'1Z[0-9A-Z]{16}', r'TBA[0-9]{10}', r'[0-9]{10,}']
        },
        'ups': {
            'domains': ['ups.com', 'ups.ca'],
            'keywords': ['ups', 'united parcel service', 'tracking'],
            'tracking_patterns': [r'1Z[0-9A-Z]{16}', r'[0-9]{9}', r'[0-9]{10}', r'[0-9]{12}']
        },
        'fedex': {
            'domains': ['fedex.com', 'fedex.ca'],
            'keywords': ['fedex', 'federal express', 'tracking'],
            'tracking_patterns': [r'[0-9]{12}', r'[0-9]{15}', r'[0-9]{22}']
        },
        'usps': {
            'domains': ['usps.com'],
            'keywords': ['usps', 'united states postal service', 'tracking'],
            'tracking_patterns': [r'[0-9]{20}', r'[0-9]{22}', r'[0-9]{13}', r'[0-9]{15}']
        },
        'dhl': {
            'domains': ['dhl.com', 'dhl.de'],
            'keywords': ['dhl', 'tracking'],
            'tracking_patterns': [r'[0-9]{10}', r'[0-9]{11}', r'[0-9]{12}', r'[0-9]{13}']
        }
    }
    
    # Generic tracking number patterns
    GENERIC_TRACKING_PATTERNS = [
        r'[0-9]{10,}',  # 10+ digits
        r'[A-Z]{2}[0-9]{9}[A-Z]{2}',  # Generic format
        r'[0-9]{3}-[0-9]{3}-[0-9]{4}',  # XXX-XXX-XXXX format
    ]
    
    def __init__(self):
        self.shipment_keywords = [
            'shipment', 'package', 'order', 'delivery', 'tracking', 
            'shipped', 'out for delivery', 'in transit', 'arrived'
        ]
    
    def parse_email(self, subject: str, sender: str, body: str, content_type: str = "text") -> ParsedEmailData:
        """
        Parse email content to detect shipment information
        
        Args:
            subject: Email subject line
            sender: Email sender address
            body: Email body content
            content_type: Content type ('text' or 'html')
            
        Returns:
            ParsedEmailData with detection results
        """
        result = ParsedEmailData(
            is_shipment_email=False,
            detected_carrier=None,
            tracking_numbers=[],
            confidence=0.0,
            detected_from='sender',
            suggested_package_data=None
        )
        
        # Normalize text
        subject_lower = subject.lower()
        sender_lower = sender.lower()
        body_lower = body.lower()
        
        # Check sender domain
        detected_carrier = self._detect_carrier_from_sender(sender_lower)
        if detected_carrier:
            result.detected_carrier = detected_carrier
            result.is_shipment_email = True
            result.confidence += 0.4
        
        # Check subject line
        subject_has_keywords = self._has_shipment_keywords(subject_lower)
        if subject_has_keywords:
            result.is_shipment_email = True
            result.confidence += 0.3
            if result.detected_from == 'sender':
                result.detected_from = 'subject'
            else:
                result.detected_from = 'multiple'
        
        # Check body
        body_has_keywords = self._has_shipment_keywords(body_lower)
        if body_has_keywords:
            result.is_shipment_email = True
            result.confidence += 0.2
            if result.detected_from == 'sender':
                result.detected_from = 'body'
            else:
                result.detected_from = 'multiple'
        
        # Extract tracking numbers
        all_text = f"{subject} {body}"
        tracking_numbers = self._extract_tracking_numbers(all_text, detected_carrier)
        result.tracking_numbers = tracking_numbers
        
        # Boost confidence if tracking numbers found
        if tracking_numbers:
            result.confidence += 0.3
        
        # Cap confidence at 1.0
        result.confidence = min(result.confidence, 1.0)
        
        # Generate suggested package data
        if result.is_shipment_email and tracking_numbers:
            result.suggested_package_data = self._generate_suggested_package_data(
                tracking_numbers[0], detected_carrier, subject, body
            )
        
        return result
    
    def _detect_carrier_from_sender(self, sender: str) -> Optional[str]:
        """Detect carrier from sender email domain"""
        for carrier, patterns in self.CARRIER_PATTERNS.items():
            if any(domain in sender for domain in patterns['domains']):
                return carrier
        return None
    
    def _has_shipment_keywords(self, text: str) -> bool:
        """Check if text contains shipment-related keywords"""
        return any(keyword in text for keyword in self.shipment_keywords)
    
    def _extract_tracking_numbers(self, text: str, detected_carrier: Optional[str]) -> List[str]:
        """Extract tracking numbers from text"""
        found_numbers = set()
        
        # Check carrier-specific patterns first
        if detected_carrier and detected_carrier in self.CARRIER_PATTERNS:
            patterns = self.CARRIER_PATTERNS[detected_carrier]['tracking_patterns']
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                found_numbers.update(matches)
        
        # Check generic patterns
        for pattern in self.GENERIC_TRACKING_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_numbers.update(matches)
        
        return list(found_numbers)
    
    def _generate_suggested_package_data(self, tracking_number: str, carrier: Optional[str], subject: str, body: str) -> Dict:
        """Generate suggested package data for creating a tracking entry"""
        suggested_data = {
            'tracking_number': tracking_number,
            'carrier': carrier or 'unknown',
            'status': 'pending'
        }
        
        # Try to extract order number from subject or body
        order_patterns = [
            r'order[:\s#]*([A-Z0-9\-]+)',
            r'order[:\s#]*#([A-Z0-9\-]+)',
            r'#([A-Z0-9\-]{10,})'
        ]
        
        for pattern in order_patterns:
            match = re.search(pattern, subject + ' ' + body, re.IGNORECASE)
            if match:
                suggested_data['order_number'] = match.group(1)
                break
        
        return suggested_data 