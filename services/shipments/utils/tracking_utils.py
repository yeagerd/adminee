"""
Utilities for tracking number normalization and validation
"""

import re
from typing import Optional


def normalize_tracking_number(
    tracking_number: str, carrier: Optional[str] = None
) -> str:
    """
    Normalize tracking number based on carrier-specific rules.

    Args:
        tracking_number: Raw tracking number
        carrier: Carrier name (optional, for carrier-specific rules)

    Returns:
        Normalized tracking number
    """
    if not tracking_number:
        return tracking_number

    # Remove common separators and whitespace
    normalized = re.sub(r"[\s\-_\.]", "", tracking_number.strip())

    # Carrier-specific normalization
    if carrier:
        carrier_lower = carrier.lower()

        if carrier_lower == "ups":
            # UPS tracking numbers are typically uppercase
            normalized = normalized.upper()

        elif carrier_lower == "fedex":
            # FedEx tracking numbers are typically uppercase
            normalized = normalized.upper()

        elif carrier_lower == "usps":
            # USPS tracking numbers are typically uppercase
            normalized = normalized.upper()

        elif carrier_lower == "dhl":
            # DHL tracking numbers are typically uppercase
            normalized = normalized.upper()

        elif carrier_lower == "amazon":
            # Amazon tracking numbers can be mixed case, but often uppercase
            # TBA numbers are typically uppercase
            if normalized.startswith("TBA"):
                normalized = normalized.upper()
            else:
                # For other Amazon tracking numbers, preserve case but ensure consistency
                normalized = normalized.upper()

    return normalized


def validate_tracking_number_format(
    tracking_number: str, carrier: Optional[str] = None
) -> bool:
    """
    Validate tracking number format based on carrier patterns.

    Args:
        tracking_number: Tracking number to validate
        carrier: Carrier name (optional, for carrier-specific validation)

    Returns:
        True if format is valid, False otherwise
    """
    if not tracking_number:
        return False

    normalized = normalize_tracking_number(tracking_number, carrier)

    if carrier:
        carrier_lower = carrier.lower()

        if carrier_lower == "ups":
            # UPS: 1Z + 16 alphanumeric characters, or 9-12 digits
            return bool(
                re.match(r"^1Z[0-9A-Z]{16}$", normalized)
                or re.match(r"^[0-9]{9}$", normalized)
                or re.match(r"^[0-9]{10}$", normalized)
                or re.match(r"^[0-9]{12}$", normalized)
            )

        elif carrier_lower == "fedex":
            # FedEx: 12, 15, or 22 digits
            return bool(
                re.match(r"^[0-9]{12}$", normalized)
                or re.match(r"^[0-9]{15}$", normalized)
                or re.match(r"^[0-9]{22}$", normalized)
            )

        elif carrier_lower == "usps":
            # USPS: 13, 15, 20, 22, or 26 digits
            return bool(
                re.match(r"^[0-9]{13}$", normalized)
                or re.match(r"^[0-9]{15}$", normalized)
                or re.match(r"^[0-9]{20}$", normalized)
                or re.match(r"^[0-9]{22}$", normalized)
                or re.match(r"^[0-9]{26}$", normalized)
            )

        elif carrier_lower == "dhl":
            # DHL: 10-13 digits
            return bool(
                re.match(r"^[0-9]{10}$", normalized)
                or re.match(r"^[0-9]{11}$", normalized)
                or re.match(r"^[0-9]{12}$", normalized)
                or re.match(r"^[0-9]{13}$", normalized)
            )

        elif carrier_lower == "amazon":
            # Amazon: TBA + 10 digits, or 1Z + 16 alphanumeric, or 10+ digits
            return bool(
                re.match(r"^TBA[0-9]{10}$", normalized)
                or re.match(r"^1Z[0-9A-Z]{16}$", normalized)
                or re.match(r"^[0-9]{10,}$", normalized)
            )

    # Generic validation: at least 10 characters, alphanumeric
    return len(normalized) >= 10 and bool(re.match(r"^[0-9A-Z]+$", normalized))


def get_unique_constraint_key(user_id: str, tracking_number: str, carrier: str) -> str:
    """
    Generate a unique constraint key for tracking number validation.

    Args:
        user_id: User ID
        tracking_number: Normalized tracking number
        carrier: Carrier name

    Returns:
        Unique constraint key
    """
    normalized_tracking = normalize_tracking_number(tracking_number, carrier)
    normalized_carrier = carrier.lower().strip()
    return f"{user_id}:{normalized_tracking}:{normalized_carrier}"
