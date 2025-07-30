"""
Pydantic schemas for email parser functionality
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EmailParseRequest(BaseModel):
    """Request schema for email parsing"""

    subject: str = Field(..., description="Email subject line")
    sender: str = Field(..., description="Email sender address")
    body: str = Field(..., description="Email body content (HTML or text)")
    content_type: str = Field(
        default="text", description="Content type: 'text' or 'html'"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subject": "Your Amazon order has shipped",
                "sender": "shipment-tracking@amazon.com",
                "body": "Your order #123-4567890-1234567 has shipped via UPS. Tracking number: 1Z999AA1234567890",
                "content_type": "text",
            }
        }
    )


class ParsedTrackingInfo(BaseModel):
    """Individual tracking information found in email"""

    tracking_number: str = Field(..., description="Extracted tracking number")
    carrier: Optional[str] = Field(None, description="Detected carrier name")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this detection"
    )
    source: str = Field(
        ...,
        description="Where this information was found: 'subject', 'body', or 'both'",
    )


class EmailParseResponse(BaseModel):
    """Response schema for email parsing"""

    is_shipment_email: bool = Field(
        ..., description="Whether this appears to be a shipment email"
    )
    detected_carrier: Optional[str] = Field(
        None, description="Primary detected carrier"
    )
    tracking_numbers: List[ParsedTrackingInfo] = Field(
        default_factory=list, description="List of tracking numbers found"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence score"
    )
    detected_from: str = Field(
        ...,
        description="Where detection was based: 'sender', 'subject', 'body', or 'multiple'",
    )
    suggested_package_data: Optional[dict] = Field(
        None, description="Suggested package data for creating tracking entry"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_shipment_email": True,
                "detected_carrier": "amazon",
                "tracking_numbers": [
                    {
                        "tracking_number": "1Z999AA1234567890",
                        "carrier": "ups",
                        "confidence": 0.95,
                        "source": "body",
                    }
                ],
                "confidence": 0.85,
                "detected_from": "multiple",
                "suggested_package_data": {
                    "carrier": "ups",
                    "tracking_number": "1Z999AA1234567890",
                    "status": "in_transit",
                },
            }
        }
    )


class EmailParseError(BaseModel):
    """Error response for email parsing failures"""

    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    error_code: str = Field(..., description="Error code for client handling")
