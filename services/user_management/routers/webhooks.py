"""
Webhook handling router.

Handles incoming webhooks from external providers (Clerk, OAuth providers)
with signature verification and event processing.
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
    responses={400: {"description": "Invalid webhook signature or payload"}},
)


@router.post("/clerk")
async def clerk_webhook():
    """
    Clerk webhook endpoint placeholder.

    TODO: Implement Clerk webhook processing for user.created, user.updated, user.deleted events
    with signature verification and idempotency.
    """
    return {"message": "Clerk webhook - to be implemented"}


@router.post("/oauth/{provider}")
async def oauth_webhook(provider: str):
    """
    OAuth provider webhook endpoint placeholder.

    TODO: Implement OAuth provider webhooks for token revocation and account changes.
    """
    return {"message": f"OAuth webhook for {provider} - to be implemented"}
