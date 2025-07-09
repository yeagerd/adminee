"""
Unified email endpoints for the Office Service.

Provides endpoints for reading email messages across Google and Microsoft providers,
with unified data models, caching, and parallel API calls for optimal performance.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException, Path, Query

from services.office.core.api_client_factory import APIClientFactory
from services.office.core.cache_manager import cache_manager, generate_cache_key
from services.office.core.clients.google import GoogleAPIClient
from services.office.core.clients.microsoft import MicrosoftAPIClient
from services.office.core.normalizer import (
    normalize_google_email,
    normalize_microsoft_email,
)
from services.office.models import Provider
from services.office.schemas import (
    EmailMessage,
    EmailMessageList,
    SendEmailRequest,
    SendEmailResponse,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/email", tags=["email"])

# Initialize dependencies
api_client_factory = APIClientFactory()


@router.get("/messages", response_model=EmailMessageList)
async def get_email_messages(
    user_id: str = Query(..., description="ID of the user to fetch emails for"),
    providers: Optional[List[str]] = Query(
        None,
        description="Providers to fetch from (google, microsoft). If not specified, fetches from all available providers",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of messages to return per provider",
    ),
    include_body: bool = Query(
        False, description="Whether to include message body content"
    ),
    labels: Optional[List[str]] = Query(
        None, description="Filter by labels (inbox, sent, etc.)"
    ),
    q: Optional[str] = Query(None, description="Search query to filter messages"),
    page_token: Optional[str] = Query(
        None, description="Pagination token for next page"
    ),
):
    """
    Get unified email messages from multiple providers.

    Fetches email messages from Google Gmail and Microsoft Outlook APIs,
    normalizes them to a unified format, and returns aggregated results.
    Responses are cached for improved performance.

    Args:
        user_id: ID of the user to fetch emails for
        providers: List of providers to query (defaults to all available)
        limit: Maximum messages per provider
        include_body: Whether to include full message bodies
        labels: Filter by message labels/categories
        q: Search query string
        page_token: Pagination token

    Returns:
        EmailMessageList with aggregated email messages
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] Email messages request: user_id={user_id}, providers={providers}, limit={limit}"
    )

    try:
        # Default to all providers if not specified
        if not providers:
            providers = ["google", "microsoft"]

        # Validate providers
        valid_providers = []
        for provider in providers:
            if provider.lower() in ["google", "microsoft"]:
                valid_providers.append(provider.lower())
            else:
                logger.warning(f"[{request_id}] Invalid provider: {provider}")

        if not valid_providers:
            raise HTTPException(status_code=400, detail="No valid providers specified")

        # Build cache key
        cache_params = {
            "providers": valid_providers,
            "limit": limit,
            "include_body": include_body,
            "labels": labels or [],
            "q": q or "",
            "page_token": page_token or "",
        }
        cache_key = generate_cache_key(user_id, "unified", "messages", cache_params)

        # Check cache first
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result:
            logger.info(f"[{request_id}] Cache hit for email messages")
            return EmailMessageList(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch from providers in parallel
        tasks = []
        for provider in valid_providers:
            task = fetch_provider_emails(
                request_id,
                user_id,
                provider,
                limit,
                include_body,
                labels,
                q,
                page_token,
            )
            tasks.append(task)

        # Execute parallel requests
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        aggregated_messages: List[EmailMessage] = []
        provider_errors = {}
        providers_used = []

        for i, result in enumerate(provider_results):
            provider = valid_providers[i]

            if isinstance(result, Exception):
                logger.error(f"[{request_id}] Provider {provider} failed: {result}")
                provider_errors[provider] = str(result)
            elif result is not None and not isinstance(result, BaseException):
                try:
                    # Type narrowing: result should be tuple[List[EmailMessage], str]
                    messages, provider_name = result
                    aggregated_messages.extend(messages)
                    providers_used.append(provider_name)
                    logger.info(
                        f"[{request_id}] Provider {provider} returned {len(messages)} messages"
                    )
                except (TypeError, ValueError) as e:
                    logger.error(
                        f"[{request_id}] Invalid result format from {provider}: {e}"
                    )
                    provider_errors[provider] = f"Invalid result format: {e}"

        # Sort messages by date (newest first)
        aggregated_messages.sort(key=lambda msg: msg.date, reverse=True)

        # Apply global limit if we have results from multiple providers
        if len(providers_used) > 1:
            aggregated_messages = aggregated_messages[: limit * 2]  # Allow some overlap

        # Build response
        response_data = {
            "messages": [msg.model_dump() for msg in aggregated_messages],
            "total_count": len(aggregated_messages),
            "providers_used": providers_used,
            "provider_errors": provider_errors if provider_errors else None,
            "has_more": len(aggregated_messages) >= limit,  # Simple heuristic
            "request_metadata": {
                "user_id": user_id,
                "providers_requested": valid_providers,
                "limit": limit,
                "include_body": include_body,
            },
        }

        # Cache the result for 15 minutes
        await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=900)

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Email messages request completed in {response_time_ms}ms"
        )

        return EmailMessageList(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=(
                Provider(providers_used[0]) if len(providers_used) == 1 else None
            ),
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Email messages request failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch email messages: {str(e)}"
        )


