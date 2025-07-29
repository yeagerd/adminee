"""
Data collection router for storing user-corrected shipment data
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.common.logging_config import get_logger
from services.shipments.service_auth import service_permission_required

logger = get_logger(__name__)

router = APIRouter()


class DataCollectionRequest(BaseModel):
    """Request schema for collecting user-corrected shipment data"""
    user_id: str = Field(..., description="User ID")
    email_message_id: str = Field(..., description="Original email message ID")
    original_email_data: Dict[str, Any] = Field(..., description="Original email content")
    auto_detected_data: Dict[str, Any] = Field(..., description="Auto-detected shipment data")
    user_corrected_data: Dict[str, Any] = Field(..., description="User-corrected shipment data")
    detection_confidence: float = Field(..., ge=0.0, le=1.0, description="Original detection confidence")
    correction_reason: Optional[str] = Field(None, description="Reason for user correction")
    consent_given: bool = Field(..., description="Whether user has given consent for data collection")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user123",
                "email_message_id": "email456",
                "original_email_data": {
                    "subject": "Your Amazon order has shipped",
                    "sender": "shipment-tracking@amazon.com",
                    "body": "Your order #123-4567890-1234567 has shipped via UPS. Tracking number: 1Z999AA1234567890"
                },
                "auto_detected_data": {
                    "tracking_number": "1Z999AA1234567890",
                    "carrier": "amazon",
                    "confidence": 0.85
                },
                "user_corrected_data": {
                    "tracking_number": "1Z999AA1234567890",
                    "carrier": "ups",
                    "status": "in_transit"
                },
                "detection_confidence": 0.85,
                "correction_reason": "Carrier was incorrectly identified as Amazon instead of UPS",
                "consent_given": True
            }
        }


class DataCollectionResponse(BaseModel):
    """Response schema for data collection"""
    success: bool = Field(..., description="Whether data collection was successful")
    collection_id: str = Field(..., description="Unique identifier for this data collection entry")
    timestamp: datetime = Field(..., description="When the data was collected")
    message: str = Field(..., description="Response message")


@router.post("/collect", response_model=DataCollectionResponse)
async def collect_shipment_data(
    request: DataCollectionRequest,
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> DataCollectionResponse:
    """
    Collect user-corrected shipment data for service improvements
    
    This endpoint stores:
    - Original email content
    - Auto-detected shipment information
    - User corrections and improvements
    - Detection confidence scores
    
    This data is used to improve the accuracy of future shipment detection.
    """
    try:
        # Validate user consent
        if not request.consent_given:
            logger.warning("Data collection attempted without user consent", 
                          user_id=request.user_id, email_id=request.email_message_id)
            raise HTTPException(
                status_code=403,
                detail="Data collection requires explicit user consent"
            )
        
        # Generate collection ID
        collection_id = f"collection_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request.user_id[:8]}"
        
        # Log the data collection (in production, this would be stored in a database)
        logger.info("Collecting shipment data for improvements",
                   collection_id=collection_id,
                   user_id=request.user_id,
                   email_id=request.email_message_id,
                   confidence=request.detection_confidence,
                   has_corrections=bool(request.correction_reason))
        
        # TODO: Store data in database for training improvements
        # For now, we'll just log the data structure
        training_data = {
            "collection_id": collection_id,
            "user_id": request.user_id,
            "email_message_id": request.email_message_id,
            "original_email_data": request.original_email_data,
            "auto_detected_data": request.auto_detected_data,
            "user_corrected_data": request.user_corrected_data,
            "detection_confidence": request.detection_confidence,
            "correction_reason": request.correction_reason,
            "consent_given": request.consent_given,
            "collected_at": datetime.utcnow().isoformat(),
        }
        
        # In a real implementation, this would be stored in a database
        # For now, we'll just log it for demonstration
        logger.info("Training data structure", training_data=training_data)
        
        return DataCollectionResponse(
            success=True,
            collection_id=collection_id,
            timestamp=datetime.utcnow(),
            message="Shipment data collected successfully for service improvements"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error collecting shipment data", 
                    error=str(e), 
                    user_id=request.user_id,
                    email_id=request.email_message_id,
                    exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to collect shipment data",
                "details": str(e),
                "error_code": "COLLECTION_ERROR"
            }
        )


@router.get("/stats")
async def get_collection_stats(
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> Dict[str, Any]:
    """
    Get statistics about data collection (for admin/monitoring purposes)
    """
    try:
        # TODO: Implement actual statistics from database
        # For now, return placeholder stats
        stats = {
            "total_collections": 0,
            "collections_today": 0,
            "average_confidence": 0.0,
            "correction_rate": 0.0,
            "top_correction_reasons": [],
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return stats
        
    except Exception as e:
        logger.error("Error getting collection stats", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve collection statistics"
        ) 