"""
Email parser router for detecting shipment information in emails
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from services.common.logging_config import get_logger
from services.shipments.email_parser import EmailParser
from services.shipments.schemas.email_parser import (
    EmailParseRequest,
    EmailParseResponse,
    ParsedTrackingInfo,
    EmailParseError
)
from services.shipments.service_auth import service_permission_required

logger = get_logger(__name__)

router = APIRouter()
email_parser = EmailParser()


@router.post("/parse", response_model=EmailParseResponse)
async def parse_email(
    request: EmailParseRequest,
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> EmailParseResponse:
    """
    Parse email content to detect shipment information
    
    This endpoint analyzes email content to identify:
    - Whether the email is related to shipments
    - Detected carriers (Amazon, UPS, FedEx, etc.)
    - Tracking numbers found in the email
    - Confidence scores for the detection
    
    Returns structured data that can be used to create package tracking entries.
    """
    try:
        logger.info("Parsing email for shipment information", 
                   subject_length=len(request.subject),
                   sender=request.sender,
                   content_type=request.content_type)
        
        # Parse the email using the EmailParser
        parsed_data = email_parser.parse_email(
            subject=request.subject,
            sender=request.sender,
            body=request.body,
            content_type=request.content_type
        )
        
        # Convert tracking numbers to ParsedTrackingInfo objects
        tracking_info = []
        for tracking_number in parsed_data.tracking_numbers:
            # Determine carrier for this tracking number
            carrier = parsed_data.detected_carrier
            if not carrier:
                # Try to detect carrier from tracking number format
                carrier = _detect_carrier_from_tracking_number(tracking_number)
            
            tracking_info.append(ParsedTrackingInfo(
                tracking_number=tracking_number,
                carrier=carrier,
                confidence=parsed_data.confidence,
                source=parsed_data.detected_from
            ))
        
        # Create response
        response = EmailParseResponse(
            is_shipment_email=parsed_data.is_shipment_email,
            detected_carrier=parsed_data.detected_carrier,
            tracking_numbers=tracking_info,
            confidence=parsed_data.confidence,
            detected_from=parsed_data.detected_from,
            suggested_package_data=parsed_data.suggested_package_data
        )
        
        logger.info("Email parsing completed", 
                   is_shipment=response.is_shipment_email,
                   carrier=response.detected_carrier,
                   tracking_count=len(response.tracking_numbers),
                   confidence=response.confidence)
        
        return response
        
    except Exception as e:
        logger.error("Error parsing email", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to parse email",
                "details": str(e),
                "error_code": "PARSE_ERROR"
            }
        )


def _detect_carrier_from_tracking_number(tracking_number: str) -> str:
    """
    Attempt to detect carrier from tracking number format
    
    This is a fallback when carrier detection from sender domain fails
    """
    tracking_number = tracking_number.upper()
    
    # UPS patterns
    if tracking_number.startswith('1Z') and len(tracking_number) == 18:
        return 'ups'
    
    # FedEx patterns
    if len(tracking_number) in [12, 15, 22] and tracking_number.isdigit():
        return 'fedex'
    
    # USPS patterns
    if len(tracking_number) in [20, 22, 13, 15] and tracking_number.isdigit():
        return 'usps'
    
    # DHL patterns
    if len(tracking_number) in [10, 11, 12, 13] and tracking_number.isdigit():
        return 'dhl'
    
    # Amazon patterns
    if tracking_number.startswith('TBA') and len(tracking_number) == 13:
        return 'amazon'
    
    return 'unknown' 