@router.get("/messages/{message_id}", response_model=EmailMessageList)
async def get_email_message(
    message_id: str = Path(..., description="Message ID (format: provider_originalId)"),
    user_id: str = Query(..., description="ID of the user who owns the message"),
    include_body: bool = Query(
        True, description="Whether to include message body content"
    ),
):
    """
    Get a specific email message by ID.

    The message_id should be in the format "provider_originalId" (e.g., "gmail_abc123" or "outlook_xyz789").
    This endpoint determines the correct provider from the message ID and fetches the full message details.

    Args:
        message_id: Message ID with provider prefix
        user_id: ID of the user who owns the message
        include_body: Whether to include full message body

    Returns:
        EmailMessageList with the specific email message
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] Email message detail request: message_id={message_id}, user_id={user_id}"
    )

    try:
        # Parse provider from message_id
        provider, original_message_id = parse_message_id(message_id)

        # Build cache key
        cache_params = {"message_id": message_id, "include_body": include_body}
        cache_key = generate_cache_key(
            user_id, provider, "message_detail", cache_params
        )

        # Check cache first
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result:
            logger.info(f"[{request_id}] Cache hit for message detail")
            return EmailMessageList(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch from the specific provider
        message = await fetch_single_message(
            request_id, user_id, provider, original_message_id, include_body
        )

        if not message:
            raise HTTPException(
                status_code=404, detail=f"Message {message_id} not found"
            )

        # Build response
        response_data = {
            "message": message.model_dump(),
            "provider": provider,
            "request_metadata": {
                "user_id": user_id,
                "message_id": message_id,
                "include_body": include_body,
            },
        }

        # Cache the result for 1 hour (messages don't change often)
        await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=3600)

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Message detail request completed in {response_time_ms}ms"
        )

        return EmailMessageList(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=Provider(provider),
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Message detail request failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch message: {str(e)}"
        )


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    email_data: SendEmailRequest,
    user_id: str = Query(..., description="ID of the user sending the email"),
):
    """
    Send an email through a specific provider.

    For the MVP, this is a simple pass-through that determines the provider
    and makes the API call. In a production system, this would typically
    queue the email for asynchronous processing.

    Args:
        email_data: Email content and configuration
        user_id: ID of the user sending the email

    Returns:
        SendEmailResponse with sent message details
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] Send email request: user_id={user_id}, "
        f"to={[addr.email for addr in email_data.to]}, subject='{email_data.subject}'"
    )

    try:
        # Determine provider (default to google if not specified)
        provider = email_data.provider or "google"

        # Validate provider
        if provider.lower() not in ["google", "microsoft"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider: {provider}. Must be 'google' or 'microsoft'",
            )

        provider = provider.lower()

        # Get API client for provider
        client = await api_client_factory.create_client(user_id, provider)
        if client is None:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to create API client for provider {provider}. "
                "User may not have connected this provider.",
            )

        # Send email based on provider
        sent_message_data = None

        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                sent_message_data = await send_gmail_message(
                    request_id, google_client, email_data
                )
            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                sent_message_data = await send_outlook_message(
                    request_id, microsoft_client, email_data
                )

        # Build response
        response_data = {
            "message_id": sent_message_data.get("id") if sent_message_data else None,
            "provider": provider,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "request_metadata": {
                "user_id": user_id,
                "to": [addr.email for addr in email_data.to],
                "subject": email_data.subject,
                "provider": provider,
            },
        }

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Email sent successfully in {response_time_ms}ms via {provider}"
        )

        return SendEmailResponse(
            success=True,
            data=response_data,
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Send email request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


async def send_gmail_message(
    request_id: str, client: GoogleAPIClient, email_data: SendEmailRequest
) -> Dict[str, Any]:
    """
    Send an email via Gmail API.

    Args:
        request_id: Request tracking ID
        client: Google API client
        email_data: Email content and configuration

    Returns:
        Dictionary containing sent message details
    """
    try:
        # Build Gmail message data
        # For simplicity in MVP, we'll create a basic message structure
        # In production, this would handle HTML formatting, attachments, etc.

        # Convert to Gmail API format
        to_addresses = [addr.email for addr in email_data.to]
        cc_addresses = [addr.email for addr in email_data.cc] if email_data.cc else []
        bcc_addresses = (
            [addr.email for addr in email_data.bcc] if email_data.bcc else []
        )

        # Build basic email content (simplified for MVP)
        message_content = {
            "raw": _build_gmail_raw_message(
                to_addresses=to_addresses,
                cc_addresses=cc_addresses,
                bcc_addresses=bcc_addresses,
                subject=email_data.subject,
                body=email_data.body,
            )
        }

        # Send the message
        result = await client.send_message(message_content)

        logger.info(
            f"[{request_id}] Gmail message sent successfully: {result.get('id')}"
        )
        return result

    except Exception as e:
        logger.error(f"[{request_id}] Failed to send Gmail message: {e}")
        raise


async def send_outlook_message(
    request_id: str, client: MicrosoftAPIClient, email_data: SendEmailRequest
) -> Dict[str, Any]:
    """
    Send an email via Microsoft Graph API.

    Args:
        request_id: Request tracking ID
        client: Microsoft API client
        email_data: Email content and configuration

    Returns:
        Dictionary containing sent message details
    """
    try:
        # Build Microsoft Graph message data
        to_recipients = [
            {"emailAddress": {"address": addr.email, "name": addr.name or addr.email}}
            for addr in email_data.to
        ]

        cc_recipients = []
        if email_data.cc:
            cc_recipients = [
                {
                    "emailAddress": {
                        "address": addr.email,
                        "name": addr.name or addr.email,
                    }
                }
                for addr in email_data.cc
            ]

        bcc_recipients = []
        if email_data.bcc:
            bcc_recipients = [
                {
                    "emailAddress": {
                        "address": addr.email,
                        "name": addr.name or addr.email,
                    }
                }
                for addr in email_data.bcc
            ]

        message_data = {
            "message": {
                "subject": email_data.subject,
                "body": {
                    "contentType": "Text",  # Could be "HTML" for rich content
                    "content": email_data.body,
                },
                "toRecipients": to_recipients,
                "ccRecipients": cc_recipients,
                "bccRecipients": bcc_recipients,
            }
        }

        # Add importance if specified
        if email_data.importance:
            importance_map = {"low": "low", "normal": "normal", "high": "high"}
            if email_data.importance.lower() in importance_map:
                message_data["message"]["importance"] = importance_map[
                    email_data.importance.lower()
                ]

        # Send the message
        await client.send_message(message_data)

        # Microsoft Graph sendMail doesn't return the sent message details
        # We'll return a simple confirmation
        result = {"id": f"outlook_sent_{request_id}", "status": "sent"}

        logger.info(f"[{request_id}] Outlook message sent successfully")
        return result

    except Exception as e:
        logger.error(f"[{request_id}] Failed to send Outlook message: {e}")
        raise


def _build_gmail_raw_message(
    to_addresses: List[str],
    cc_addresses: List[str],
    bcc_addresses: List[str],
    subject: str,
    body: str,
) -> str:
    """
    Build a raw Gmail message in RFC 2822 format.

    This is a simplified implementation for the MVP.
    In production, you'd use a proper email library like email.mime.
    """
    import base64
    from email.mime.text import MIMEText

    # Create MIMEText message
    msg = MIMEText(body)
    msg["To"] = ", ".join(to_addresses)
    if cc_addresses:
        msg["Cc"] = ", ".join(cc_addresses)
    if bcc_addresses:
        msg["Bcc"] = ", ".join(bcc_addresses)
    msg["Subject"] = subject

    # Encode to base64 for Gmail API
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return raw_message


async def fetch_provider_emails(
    request_id: str,
    user_id: str,
    provider: str,
    limit: int,
    include_body: bool,
    labels: Optional[List[str]],
    q: Optional[str],
    page_token: Optional[str],
) -> tuple[List[EmailMessage], str]:
    """
    Fetch emails from a specific provider.

    Args:
        request_id: Request tracking ID
        user_id: User ID
        provider: Provider name (google, microsoft)
        limit: Maximum number of messages
        include_body: Whether to include message bodies
        labels: Label filters
        q: Search query
        page_token: Pagination token

    Returns:
        Tuple of (messages list, provider name)
    """
    try:
        # Get API client for provider
        client = await api_client_factory.create_client(user_id, provider)
        if client is None:
            raise ValueError(f"Failed to create API client for provider {provider}")

        # Use client as async context manager
        async with client:
            # Build provider-specific parameters
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                # Fetch messages from Gmail
                messages_response = await google_client.get_messages(
                    max_results=limit, page_token=page_token, query=q
                )
                messages = messages_response.get("messages", [])

                # Normalize messages
                normalized_messages = []
                for msg_summary in messages:
                    # Fetch full message if we only got summaries
                    if include_body or "payload" not in msg_summary:
                        full_message = await google_client.get_message(
                            msg_summary["id"]
                        )
                    else:
                        full_message = msg_summary

                    # Get user account info (simplified - in real implementation would cache this)
                    # Handle case where user_id is already an email address
                    if "@" in user_id:
                        account_email = user_id
                        account_name = f"Gmail Account ({user_id.split('@')[0]})"
                    else:
                        account_email = f"{user_id}@gmail.com"  # Placeholder
                        account_name = f"Gmail Account ({user_id})"  # Placeholder

                    normalized_msg = normalize_google_email(
                        full_message, account_email, account_name
                    )
                    normalized_messages.append(normalized_msg)

            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)

                # Build filter for labels (categories in Microsoft)
                filter_expr = None
                if labels:
                    category_filter = " or ".join(
                        [f"categories/any(c:c eq '{label}')" for label in labels]
                    )
                    filter_expr = category_filter

                # Convert page_token to skip value
                skip_value = 0
                if page_token:
                    try:
                        skip_value = int(page_token)
                    except (ValueError, TypeError):
                        skip_value = 0

                # Fetch messages from Outlook
                messages_response = await microsoft_client.get_messages(
                    top=limit,
                    skip=skip_value,
                    filter=filter_expr,
                    search=q,
                    order_by="receivedDateTime desc",
                )
                messages = messages_response.get("value", [])

                # Normalize messages
                normalized_messages = []
                for msg in messages:
                    # Get user account info (simplified - in real implementation would cache this)
                    # Handle case where user_id is already an email address
                    if "@" in user_id:
                        account_email = user_id
                        account_name = f"Outlook Account ({user_id.split('@')[0]})"
                    else:
                        account_email = f"{user_id}@outlook.com"  # Placeholder
                        account_name = f"Outlook Account ({user_id})"  # Placeholder

                    normalized_msg = normalize_microsoft_email(
                        msg, account_email, account_name
                    )
                    normalized_messages.append(normalized_msg)

            else:
                raise ValueError(f"Unsupported provider: {provider}")

            logger.info(
                f"[{request_id}] Successfully fetched {len(normalized_messages)} messages from {provider}"
            )
            return normalized_messages, provider

    except Exception as e:
        logger.error(f"[{request_id}] Failed to fetch emails from {provider}: {e}")
        raise


