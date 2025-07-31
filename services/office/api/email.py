"""
Unified email endpoints for the Office Service.

All user-facing endpoints extract user from the X-User-Id header (set by the gateway).
No user_id is accepted in the path or query for user-facing endpoints.
Internal/service endpoints, if any, should be under /internal and require API key auth.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, Path, Query, Request

from services.common.http_errors import NotFoundError, ServiceError, ValidationError
from services.common.logging_config import get_logger, request_id_var
from services.office.core.api_client_factory import APIClientFactory
from services.office.core.auth import service_permission_required
from services.office.core.cache_manager import (
    cache_manager,
    generate_cache_key,
    generate_message_thread_cache_key,
    generate_thread_cache_key,
    generate_threads_list_cache_key,
)
from services.office.core.clients.google import GoogleAPIClient
from services.office.core.clients.microsoft import MicrosoftAPIClient
from services.office.core.normalizer import (
    normalize_google_email,
    normalize_google_thread,
    normalize_microsoft_conversation,
    normalize_microsoft_email,
)
from services.office.models import Provider
from services.office.schemas import (
    EmailFolder,
    EmailFolderList,
    EmailMessage,
    EmailMessageList,
    EmailThread,
    EmailThreadList,
    SendEmailRequest,
    SendEmailResponse,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/email", tags=["email"])

# Lazy-initialized API client factory instance
_api_client_factory = None
_api_client_factory_lock = asyncio.Lock()


async def get_api_client_factory() -> APIClientFactory:
    """Get or create the shared API client factory instance."""
    global _api_client_factory

    if _api_client_factory is None:
        async with _api_client_factory_lock:
            if _api_client_factory is None:
                _api_client_factory = APIClientFactory()
                logger.info(
                    "Created lazy-initialized APIClientFactory instance with shared TokenManager"
                )

    return _api_client_factory


async def get_user_id_from_gateway(request: Request) -> str:
    """
    Extract user ID from gateway headers.

    The office service only supports requests through the gateway,
    which forwards user identity via X-User-Id header.
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise ValidationError(message="X-User-Id header is required", field="X-User-Id")
    return user_id


def get_request_id() -> str:
    """
    Get the current request ID from context or generate a fallback.
    """
    request_id = request_id_var.get()
    if not request_id or request_id == "uninitialized":
        # Fallback for cases where middleware hasn't set the context
        return "no-request-id"
    return request_id


