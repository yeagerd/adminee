"""
Instructor-based data models for LLM parsing of shipping emails.

This module defines structured data models that can be used with the Instructor
package to extract shipping information from emails using LLMs.
"""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ShipmentStatus(str, Enum):
    """Enumeration of possible shipment statuses."""

    CONFIRMED = "confirmed"
    PENDING = "pending"
    PACKING = "packing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class ShipmentInfo(BaseModel):
    """
    Structured information extracted from shipping emails using LLM.

    All fields are optional to handle cases where information is not available
    or cannot be reliably extracted.
    """

    # Core shipping information
    is_order_update: Optional[bool] = Field(
        default=None,
        description="Whether this email is related to an order/shipment update",
    )

    shipment_status: Optional[ShipmentStatus] = Field(
        default=None, description="Current status of the shipment"
    )

    order_number: Optional[str] = Field(
        default=None, description="Order number or order ID from the email"
    )

    tracking_number: Optional[str] = Field(
        default=None, description="Tracking number for the shipment"
    )

    # Delivery information
    estimated_delivery: Optional[date] = Field(
        default=None, description="Estimated delivery date (YYYY-MM-DD format)"
    )

    # Vendor and package information
    vendor_name: Optional[str] = Field(
        default=None, description="Name of the vendor or retailer"
    )

    package_description: Optional[str] = Field(
        default=None, description="Description of the package contents"
    )

    # Recipient information
    recipient_name: Optional[str] = Field(
        default=None, description="Name of the recipient"
    )

    # Additional metadata
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the extracted information (0.0 to 1.0)",
    )

    notes: Optional[str] = Field(
        default=None, description="Additional notes or observations about the email"
    )


class ShipmentInfoWithContext(ShipmentInfo):
    """
    Extended shipment information that includes context about what was already known.

    This is used when we have some information from regex parsing and want the LLM
    to fill in missing details.
    """

    # Context about what we already know
    known_carrier: Optional[str] = Field(
        default=None,
        description="Carrier that was already detected (e.g., UPS, FedEx, USPS)",
    )

    known_tracking_number: Optional[str] = Field(
        default=None, description="Tracking number that was already extracted"
    )

    known_order_number: Optional[str] = Field(
        default=None, description="Order number that was already extracted"
    )

    # Instructions for what to extract
    extract_instructions: Optional[str] = Field(
        default=None,
        description="Specific instructions for what information to extract",
    )
