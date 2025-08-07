"""
Email parser for detecting shipment information in emails
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from services.shipments.utils import normalize_tracking_number


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
        "amazon": {
            "domains": [
                "amazon.com",
                "amazon.co.uk",
                "amazon.ca",
                "amazon.de",
                "amazon.fr",
                "amazon.it",
                "amazon.es",
                "amazon.co.jp",
            ],
            "keywords": ["shipment", "package", "order", "delivery", "tracking"],
            "tracking_patterns": [r"1Z[0-9A-Z]{16}", r"TBA[0-9]{10}", r"[0-9]{10,}"],
        },
        "usps": {
            "domains": ["usps.com"],
            "keywords": ["usps", "united states postal service", "tracking"],
            "tracking_patterns": [
                r"[0-9]{20}",
                r"[0-9]{22}",
                r"[0-9]{13}",
                r"[0-9]{15}",
                r"[0-9]{26}",  # USPS 26-digit tracking numbers
            ],
        },
        "ups": {
            "domains": ["ups.com", "ups.ca"],
            "keywords": ["ups", "united parcel service", "tracking"],
            "tracking_patterns": [
                r"1Z[0-9A-Z]{16}",
                r"[0-9]{9}",
                r"[0-9]{10}",
                r"[0-9]{12}",
                r"[0-9]{26}",
            ],
        },
        "fedex": {
            "domains": ["fedex.com", "fedex.ca"],
            "keywords": ["fedex", "federal express", "tracking"],
            "tracking_patterns": [r"[0-9]{12}", r"[0-9]{15}", r"[0-9]{22}"],
        },
        "dhl": {
            "domains": ["dhl.com", "dhl.de"],
            "keywords": ["dhl", "tracking"],
            "tracking_patterns": [
                r"[0-9]{10}",
                r"[0-9]{11}",
                r"[0-9]{12}",
                r"[0-9]{13}",
            ],
        },
    }

    # Generic tracking number patterns
    GENERIC_TRACKING_PATTERNS = [
        r"[0-9]{10,}",  # 10+ digits
        r"[A-Z]{2}[0-9]{9}[A-Z]{2}",  # Generic format
        r"[0-9]{3}-[0-9]{3}-[0-9]{4}",  # XXX-XXX-XXXX format
    ]

    def __init__(self) -> None:
        self.shipment_keywords = [
            "shipment",
            "package",
            "order",
            "delivery",
            "tracking",
            "shipped",
            "out for delivery",
            "in transit",
            "arrived",
        ]

    def parse_email(
        self, subject: str, sender: str, body: str, content_type: str = "text"
    ) -> ParsedEmailData:
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
            detected_from="sender",
            suggested_package_data=None,
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
            if result.detected_from == "sender":
                result.detected_from = "subject"
            else:
                result.detected_from = "multiple"

        # Check body
        body_has_keywords = self._has_shipment_keywords(body_lower)
        if body_has_keywords:
            result.is_shipment_email = True
            result.confidence += 0.2
            if result.detected_from == "sender":
                result.detected_from = "body"
            else:
                result.detected_from = "multiple"

        # Extract tracking numbers
        all_text = f"{subject} {body}"
        tracking_numbers = self._extract_tracking_numbers(all_text, detected_carrier)
        result.tracking_numbers = tracking_numbers

        # If no carrier detected from sender but we have tracking numbers, try to detect from tracking number
        if not detected_carrier and tracking_numbers:
            detected_carrier = self._detect_carrier_from_tracking_number(
                tracking_numbers[0], body
            )
            if detected_carrier:
                result.detected_carrier = detected_carrier
                result.confidence += 0.2

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
            if any(domain in sender for domain in patterns["domains"]):
                return carrier
        return None

    def _detect_carrier_from_tracking_number(
        self, tracking_number: str, body: str = ""
    ) -> Optional[str]:
        """Detect carrier from tracking number format"""
        if not tracking_number:
            return None

        # Remove any non-alphanumeric characters
        clean_number = re.sub(r"[^0-9A-Za-z]", "", tracking_number)

        # Special handling for 26-digit tracking numbers (UPS Mail Innovations vs USPS)
        if len(clean_number) == 26 and clean_number.isdigit():
            # Check if this is UPS Mail Innovations by looking for UPS context in the body
            body_lower = body.lower()
            if "ups.com" in body_lower or "united parcel service" in body_lower:
                return "ups"
            else:
                # Default to USPS for 26-digit numbers without UPS context
                return "usps"

        # Check each carrier's patterns
        for carrier, patterns in self.CARRIER_PATTERNS.items():
            for pattern in patterns["tracking_patterns"]:
                if re.match(pattern, clean_number):
                    return carrier
        return None

    def _has_shipment_keywords(self, text: str) -> bool:
        """Check if text contains shipment-related keywords"""
        return any(keyword in text for keyword in self.shipment_keywords)

    def _extract_tracking_numbers(
        self, text: str, detected_carrier: Optional[str]
    ) -> List[str]:
        """Extract tracking numbers from text"""
        found_numbers = set()

        # Check carrier-specific patterns first
        if detected_carrier and detected_carrier in self.CARRIER_PATTERNS:
            patterns = self.CARRIER_PATTERNS[detected_carrier]["tracking_patterns"]
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                # Normalize each found tracking number
                normalized_matches = [
                    normalize_tracking_number(match, detected_carrier)
                    for match in matches
                ]
                found_numbers.update(normalized_matches)

        # Check generic patterns
        for pattern in self.GENERIC_TRACKING_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            # Normalize each found tracking number
            normalized_matches = [
                normalize_tracking_number(match, detected_carrier) for match in matches
            ]
            found_numbers.update(normalized_matches)

        return list(found_numbers)

    def _generate_suggested_package_data(
        self, tracking_number: str, carrier: Optional[str], subject: str, body: str
    ) -> Dict:
        """Generate suggested package data for creating a tracking entry"""
        # Ensure tracking number is normalized
        normalized_tracking = normalize_tracking_number(tracking_number, carrier)

        suggested_data = {
            "tracking_number": normalized_tracking,
            "carrier": carrier or "unknown",
            "status": "pending",
        }

        # Try to extract order number from subject or body
        order_patterns = [
            r"order[:\s#]*([A-Z0-9\-]+)",
            r"order[:\s#]*#([A-Z0-9\-]+)",
            r"#([A-Z0-9\-]{10,})",
        ]

        for pattern in order_patterns:
            match = re.search(pattern, subject + " " + body, re.IGNORECASE)
            if match:
                suggested_data["order_number"] = match.group(1)
                break

        # Try to extract shipper name from sender domain or common patterns
        if carrier == "amazon":
            suggested_data["shipper_name"] = "Amazon"
        elif carrier == "ups":
            suggested_data["shipper_name"] = "UPS"
        elif carrier == "fedex":
            suggested_data["shipper_name"] = "FedEx"
        elif carrier == "usps":
            suggested_data["shipper_name"] = "USPS"
        elif carrier == "dhl":
            suggested_data["shipper_name"] = "DHL"

        # Try to extract package description from subject
        if subject:
            # Remove common prefixes and clean up
            clean_subject = re.sub(
                r"^(Your |Order |Package |Shipment |Tracking )",
                "",
                subject,
                flags=re.IGNORECASE,
            )
            clean_subject = re.sub(
                r" has (shipped|been shipped|arrived|been delivered)",
                "",
                clean_subject,
                flags=re.IGNORECASE,
            )
            if clean_subject and len(clean_subject) > 5:
                suggested_data["package_description"] = clean_subject

        return suggested_data