async def fetch_single_message(
    request_id: str,
    user_id: str,
    provider: str,
    original_message_id: str,
    include_body: bool,
) -> Optional[EmailMessage]:
    """
    Fetch a single email message from a specific provider.

    Args:
        request_id: Request tracking ID
        user_id: User ID
        provider: Provider name
        original_message_id: Original provider message ID
        include_body: Whether to include message body

    Returns:
        EmailMessage or None if not found
    """
    try:
        # Get API client for provider
        client = await api_client_factory.create_client(user_id, provider)
        if client is None:
            raise ValueError(f"Failed to create API client for provider {provider}")

        # Use client as async context manager
        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                # Fetch message from Gmail
                message = await google_client.get_message(
                    original_message_id, format="full" if include_body else "metadata"
                )

                # Get user account info (simplified)
                # Handle case where user_id is already an email address
                if "@" in user_id:
                    account_email = user_id
                    account_name = f"Gmail Account ({user_id.split('@')[0]})"
                else:
                    account_email = f"{user_id}@gmail.com"  # Placeholder
                    account_name = f"Gmail Account ({user_id})"  # Placeholder

                return normalize_google_email(message, account_email, account_name)

            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                # Fetch message from Outlook
                message = await microsoft_client.get_message(original_message_id)

                # Get user account info (simplified)
                # Handle case where user_id is already an email address
                if "@" in user_id:
                    account_email = user_id
                    account_name = f"Outlook Account ({user_id.split('@')[0]})"
                else:
                    account_email = f"{user_id}@outlook.com"  # Placeholder
                    account_name = f"Outlook Account ({user_id})"  # Placeholder

                return normalize_microsoft_email(message, account_email, account_name)

            else:
                raise ValueError(f"Unsupported provider: {provider}")

    except Exception as e:
        logger.error(
            f"[{request_id}] Failed to fetch message {original_message_id} from {provider}: {e}"
        )
        return None


def parse_message_id(message_id: str) -> tuple[str, str]:
    """
    Parse a unified message ID to extract provider and original ID.

    Args:
        message_id: Unified message ID (format: "provider_originalId")

    Returns:
        Tuple of (provider, original_message_id)

    Raises:
        HTTPException: If message ID format is invalid
    """
    try:
        if "_" not in message_id:
            raise ValueError("Invalid message ID format")

        parts = message_id.split("_", 1)
        provider_prefix = parts[0].lower()
        original_id = parts[1]

        # Map provider prefixes to standard names
        provider_map = {
            "gmail": "google",
            "google": "google",
            "outlook": "microsoft",
            "microsoft": "microsoft",
        }

        provider = provider_map.get(provider_prefix)
        if not provider:
            raise ValueError(f"Unknown provider prefix: {provider_prefix}")

        return provider, original_id

    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid message ID format: {message_id}. Expected format: 'provider_originalId'",
        )