@router.get("/messages", response_model=EmailMessageList)
async def get_email_messages(
    request: Request,
    service_name: str = Depends(service_permission_required(["read_emails"])),
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
    folder_id: Optional[str] = Query(
        None, description="Folder ID to fetch messages from (provider-specific)"
    ),
    q: Optional[str] = Query(None, description="Search query to filter messages"),
    page_token: Optional[str] = Query(
        None, description="Pagination token for next page"
    ),
    no_cache: bool = Query(
        False, description="Bypass cache and fetch fresh data from providers"
    ),
) -> EmailMessageList:
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
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"Email messages request: user_id={user_id}, providers={providers}, limit={limit}"
    )

    try:
        # Query all available providers for the user
        # This should check the user's integrations and only query active providers
        # For now, we'll use the provided providers or default to all

        # Default to all providers if not specified
        if not providers:
            providers = ["google", "microsoft"]

        # Validate providers
        valid_providers = []
        for provider_name in providers:
            if provider_name.lower() in ["google", "microsoft"]:
                valid_providers.append(provider_name.lower())
            else:
                logger.warning(f"Invalid provider: {provider_name}")

        if not valid_providers:
            raise ValidationError(message="No valid providers specified")

        # Build cache key
        cache_params = {
            "providers": valid_providers,
            "limit": limit,
            "include_body": include_body,
            "labels": labels or [],
            "folder_id": folder_id or "",
            "q": q or "",
            "page_token": page_token or "",
            "no_cache": no_cache,
        }
        cache_key = generate_cache_key(user_id, "unified", "messages", cache_params)

        # Check cache first
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result and not no_cache:
            logger.info("Cache hit for email messages")
            return EmailMessageList(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch from providers in parallel
        tasks = []
        for provider_name in valid_providers:
            logger.info(f"[{request_id}] Creating task for provider: {provider_name}")
            task = fetch_provider_emails(
                request_id,
                user_id,
                provider_name,
                limit,
                include_body,
                labels,
                folder_id,
                q,
                page_token,
            )
            tasks.append(task)

        logger.info(
            f"[{request_id}] Created {len(tasks)} tasks, executing with asyncio.gather"
        )

        # Execute parallel requests
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        aggregated_messages: List[EmailMessage] = []
        provider_errors = {}
        providers_used = []

        for i, result in enumerate(provider_results):
            provider_name = valid_providers[i]

            if isinstance(result, Exception):
                logger.error(f"Provider {provider_name} failed: {result}")
                provider_errors[provider_name] = str(result)
            elif result is not None and not isinstance(result, BaseException):
                try:
                    # Type narrowing: result should be tuple[List[EmailMessage], str]
                    messages, provider_name = result
                    aggregated_messages.extend(messages)
                    providers_used.append(provider_name)
                    logger.info(
                        f"Provider {provider_name} returned {len(messages)} messages"
                    )
                except (TypeError, ValueError) as e:
                    logger.error(f"Invalid result format from {provider_name}: {e}")
                    provider_errors[provider_name] = f"Invalid result format: {e}"

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

        # Only cache if we have successful results from at least one provider
        if providers_used:  # Only cache if at least one provider succeeded
            # Cache the result for 15 minutes
            await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=900)
        else:
            logger.info(
                "Not caching response due to no successful providers",
                extra={
                    "providers_used": providers_used,
                    "provider_errors": provider_errors,
                },
            )

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(f"Email messages request completed in {response_time_ms}ms")

        return EmailMessageList(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=(
                Provider(providers_used[0]) if len(providers_used) == 1 else None
            ),
            request_id=request_id,
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Email messages request failed: {e}")
        raise ServiceError(message=f"Failed to fetch email messages: {str(e)}")


@router.get("/folders", response_model=EmailFolderList)
async def get_email_folders(
    request: Request,
    service_name: str = Depends(service_permission_required(["read_emails"])),
    providers: Optional[List[str]] = Query(
        None,
        description="Providers to fetch from (google, microsoft). If not specified, fetches from all available providers",
    ),
    no_cache: bool = Query(
        False, description="Bypass cache and fetch fresh data from providers"
    ),
) -> EmailFolderList:
    """
    Get unified email folders/labels from multiple providers.

    Fetches email folders from Microsoft Outlook and labels from Google Gmail APIs,
    normalizes them to a unified format, and returns aggregated results.
    Responses are cached for improved performance.

    Args:
        user_id: ID of the user to fetch folders for
        providers: List of providers to query (defaults to all available)
        no_cache: Bypass cache and fetch fresh data

    Returns:
        EmailFolderList with aggregated email folders
    """
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(f"Email folders request: user_id={user_id}, providers={providers}")

    try:
        # Default to all providers if not specified
        if not providers:
            providers = ["google", "microsoft"]

        # Validate providers
        valid_providers = []
        for provider_name in providers:
            if provider_name.lower() in ["google", "microsoft"]:
                valid_providers.append(provider_name.lower())
            else:
                logger.warning(f"Invalid provider: {provider_name}")

        if not valid_providers:
            raise ValidationError(message="No valid providers specified")

        # Build cache key
        cache_params = {
            "providers": valid_providers,
            "no_cache": no_cache,
        }
        cache_key = generate_cache_key(user_id, "unified", "folders", cache_params)

        # Check cache first
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result and not no_cache:
            logger.info("Cache hit for email folders")
            # Convert cached dictionary data back to proper format for response
            # The cached data contains folder dictionaries, but we need to return the original format
            response_data = {
                "folders": [
                    EmailFolder(**folder_data)
                    for folder_data in cached_result.get("folders", [])
                ],
                "providers_used": cached_result.get("providers_used", []),
                "provider_errors": cached_result.get("provider_errors", {}),
            }
            return EmailFolderList(
                success=True, data=response_data, cache_hit=True, request_id=request_id
            )

        # Fetch from providers in parallel
        tasks = []
        for provider_name in valid_providers:
            task = fetch_provider_folders(
                request_id,
                user_id,
                provider_name,
            )
            tasks.append(task)

        # Execute parallel requests
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        aggregated_folders: List[EmailFolder] = []
        provider_errors = {}
        providers_used = []

        for i, result in enumerate(provider_results):
            provider_name = valid_providers[i]

            if isinstance(result, Exception):
                logger.error(f"Provider {provider_name} failed: {result}")
                provider_errors[provider_name] = str(result)
            elif result is not None and not isinstance(result, BaseException):
                try:
                    # Type narrowing: result should be tuple[List[EmailFolder], str]
                    folders, provider_name = result
                    aggregated_folders.extend(folders)
                    providers_used.append(provider_name)
                    logger.info(
                        f"Provider {provider_name} returned {len(folders)} folders"
                    )
                except (TypeError, ValueError) as e:
                    logger.error(f"Invalid result format from {provider_name}: {e}")
                    provider_errors[provider_name] = f"Invalid result format: {e}"

        # Remove duplicates based on label
        seen_labels = set()
        unique_folders = []
        for folder in aggregated_folders:
            if folder.label not in seen_labels:
                seen_labels.add(folder.label)
                unique_folders.append(folder)

        # Sort folders by name
        unique_folders.sort(key=lambda folder: folder.name.lower())

        # Build response
        response_data = {
            "folders": unique_folders,
            "providers_used": providers_used,
            "provider_errors": provider_errors,
        }

        # Convert Pydantic models to dictionaries for caching
        cache_data = {
            "folders": [folder.model_dump() for folder in unique_folders],
            "providers_used": providers_used,
            "provider_errors": provider_errors,
        }

        # Cache the result
        await cache_manager.set_to_cache(
            cache_key, cache_data, ttl_seconds=3600
        )  # 1 hour

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        logger.info(
            f"Email folders request completed in {duration:.2f}s: "
            f"{len(unique_folders)} folders from {len(providers_used)} providers"
        )

        return EmailFolderList(
            success=True, data=response_data, cache_hit=False, request_id=request_id
        )

    except Exception as e:
        logger.error(f"Error fetching email folders: {e}")
        raise ServiceError(
            message="Failed to fetch email folders",
            details={"error": str(e)},
        )


@router.get("/messages/{message_id}", response_model=EmailMessageList)
async def get_email_message(
    request: Request,
    service_name: str = Depends(service_permission_required(["read_emails"])),
    message_id: str = Path(..., description="Message ID (format: provider_originalId)"),
    include_body: bool = Query(
        True, description="Whether to include message body content"
    ),
) -> EmailMessageList:
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
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"Email message detail request: message_id={message_id}, user_id={user_id}"
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
            logger.info("Cache hit for message detail")
            return EmailMessageList(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch from the specific provider
        message = await fetch_single_message(
            request_id, user_id, provider, original_message_id, include_body
        )

        if not message:
            raise NotFoundError("Message", message_id)

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

        logger.info(f"Message detail request completed in {response_time_ms}ms")

        return EmailMessageList(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=Provider(provider),
            request_id=request_id,
        )

    except NotFoundError:
        raise
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Message detail request failed: {e}")
        raise ServiceError(message=f"Failed to fetch message: {str(e)}")


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    request: Request,
    email_data: SendEmailRequest,
    service_name: str = Depends(service_permission_required(["send_emails"])),
) -> SendEmailResponse:
    """
    Send an email message.

    This endpoint supports sending emails through Gmail and Outlook.
    The provider can be specified in the request, otherwise it uses the user's default preference.
    """
    request_id = get_request_id()
    user_id = await get_user_id_from_gateway(request)

    logger.info(f"Send email request {request_id} for user {user_id}")

    try:
        # Determine provider to use
        provider = email_data.provider
        if not provider:
            # Use the first available provider as default
            provider = "google"  # Default to Gmail for now

        # Get API client for provider
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise ValidationError(
                message=f"Failed to create API client for provider {provider}"
            )

        # Use client as async context manager
        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                result = await send_gmail_message(request_id, google_client, email_data)
            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                result = await send_outlook_message(
                    request_id, microsoft_client, email_data
                )
            else:
                raise ValidationError(message=f"Unsupported provider: {provider}")

        return SendEmailResponse(
            success=True,
            data=result,
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to send email for user {user_id}: {e}")
        return SendEmailResponse(
            success=False,
            error={"message": str(e)},
            request_id=request_id,
        )


@router.get("/threads", response_model=EmailThreadList)
async def get_email_threads(
    request: Request,
    service_name: str = Depends(service_permission_required(["read_emails"])),
    providers: Optional[List[str]] = Query(
        None,
        description="Providers to fetch from (google, microsoft). If not specified, fetches from all available providers",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of threads to return per provider",
    ),
    include_body: bool = Query(
        False, description="Whether to include message body content"
    ),
    labels: Optional[List[str]] = Query(
        None, description="Filter by labels (inbox, sent, etc.)"
    ),
    folder_id: Optional[str] = Query(
        None, description="Folder ID to fetch threads from (provider-specific)"
    ),
    q: Optional[str] = Query(None, description="Search query to filter threads"),
    page_token: Optional[str] = Query(
        None, description="Pagination token for next page"
    ),
    no_cache: bool = Query(
        False, description="Bypass cache and fetch fresh data from providers"
    ),
) -> EmailThreadList:
    """
    Get email threads from multiple providers.

    This endpoint fetches email threads from Gmail and/or Outlook,
    normalizes them to a unified format, and returns them grouped by thread.
    """
    request_id = get_request_id()
    user_id = await get_user_id_from_gateway(request)

    logger.info(f"Get email threads request {request_id} for user {user_id}")

    try:
        # Determine providers to fetch from
        if not providers:
            providers = ["google", "microsoft"]  # Default to all providers

        # Validate providers
        valid_providers = {"google", "microsoft"}
        invalid_providers = set(providers) - valid_providers
        if invalid_providers:
            raise ValidationError(
                message=f"Invalid providers: {invalid_providers}. Valid providers: {valid_providers}"
            )

        # Check cache first
        cache_key = generate_threads_list_cache_key(
            user_id=user_id,
            providers=providers,
            limit=limit,
            include_body=include_body,
            labels=labels,
            folder_id=folder_id,
            q=q,
            page_token=page_token,
        )

        if not no_cache:
            cached_result = await cache_manager.get_from_cache(cache_key)
            if cached_result:
                logger.info(f"Cache hit for email threads request {request_id}")
                return EmailThreadList(
                    success=True,
                    data=cached_result,
                    cache_hit=True,
                    request_id=request_id,
                )

        # Fetch threads from each provider
        all_threads = []
        provider_errors = {}
        primary_provider = None

        for provider in providers:
            try:
                threads, provider_used = await fetch_provider_threads(
                    request_id,
                    user_id,
                    provider,
                    limit,
                    include_body,
                    labels,
                    folder_id,
                    q,
                    page_token,
                )
                all_threads.extend(threads)
                if not primary_provider:
                    primary_provider = provider_used

            except Exception as e:
                logger.error(f"Failed to fetch threads from {provider}: {e}")
                provider_errors[provider] = str(e)

        # Sort threads by last message date
        all_threads.sort(key=lambda t: t.last_message_date, reverse=True)

        # Prepare response data
        response_data = {
            "threads": all_threads,
            "total_count": len(all_threads),
            "providers_used": providers,
            "provider_errors": provider_errors if provider_errors else None,
        }

        # Cache the result
        if not no_cache:
            await cache_manager.set_to_cache(
                cache_key, response_data, ttl_seconds=300
            )  # 5 minutes

        return EmailThreadList(
            success=True,
            data=response_data,
            provider_used=get_provider_enum(primary_provider) if primary_provider else None,
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to get email threads for user {user_id}: {e}")
        return EmailThreadList(
            success=False,
            error={"message": str(e)},
            request_id=request_id,
        )


@router.get("/threads/{thread_id}", response_model=EmailThreadList)
async def get_email_thread(
    request: Request,
    thread_id: str = Path(..., description="Thread ID (format: provider_originalId)"),
    include_body: bool = Query(
        True, description="Whether to include message body content"
    ),
    no_cache: bool = Query(
        False, description="Bypass cache and fetch fresh data from providers"
    ),
    service_name: str = Depends(service_permission_required(["read_emails"])),
) -> EmailThreadList:
    """
    Get a specific email thread with all its messages.

    This endpoint fetches a specific thread and all its messages from the provider.
    """
    request_id = get_request_id()
    user_id = await get_user_id_from_gateway(request)

    logger.info(
        f"Get email thread request {request_id} for user {user_id}, thread {thread_id}"
    )

    try:
        # Parse thread ID to get provider and original ID
        provider, original_thread_id = parse_thread_id(thread_id)

        # Check cache first
        cache_key = generate_thread_cache_key(
            user_id=user_id,
            thread_id=thread_id,
            include_body=include_body,
        )

        if not no_cache:
            cached_result = await cache_manager.get_from_cache(cache_key)
            if cached_result:
                logger.info(f"Cache hit for email thread request {request_id}")
                return EmailThreadList(
                    success=True,
                    data=cached_result,
                    cache_hit=True,
                    request_id=request_id,
                )

        # Fetch thread from provider
        thread = await fetch_single_thread(
            request_id,
            user_id,
            provider,
            original_thread_id,
            include_body,
        )

        if not thread:
            raise NotFoundError("Thread", thread_id)

        # Prepare response data
        response_data = {
            "thread": thread,
            "provider_used": provider,
        }

        # Cache the result
        if not no_cache:
            await cache_manager.set_to_cache(
                cache_key, response_data, ttl_seconds=600
            )  # 10 minutes

        return EmailThreadList(
            success=True,
            data=response_data,
            provider_used=get_provider_enum(provider),
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to get email thread {thread_id} for user {user_id}: {e}")
        return EmailThreadList(
            success=False,
            error={"message": str(e)},
            request_id=request_id,
        )


@router.get("/messages/{message_id}/thread", response_model=EmailThreadList)
async def get_message_thread(
    request: Request,
    message_id: str = Path(..., description="Message ID (format: provider_originalId)"),
    include_body: bool = Query(
        True, description="Whether to include message body content"
    ),
    no_cache: bool = Query(
        False, description="Bypass cache and fetch fresh data from providers"
    ),
    service_name: str = Depends(service_permission_required(["read_emails"])),
) -> EmailThreadList:
    """
    Get the thread containing a specific message.

    This endpoint finds the thread that contains the specified message and returns all messages in that thread.
    """
    request_id = get_request_id()
    user_id = await get_user_id_from_gateway(request)

    logger.info(
        f"Get message thread request {request_id} for user {user_id}, message {message_id}"
    )

    try:
        # Parse message ID to get provider and original ID
        provider, original_message_id = parse_message_id(message_id)

        # Check cache first
        cache_key = generate_message_thread_cache_key(
            user_id=user_id,
            message_id=message_id,
            include_body=include_body,
        )

        if not no_cache:
            cached_result = await cache_manager.get_from_cache(cache_key)
            if cached_result:
                logger.info(f"Cache hit for message thread request {request_id}")
                return EmailThreadList(
                    success=True,
                    data=cached_result,
                    cache_hit=True,
                    request_id=request_id,
                )

        # Fetch thread for the message
        thread = await fetch_message_thread(
            request_id,
            user_id,
            provider,
            original_message_id,
            include_body,
        )

        if not thread:
            raise NotFoundError("Thread", f"for message {message_id}")

        # Prepare response data
        response_data = {
            "thread": thread,
            "provider_used": provider,
        }

        # Cache the result
        if not no_cache:
            await cache_manager.set_to_cache(
                cache_key, response_data, ttl_seconds=600
            )  # 10 minutes

        return EmailThreadList(
            success=True,
            data=response_data,
            provider_used=get_provider_enum(provider),
            request_id=request_id,
        )

    except Exception as e:
        logger.error(
            f"Failed to get message thread for {message_id} and user {user_id}: {e}"
        )
        return EmailThreadList(
            success=False,
            error={"message": str(e)},
            request_id=request_id,
        )


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

        logger.info(f"Gmail message sent successfully: {result.get('id')}")
        return result

    except Exception as e:
        logger.error(f"Failed to send Gmail message: {e}")
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

        logger.info("Outlook message sent successfully")
        return result

    except Exception as e:
        logger.error(f"Failed to send Outlook message: {e}")
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
    folder_id: Optional[str],
    q: Optional[str],
    page_token: Optional[str],
) -> tuple[List[EmailMessage], str]:
    """
    Fetch emails from a specific provider.

    Args:
        request_id: Request tracking ID
        user_id: User ID
        provider: Provider name (google, microsoft)
        limit: Maximum messages to return
        include_body: Whether to include message body content
        labels: Filter by labels (inbox, sent, etc.)
        folder_id: Folder ID to fetch from
        q: Search query
        page_token: Pagination token

    Returns:
        Tuple of (messages list, provider name)
    """
    try:
        logger.info(
            f"[{request_id}] fetch_provider_emails called for user {user_id}, provider {provider}"
        )

        # Get API client for provider
        logger.info(
            f"[{request_id}] Calling api_client_factory.create_client for user {user_id}, provider {provider}"
        )
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise ValidationError(
                message=f"Failed to create API client for provider {provider}"
            )

        logger.info(
            f"[{request_id}] Successfully created {provider} client for user {user_id}"
        )

        # Use client as async context manager
        async with client:
            # Build provider-specific parameters
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)

                # Fetch messages from Gmail - use label-specific endpoint if folder_id is provided
                if folder_id:
                    messages_response = await google_client.get_messages_from_label(
                        label_id=folder_id,
                        max_results=limit,
                        page_token=page_token,
                    )
                else:
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

                # Fetch messages from Outlook - use folder-specific endpoint if folder_id is provided
                if folder_id:
                    messages_response = await microsoft_client.get_messages_from_folder(
                        folder_id=folder_id,
                        top=limit,
                        skip=skip_value,
                        filter=filter_expr,
                        search=q,
                        order_by="receivedDateTime desc",
                    )
                else:
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
                raise ValidationError(message=f"Unsupported provider: {provider}")

            logger.info(
                f"Successfully fetched {len(normalized_messages)} messages from {provider}"
            )
            return normalized_messages, provider

    except Exception as e:
        logger.error(f"Error fetching emails from {provider}: {e}")
        raise


async def fetch_provider_folders(
    request_id: str,
    user_id: str,
    provider: str,
) -> tuple[List[EmailFolder], str]:
    """
    Fetch folders/labels from a specific provider.

    Args:
        request_id: Request tracking ID
        user_id: User ID
        provider: Provider name (google, microsoft)

    Returns:
        Tuple of (folders list, provider name)
    """
    try:
        # Get API client for provider
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise ValidationError(
                message=f"Failed to create API client for provider {provider}"
            )

        # Use client as async context manager
        async with client:
            # Build provider-specific parameters
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)

                # Fetch labels from Gmail
                labels_response = await google_client.get_labels()
                labels = labels_response.get("labels", [])

                # Get user account info
                if "@" in user_id:
                    account_email = user_id
                    account_name = f"Gmail Account ({user_id.split('@')[0]})"
                else:
                    account_email = f"{user_id}@gmail.com"  # Placeholder
                    account_name = f"Gmail Account ({user_id})"  # Placeholder

                # Normalize Gmail labels to EmailFolder objects
                normalized_folders = []
                for label in labels:
                    label_id = label.get("id")
                    label_name = label.get("name", "")
                    message_count = label.get("messagesTotal", 0)

                    # Skip system labels that we don't want to show
                    system_labels_to_skip = {
                        "UNREAD",
                        "STARRED",
                        "IMPORTANT",
                        "CATEGORY_PERSONAL",
                        "CATEGORY_SOCIAL",
                        "CATEGORY_PROMOTIONS",
                        "CATEGORY_UPDATES",
                        "CATEGORY_FORUMS",
                        "CHAT",
                    }

                    if label_id in system_labels_to_skip:
                        continue

                    # Determine if this is a system folder
                    system_labels = {
                        "INBOX",
                        "SENT",
                        "DRAFT",
                        "SPAM",
                        "TRASH",
                        "ARCHIVE",
                    }
                    is_system = label_id in system_labels

                    # Map Gmail label IDs to our standardized labels
                    label_map = {
                        "INBOX": "inbox",
                        "SENT": "sent",
                        "DRAFT": "draft",
                        "SPAM": "spam",
                        "TRASH": "trash",
                        "ARCHIVE": "archive",
                    }

                    normalized_label = label_map.get(label_id, label_id.lower())

                    folder = EmailFolder(
                        label=normalized_label,
                        name=label_name,
                        provider=Provider.GOOGLE,
                        provider_folder_id=label_id,
                        account_email=account_email,
                        account_name=account_name,
                        is_system=is_system,
                        message_count=message_count,
                    )
                    normalized_folders.append(folder)

            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)

                # Fetch mailboxes from Outlook
                mailboxes_response = await microsoft_client.get_mailboxes()
                mailboxes = mailboxes_response.get("value", [])

                # Get user account info
                if "@" in user_id:
                    account_email = user_id
                    account_name = f"Outlook Account ({user_id.split('@')[0]})"
                else:
                    account_email = f"{user_id}@outlook.com"  # Placeholder
                    account_name = f"Outlook Account ({user_id})"  # Placeholder

                # Normalize Microsoft mailboxes to EmailFolder objects
                normalized_folders = []
                for mailbox in mailboxes:
                    folder_id = mailbox.get("id")
                    folder_name = mailbox.get("displayName", "")
                    message_count = mailbox.get("totalItemCount", 0)

                    # Skip system folders we don't want to show
                    system_folders_to_skip = {
                        "Conversation History",
                        "Notes",
                        "Outbox",
                        "RSS Feeds",
                        "Search Folders",
                        "Sync Issues",
                    }

                    if folder_name in system_folders_to_skip:
                        continue

                    # Determine if this is a system folder
                    system_folders = {
                        "Inbox",
                        "Sent Items",
                        "Drafts",
                        "Junk Email",
                        "Deleted Items",
                        "Archive",
                    }
                    is_system = folder_name in system_folders

                    # Map Microsoft folder names to our standardized labels
                    folder_map = {
                        "Inbox": "inbox",
                        "Sent Items": "sent",
                        "Drafts": "draft",
                        "Junk Email": "spam",
                        "Deleted Items": "trash",
                        "Archive": "archive",
                    }

                    normalized_label = folder_map.get(
                        folder_name, folder_name.lower().replace(" ", "_")
                    )

                    folder = EmailFolder(
                        label=normalized_label,
                        name=folder_name,
                        provider=Provider.MICROSOFT,
                        provider_folder_id=folder_id,
                        account_email=account_email,
                        account_name=account_name,
                        is_system=is_system,
                        message_count=message_count,
                    )
                    normalized_folders.append(folder)

            else:
                raise ValidationError(message=f"Unsupported provider: {provider}")

        return normalized_folders, provider

    except Exception as e:
        logger.error(f"Error fetching folders from {provider}: {e}")
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
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise ValidationError(
                message=f"Failed to create API client for provider {provider}"
            )

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
                raise ValidationError(message=f"Unsupported provider: {provider}")

    except Exception as e:
        logger.error(
            f"Failed to fetch message {original_message_id} from {provider}: {e}"
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
            raise ValidationError(message="Invalid message ID format")

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
            raise ValidationError(message=f"Unknown provider prefix: {provider_prefix}")

        return provider, original_id

    except Exception:
        raise ValidationError(
            message=f"Invalid message ID format: {message_id}. Expected format: 'provider_originalId'"
        )


def get_user_account_info(user_id: str, provider: str) -> tuple[str, str]:
    """
    Get standardized user account info for a provider.
 
    Args:
        user_id: User ID
        provider: Provider name (google, microsoft)
 
    Returns:
        Tuple of (account_email, account_name)
    """
    if "@" in user_id:
        account_email = user_id
        account_name = f"{provider.title()} Account ({user_id.split('@')[0]})"
    else:
        if provider == "google":
            account_email = f"{user_id}@gmail.com"
        else:  # microsoft
            account_email = f"{user_id}@outlook.com"
        account_name = f"{provider.title()} Account ({user_id})"
 
    return account_email, account_name


def get_provider_enum(provider: str) -> Optional[Provider]:
    """
    Convert string provider to Provider enum.
    
    Args:
        provider: Provider string (google, microsoft)
        
    Returns:
        Provider enum value or None if invalid
    """
    try:
        return Provider(provider.lower())
    except ValueError:
        return None


def parse_thread_id(thread_id: str) -> tuple[str, str]:
    """
    Parse a unified thread ID to extract provider and original ID.

    Args:
        thread_id: Unified thread ID (format: "provider_originalId")

    Returns:
        Tuple of (provider, original_thread_id)

    Raises:
        HTTPException: If thread ID format is invalid
    """
    try:
        if "_" not in thread_id:
            raise ValidationError(message="Invalid thread ID format")

        parts = thread_id.split("_", 1)
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
            raise ValidationError(message=f"Unknown provider prefix: {provider_prefix}")

        return provider, original_id

    except ValidationError:
        # Re-raise ValidationError as-is
        raise
    except Exception:
        raise ValidationError(
            message=f"Invalid thread ID format: {thread_id}. Expected format: 'provider_originalId'"
        )


async def fetch_provider_threads(
    request_id: str,
    user_id: str,
    provider: str,
    limit: int,
    include_body: bool,
    labels: Optional[List[str]],
    folder_id: Optional[str],
    q: Optional[str],
    page_token: Optional[str],
) -> tuple[List[EmailThread], str]:
    """
    Fetch email threads from a specific provider.

    Args:
        request_id: Request ID for logging
        user_id: User ID
        provider: Provider name (google, microsoft)
        limit: Maximum number of threads to return
        include_body: Whether to include message body content
        labels: Filter by labels
        folder_id: Folder ID to fetch from
        q: Search query
        page_token: Pagination token

    Returns:
        Tuple of (list of EmailThread objects, provider used)
    """
    try:
        # Get API client for provider
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise ValidationError(
                message=f"Failed to create API client for provider {provider}"
            )

        # Use client as async context manager
        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                # For Gmail, we need to fetch threads and then get messages for each thread
                threads_data = await google_client.get_threads(
                    max_results=limit,
                    q=q,
                    label_ids=labels,
                )

                # Get user account info
                account_email, account_name = get_user_account_info(user_id, provider)

                # Convert Gmail threads to unified format
                threads = []
                for thread_data in threads_data.get("threads", []):
                    thread_id = thread_data.get("id")
                    if thread_id:
                        # Get messages for this thread
                        thread_messages = await google_client.get_thread(thread_id)

                        # Use the normalization function
                        try:
                            normalized_thread = normalize_google_thread(
                                thread_messages, account_email, account_name
                            )
                            threads.append(normalized_thread)
                        except Exception as e:
                            logger.warning(
                                f"Failed to normalize Gmail thread {thread_id}: {e}"
                            )
                            continue

                return threads, provider

            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                # For Microsoft, get messages and group by conversationId to create threads
                messages_response = await microsoft_client.get_messages(
                    top=limit
                    * 10,  # Get more messages to ensure we have enough threads
                )
                messages = messages_response.get("value", [])

                # Get user account info
                account_email, account_name = get_user_account_info(user_id, provider)

                # Group messages by conversationId to create threads
                conversation_groups: Dict[str, List[Dict[str, Any]]] = {}
                for message in messages:
                    conv_id = message.get("conversationId")
                    if conv_id:
                        if conv_id not in conversation_groups:
                            conversation_groups[conv_id] = []
                        conversation_groups[conv_id].append(message)

                # Convert grouped messages to unified thread format
                threads = []
                for conv_id, conv_messages in list(conversation_groups.items())[:limit]:
                    try:
                        # Create minimal conversation data
                        conv_data = {"id": conv_id}

                        normalized_thread = normalize_microsoft_conversation(
                            conv_data, conv_messages, account_email, account_name
                        )
                        threads.append(normalized_thread)
                    except Exception as e:
                        logger.warning(
                            f"Failed to normalize Microsoft thread {conv_id}: {e}"
                        )
                        continue

                return threads, provider

            else:
                raise ValidationError(message=f"Unsupported provider: {provider}")

    except Exception as e:
        logger.error(f"Failed to fetch threads from {provider}: {e}")
        raise


async def fetch_single_thread(
    request_id: str,
    user_id: str,
    provider: str,
    original_thread_id: str,
    include_body: bool,
) -> Optional[EmailThread]:
    """
    Fetch a single thread from a specific provider.

    Args:
        request_id: Request ID for logging
        user_id: User ID
        provider: Provider name (google, microsoft)
        original_thread_id: Original thread ID from the provider
        include_body: Whether to include message body content

    Returns:
        EmailThread or None if not found
    """
    try:
        # Get API client for provider
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise ValidationError(
                message=f"Failed to create API client for provider {provider}"
            )

        # Use client as async context manager
        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                # Get thread from Gmail
                thread_data = await google_client.get_thread(original_thread_id)

                # Get user account info
                account_email, account_name = get_user_account_info(user_id, provider)

                # Use the normalization function
                try:
                    return normalize_google_thread(
                        thread_data, account_email, account_name
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to normalize Gmail thread {original_thread_id}: {e}"
                    )
                    return None

            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                # Get messages and filter by conversation ID for Microsoft
                logger.info(
                    f"Fetching Microsoft thread {original_thread_id} for user {user_id}"
                )
                try:
                    # Get recent messages and filter client-side by conversationId
                    messages_response = await microsoft_client.get_messages(
                        top=200,  # Get more messages to increase chances of finding the thread
                    )
                    messages = messages_response.get("value", [])

                    # Filter messages that belong to this thread
                    thread_messages = [
                        msg
                        for msg in messages
                        if msg.get("conversationId") == original_thread_id
                    ]

                    if thread_messages:
                        logger.info(
                            f"Found {len(thread_messages)} messages for thread {original_thread_id}"
                        )

                        # Get user account info
                        account_email, account_name = get_user_account_info(
                            user_id, provider
                        )

                        return normalize_microsoft_conversation(
                            {"id": original_thread_id},
                            thread_messages,
                            account_email,
                            account_name,
                        )
                    else:
                        logger.warning(
                            f"No messages found for thread {original_thread_id}"
                        )
                        return None
                except Exception as e:
                    logger.error(
                        f"Failed to fetch Microsoft thread {original_thread_id}: {e}"
                    )
                    return None

            else:
                raise ValidationError(message=f"Unsupported provider: {provider}")

        return None

    except Exception as e:
        logger.error(
            f"Failed to fetch thread {original_thread_id} from {provider}: {e}"
        )
        return None


async def fetch_message_thread(
    request_id: str,
    user_id: str,
    provider: str,
    original_message_id: str,
    include_body: bool,
) -> Optional[EmailThread]:
    """
    Fetch the thread containing a specific message.

    Args:
        request_id: Request ID for logging
        user_id: User ID
        provider: Provider name (google, microsoft)
        original_message_id: Original message ID from the provider
        include_body: Whether to include message body content

    Returns:
        EmailThread or None if not found
    """
    try:
        # Get API client for provider
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise ValidationError(
                message=f"Failed to create API client for provider {provider}"
            )

        # Use client as async context manager
        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                # Get message to find its thread ID
                message_data = await google_client.get_message(original_message_id)
                thread_id = message_data.get("threadId")

                if thread_id:
                    return await fetch_single_thread(
                        request_id, user_id, provider, thread_id, include_body
                    )

            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                # Get the message to find its conversation ID
                message_data = await microsoft_client.get_message(original_message_id)
                conversation_id = message_data.get("conversationId")

                if conversation_id:
                    return await fetch_single_thread(
                        request_id, user_id, provider, conversation_id, include_body
                    )
                else:
                    logger.warning(
                        f"Message {original_message_id} does not have a conversation ID"
                    )
                    return None

            else:
                raise ValidationError(message=f"Unsupported provider: {provider}")

        return None

    except Exception as e:
        logger.error(
            f"Failed to fetch message thread for {original_message_id} from {provider}: {e}"
        )
        return None
