"""
Webhook handling router.

Handles incoming webhooks from external providers (Clerk, OAuth providers)
with signature verification and event processing.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..auth.webhook_auth import verify_webhook_signature
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
    try:
        start_time = datetime.now(timezone.utc)
        event_type = None

        # Parse the webhook payload
        try:
            webhook_data = await request.json()
            event_type = webhook_data.get("type")
            data = webhook_data.get("data", {})
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook payload format",
            )

        logger.info(f"Processing Clerk webhook: {event_type} for user {data.get('id')}")

        # Process the webhook based on event type
        if event_type == "user.created":
            result = await webhook_service.process_user_created(data)
        elif event_type == "user.updated":
            result = await webhook_service.process_user_updated(data)
        elif event_type == "user.deleted":
            result = await webhook_service.process_user_deleted(data)
        else:
            logger.warning(f"Unsupported webhook event type: {event_type}")
            return {"status": "ignored", "message": f"Unsupported event: {event_type}"}

        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            f"Webhook processed successfully: {event_type} in {processing_time:.3f}s"
        )

        return {
            "status": "success",
            "event_type": event_type,
            "processed_at": datetime.now(timezone.utc),
            "processing_time": processing_time,
            "result": result,
        }

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
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
            processed_at=datetime.now(timezone.utc),
            event_id=event.data.id,
        )

    except Exception as e:
        logger.error(f"Test webhook processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "TestWebhookError",
                "message": f"Test webhook processing failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
