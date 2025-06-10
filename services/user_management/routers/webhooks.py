"""
Webhook handling router.

Handles incoming webhooks from external providers (Clerk, OAuth providers)
with signature verification and event processing.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..auth.webhook_auth import verify_webhook_signature
from ..exceptions import (
    DatabaseError,
    WebhookProcessingError,
)
from ..schemas.webhook import ClerkWebhookEvent, WebhookResponse
from ..services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
    responses={
        400: {"description": "Invalid webhook signature or payload"},
        401: {"description": "Webhook signature verification failed"},
        422: {"description": "Invalid webhook payload format"},
        500: {"description": "Internal webhook processing error"},
    },
)

webhook_service = WebhookService()


@router.post("/clerk", response_model=WebhookResponse)
async def clerk_webhook(
    request: Request,
    _: None = Depends(verify_webhook_signature),
) -> WebhookResponse:
    """
    Clerk webhook endpoint for user lifecycle events.

    Handles user.created, user.updated, and user.deleted events from Clerk
    with automatic signature verification and idempotency protection.

    Args:
        request: FastAPI request containing webhook payload
        _: Webhook signature verification dependency

    Returns:
        WebhookResponse: Processing result with success status and details

    Raises:
        HTTPException: For validation errors, processing failures, or signature issues
    """
    start_time = datetime.utcnow()
    event_type = None

    try:
        # Parse request body
        body = await request.body()
        payload = body.decode("utf-8")

        logger.info(f"Received Clerk webhook: {len(payload)} bytes")

        # Parse and validate webhook event
        try:
            event = ClerkWebhookEvent.model_validate_json(payload)
            event_type = event.type
            user_id = event.data.id

            logger.info(f"Processing {event_type} event for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "PayloadValidationError",
                    "message": f"Invalid webhook payload: {str(e)}",
                    "timestamp": start_time.isoformat(),
                },
            )

        # Process the webhook event
        try:
            result = await webhook_service.process_clerk_webhook(event)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Successfully processed {event_type} event for user {user_id} "
                f"in {processing_time:.3f}s: {result['action']}"
            )

            return WebhookResponse(
                success=True,
                message=f"Successfully processed {event_type} event",
                processed_at=datetime.utcnow(),
                event_id=user_id,
            )

        except WebhookProcessingError as e:
            logger.error(f"Webhook processing failed for {event_type}: {e.message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "WebhookProcessingError",
                    "message": e.message,
                    "event_type": event_type,
                    "timestamp": start_time.isoformat(),
                },
            )

        except DatabaseError as e:
            logger.error(f"Database error processing {event_type}: {e.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "DatabaseError",
                    "message": "Database operation failed",
                    "event_type": event_type,
                    "timestamp": start_time.isoformat(),
                },
            )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "event_type": event_type,
                "timestamp": start_time.isoformat(),
            },
        )


@router.post("/clerk/test", response_model=WebhookResponse)
async def test_clerk_webhook(
    event: ClerkWebhookEvent,
) -> WebhookResponse:
    """
    Test endpoint for Clerk webhook events (development only).

    Allows testing webhook processing without signature verification.
    Should be disabled in production environments.

    Args:
        event: Clerk webhook event payload

    Returns:
        WebhookResponse: Processing result
    """
    logger.warning("Using test webhook endpoint - should be disabled in production")

    try:
        result = await webhook_service.process_clerk_webhook(event)

        logger.info(f"Test webhook processed: {result['action']}")

        return WebhookResponse(
            success=True,
            message=f"Test webhook processed successfully: {result['action']}",
            processed_at=datetime.utcnow(),
            event_id=event.data.id,
        )

    except Exception as e:
        logger.error(f"Test webhook processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "TestWebhookError",
                "message": f"Test webhook processing failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@router.get("/health")
async def webhook_health() -> dict:
    """
    Webhook service health check endpoint.

    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "service": "webhook-handler",
        "timestamp": datetime.utcnow().isoformat(),
        "supported_providers": ["clerk"],
        "supported_events": ["user.created", "user.updated", "user.deleted"],
    }


@router.post("/oauth/{provider}")
async def oauth_webhook(provider: str):
    """
    OAuth provider webhook endpoint placeholder.

    TODO: Implement OAuth provider webhooks for token revocation and account changes.
    """
    logger.info(f"Received OAuth webhook for provider: {provider}")
    return {"message": f"OAuth webhook for {provider} - to be implemented"}
