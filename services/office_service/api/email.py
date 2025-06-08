import asyncio
import logging
from typing import List, Optional, Union, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, status
from datetime import datetime, timezone

from schemas.common_schemas import EmailMessage, ApiResponse, Provider
from core.dependencies import get_api_client_factory
from core.api_client_factory import APIClientFactory
from core.clients.google import GoogleAPIClient
from core.clients.microsoft import MicrosoftAPIClient
from core.normalizer import normalize_google_email, normalize_microsoft_email
from core.cache_manager import get_from_cache, set_to_cache, generate_cache_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["Email"])

def parse_providers(providers_str: Optional[str]) -> List[Provider]:
    if not providers_str:
        return [p for p in Provider]
    try:
        return [Provider(p.strip().lower()) for p in providers_str.split(',') if p.strip()]
    except ValueError as e:
        # Log the error for debugging
        logger.warning(f"Invalid provider string received: {providers_str}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid provider value in query parameters. Valid values are 'google', 'microsoft'. You provided: {providers_str}")


@router.get("/messages", response_model=ApiResponse[List[EmailMessage]])
async def list_email_messages(
    user_id: str,
    providers: Annotated[Optional[str], Query(description="Comma-separated list of providers (e.g., google,microsoft)")] = None,
    api_client_factory: APIClientFactory = Depends(get_api_client_factory)
):
    try:
        requested_providers = parse_providers(providers)
    except HTTPException as e:
        return ApiResponse[List[EmailMessage]](success=False, error={"type": "validation_error", "message": e.detail}, data=[])

    cache_params = {"providers": sorted([p.value for p in requested_providers])}
    cache_key = generate_cache_key(user_id=user_id, endpoint="email_messages_list", params=cache_params)

    cached_response = await get_from_cache(cache_key)
    if cached_response:
        try:
            restored_messages = [EmailMessage(**msg_data) for msg_data in cached_response]
            return ApiResponse[List[EmailMessage]](data=restored_messages, cache_hit=True, success=True)
        except Exception as e: # Handle potential validation errors during parsing
            logger.warning(f"Cache data for {cache_key} is stale or invalid: {e}")
            # Proceed to fetch fresh data instead of failing

    all_messages: List[EmailMessage] = []
    for provider_enum in requested_providers:
        client = await api_client_factory.get_client(user_id, provider_enum)
        if not client:
            logger.warning(f"Could not get client for provider {provider_enum.value} (email list) for user {user_id}")
            continue

        try:
            if isinstance(client, GoogleAPIClient):
                raw_result_list = await client.list_gmail_messages()
                if raw_result_list and 'messages' in raw_result_list:
                    for item_stub in raw_result_list.get("messages", []):
                        msg = EmailMessage(
                            id=f"google_{item_stub['id']}",
                            provider_message_id=item_stub['id'],
                            thread_id=item_stub.get('threadId'),
                            provider=Provider.GOOGLE,
                            account_email=user_id, # Placeholder
                            date=datetime.now(timezone.utc),
                            subject=f"Email Stub {item_stub['id']}",
                            snippet="Email content not fetched for list view (stub)."
                        )
                        all_messages.append(msg)
            elif isinstance(client, MicrosoftAPIClient):
                raw_result_list = await client.list_outlook_messages()
                if raw_result_list and 'value' in raw_result_list:
                    for item in raw_result_list.get("value", []):
                        normalized = normalize_microsoft_email(item, account_email=user_id, account_name=None)
                        if normalized:
                            all_messages.append(normalized)
        except Exception as e:
            logger.error(f"Error processing emails for provider {provider_enum.value} for user {user_id}: {e}", exc_info=True)
        finally:
            if client: await client.close()

    if all_messages:
        await set_to_cache(cache_key, [msg.model_dump() for msg in all_messages])
    return ApiResponse[List[EmailMessage]](data=all_messages, success=True)


@router.get("/messages/{message_id}", response_model=ApiResponse[EmailMessage])
async def get_email_message_detail(
    user_id: str,
    message_id: str,
    api_client_factory: APIClientFactory = Depends(get_api_client_factory)
):
    cache_key = generate_cache_key(user_id=user_id, endpoint="email_message_detail", params={"message_id": message_id})
    cached_response = await get_from_cache(cache_key)
    if cached_response:
        try:
            return ApiResponse[EmailMessage](data=EmailMessage(**cached_response), cache_hit=True, success=True)
        except Exception as e:
            logger.warning(f"Cache data for {cache_key} (detail) is stale or invalid: {e}")

    provider_str, actual_id = "", ""
    provider_enum: Optional[Provider] = None
    if message_id.startswith("google_"):
        provider_str = "google"; provider_enum = Provider.GOOGLE
        actual_id = message_id.split("google_", 1)[1]
    elif message_id.startswith("microsoft_"):
        provider_str = "microsoft"; provider_enum = Provider.MICROSOFT
        actual_id = message_id.split("microsoft_", 1)[1]
    else:
        return ApiResponse[EmailMessage](success=False, error={"type": "validation_error", "message": "Invalid message_id format. Must start with 'google_' or 'microsoft_'."}, data=None)

    if not provider_enum: # Should not happen if logic above is correct
        return ApiResponse[EmailMessage](success=False, error={"type": "internal_error", "message": "Provider could not be determined from message_id."}, data=None)

    client = await api_client_factory.get_client(user_id, provider_enum)
    if not client:
        return ApiResponse[EmailMessage](success=False, error={"type": "service_unavailable", "message": f"Could not get client for provider {provider_str}"}, data=None)

    raw_message_data: Optional[dict] = None
    normalized_message: Optional[EmailMessage] = None

    try:
        if isinstance(client, GoogleAPIClient):
            raw_message_data = await client.get_gmail_message(actual_id)
            if raw_message_data:
                normalized_message = normalize_google_email(raw_message_data, account_email=user_id)
        elif isinstance(client, MicrosoftAPIClient):
            raw_message_data = await client.get_outlook_message(actual_id)
            if raw_message_data:
                normalized_message = normalize_microsoft_email(raw_message_data, account_email=user_id)
    except Exception as e:
        logger.error(f"Failed to get message {message_id} for user {user_id}: {e}", exc_info=True)
        return ApiResponse[EmailMessage](success=False, error={"type": "internal_error", "message": "Failed to retrieve message details"}, data=None)
    finally:
        if client: await client.close()

    if not normalized_message:
        return ApiResponse[EmailMessage](success=False, error={"type": "not_found", "message": "Message not found or failed to normalize"}, data=None)

    await set_to_cache(cache_key, normalized_message.model_dump())
    return ApiResponse[EmailMessage](data=normalized_message, success=True)
