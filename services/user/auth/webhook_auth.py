"""
Webhook signature verification for User Management Service.

Handles verification of webhook signatures from external providers like Clerk.
"""

import hashlib
import hmac
import logging
from typing import Optional

from fastapi import Request

from services.common.http_errors import AuthError, ServiceError, ValidationError
from services.user.settings import get_settings

logger = logging.getLogger(__name__)


class WebhookSignatureVerifier:
    """Utility class for webhook signature verification."""

    @staticmethod
    def verify_clerk_signature(
        payload: bytes, signature_header: Optional[str], timestamp_header: Optional[str]
    ) -> None:
        """
        Verify Clerk webhook signature.

        Args:
            payload: Raw webhook payload bytes
            signature_header: The svix-signature header value
            timestamp_header: The svix-timestamp header value

        Raises:
            WebhookValidationException: If signature verification fails
        """
        if not get_settings().clerk_webhook_secret:
            logger.warning("Clerk webhook secret not configured, skipping verification")
            return

        if not signature_header:
            raise ValidationError(
                message="Missing signature header", details={"provider": "clerk"}
            )

        if not timestamp_header:
            raise ValidationError(
                message="Missing timestamp header", details={"provider": "clerk"}
            )

        try:
            # Parse signature header (format: "v1=signature1,v1=signature2,...")
            signatures = WebhookSignatureVerifier._parse_signature_header(
                signature_header
            )

            # Construct the signed payload
            signed_payload = f"{timestamp_header}.{payload.decode('utf-8')}"

            # Verify against each signature
            expected_signature = WebhookSignatureVerifier._compute_clerk_signature(
                signed_payload, get_settings().clerk_webhook_secret or ""
            )

            signature_valid = any(
                hmac.compare_digest(expected_signature, sig) for sig in signatures
            )

            if not signature_valid:
                raise ValidationError(
                    message="Invalid signature", details={"provider": "clerk"}
                )

            logger.debug("Clerk webhook signature verified successfully")

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            logger.error(f"Webhook signature verification failed: {str(e)}")
            raise ValidationError(
                message=f"Signature verification error: {str(e)}",
                details={"provider": "clerk"},
            )

    @staticmethod
    def _parse_signature_header(signature_header: str) -> list:
        """
        Parse Clerk signature header format.

        Args:
            signature_header: Header value like "v1=signature1,v1=signature2"

        Returns:
            list: List of signature values
        """
        signatures = []
        for part in signature_header.split(","):
            if "=" in part:
                version, signature = part.split("=", 1)
                if version.strip() == "v1":
                    signatures.append(signature.strip())
        return signatures

    @staticmethod
    def _compute_clerk_signature(payload: str, secret: str) -> str:
        """
        Compute HMAC-SHA256 signature for Clerk webhook.

        Args:
            payload: The signed payload string
            secret: Webhook secret key

        Returns:
            str: Base64-encoded signature
        """
        import base64

        # Clerk uses base64-encoded secret
        key = base64.b64decode(secret)
        signature = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(signature).decode("utf-8")


async def verify_webhook_signature(request: Request) -> None:
    """
    FastAPI dependency to verify webhook signatures.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If signature verification fails
    """
    try:
        # Get signature headers
        signature_header = request.headers.get("svix-signature")
        timestamp_header = request.headers.get("svix-timestamp")

        # Read request body
        body = await request.body()

        # Verify signature
        WebhookSignatureVerifier.verify_clerk_signature(
            body, signature_header, timestamp_header
        )

    except ValidationError as e:
        logger.warning(f"Webhook signature verification failed: {e.message}")
        raise AuthError(message=e.message)
    except Exception as e:
        logger.error(f"Webhook verification error: {str(e)}")
        raise ServiceError(message="Internal verification error")
