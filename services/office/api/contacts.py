import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from pydantic import BaseModel

from services.common.http_errors import ServiceError, ValidationError
from services.common.logging_config import get_logger, request_id_var
from services.office.api.email import get_provider_enum, get_user_account_info
from services.office.core.api_client_factory import APIClientFactory
from services.office.core.auth import service_permission_required
from services.office.core.cache_manager import cache_manager, generate_cache_key
from services.office.core.clients.google import GoogleAPIClient
from services.office.core.clients.microsoft import MicrosoftAPIClient
from services.office.core.normalizer import (
    normalize_google_contact,
    normalize_microsoft_contact,
)
from services.office.models import Provider
from services.office.schemas import Contact, ContactList, ContactCreateResponse, ContactUpdateResponse, ContactDeleteResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/contacts", tags=["contacts"])

_api_client_factory: Optional[APIClientFactory] = None
_api_client_factory_lock = asyncio.Lock()


async def get_api_client_factory() -> APIClientFactory:
    global _api_client_factory
    if _api_client_factory is None:
        async with _api_client_factory_lock:
            if _api_client_factory is None:
                _api_client_factory = APIClientFactory()
                logger.info("Created APIClientFactory for contacts")
    return _api_client_factory


def get_request_id() -> str:
    request_id = request_id_var.get()
    if not request_id or request_id == "uninitialized":
        return "no-request-id"
    return request_id


async def _invalidate_contacts_cache(user_id: str) -> None:
    """Invalidate contacts cache for a user with backwards compatibility.

    Older tests/modules may patch `cache_manager.invalidate_user_cache`.
    Prefer that if present; otherwise fall back to `delete_pattern`.
    """
    # Back-compat: some tests patch this attribute as AsyncMock
    invalidate_attr = getattr(cache_manager, "invalidate_user_cache", None)
    if invalidate_attr is not None:
        try:
            await invalidate_attr(user_id)
            return
        except TypeError:
            # Fall back if the patched attribute isn't awaitable
            pass

    # Default: delete contacts keys for this user
    pattern = f"office:{user_id}:unified:contacts:*"
    await cache_manager.delete_pattern(pattern)


async def get_user_id_from_gateway(request: Request) -> str:
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise ValidationError(message="X-User-Id header is required", field="X-User-Id")
    return user_id


def _get_contact_scopes(provider: str, write: bool = False) -> List[str]:
    if provider == "google":
        return [
            (
                "https://www.googleapis.com/auth/contacts.readonly"
                if not write
                else "https://www.googleapis.com/auth/contacts"
            ),
        ]
    elif provider == "microsoft":
        return [
            (
                "https://graph.microsoft.com/Contacts.ReadWrite"
                if write
                else "https://graph.microsoft.com/Contacts.Read"
            ),
        ]
    return []


class _ContactCreatePayload(BaseModel):
    provider: Optional[str] = None
    full_name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    emails: Optional[List[Any]] = (
        None  # Accept strings or objects with email/address/value
    )
    company: Optional[str] = None
    job_title: Optional[str] = None
    phones: Optional[List[str]] = None


class _ContactUpdatePayload(BaseModel):
    provider: Optional[str] = None
    full_name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    emails: Optional[List[Any]] = (
        None  # Accept strings or objects with email/address/value
    )
    phones: Optional[List[str]] = None


def _extract_email_strings(raw_emails: Optional[List[Any]]) -> Optional[List[str]]:
    if not raw_emails:
        return None
    result: List[str] = []
    for item in raw_emails:
        if isinstance(item, str):
            result.append(item)
            continue
        if isinstance(item, dict):
            addr = item.get("email") or item.get("address") or item.get("value")
            if addr:
                result.append(addr)
            continue
        # Try attribute access (e.g., EmailAddress model)
        try:
            addr = getattr(item, "email", None)
            if addr:
                result.append(addr)
        except Exception:
            continue
    return result or None


@router.get("/", response_model=ContactList)
async def list_contacts(
    request: Request,
    service_name: str = Depends(service_permission_required(["read_contacts"])),
    providers: Optional[List[str]] = Query(
        None, description="Providers to fetch from (google, microsoft)."
    ),
    limit: int = Query(100, ge=1, le=500),
    q: Optional[str] = Query(None, description="Free-text search (name or email)"),
    company: Optional[str] = Query(
        None, description="Filter by company or email domain"
    ),
    no_cache: bool = Query(
        False, description="Bypass cache and fetch fresh data from providers"
    ),
) -> ContactList:
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()

    try:
        if not providers:
            providers = ["google", "microsoft"]
        valid_providers = [p for p in providers if p in ["google", "microsoft"]]
        if not valid_providers:
            raise ValidationError(
                message="No valid providers specified", field="providers"
            )

        cache_params = {
            "providers": valid_providers,
            "limit": limit,
            "q": q or "",
            "company": company or "",
        }
        cache_key = generate_cache_key(user_id, "unified", "contacts", cache_params)

        if not no_cache:
            cached = await cache_manager.get_from_cache(cache_key)
            if cached:
                return ContactList(
                    success=True, data=cached, cache_hit=True, request_id=request_id
                )

        factory = await get_api_client_factory()

        async def _fetch(provider: str) -> Tuple[List[Contact], str]:
            scopes = _get_contact_scopes(provider, write=False)

            client = await factory.create_client(user_id, provider, scopes=scopes)
            if client is None:
                logger.error(
                    f"Failed to create client for provider {provider} - client is None"
                )
                raise ServiceError(message=f"No client for provider {provider}")

            results: List[Contact] = []
            # Determine account context for this provider
            account_email, account_name = get_user_account_info(user_id, provider)

            if provider == "google":
                # Google client supports page_size
                g_client: GoogleAPIClient = client  # type: ignore[assignment]
                async with g_client:
                    data = await g_client.get_contacts(page_size=limit)
                    for c in data.get("connections", []) or []:
                        normalized = normalize_google_contact(
                            c, account_email=account_email, account_name=account_name
                        )
                        results.append(Contact(**normalized))
            elif provider == "microsoft":
                # Microsoft client supports top/select/order_by
                select = "id,displayName,givenName,surname,emailAddresses,companyName,jobTitle,businessPhones,mobilePhone,homePhones"
                # Type narrow for mypy
                ms_client: MicrosoftAPIClient = client  # type: ignore[assignment]
                async with ms_client:
                    data = await ms_client.get_contacts(
                        top=limit, select=select, order_by="lastModifiedDateTime desc"
                    )
                    for c in data.get("value", []) or []:
                        normalized = normalize_microsoft_contact(
                            c, account_email=account_email, account_name=account_name
                        )
                        results.append(Contact(**normalized))
            else:
                raise ServiceError(message=f"Unsupported provider: {provider}")

            return results, provider

        tasks = [_fetch(p) for p in valid_providers]
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)

        contacts: List[Contact] = []
        provider_errors: Dict[str, str] = {}
        providers_used: List[str] = []

        for i, result in enumerate(provider_results):
            prov = valid_providers[i]
            if isinstance(result, Exception):
                logger.error(f"Exception for provider {prov}: {result}")
                provider_errors[prov] = str(result)
                continue
            if isinstance(result, tuple) and len(result) == 2:
                res_contacts, prov_used = result
                contacts.extend(res_contacts)
                providers_used.append(prov_used)
            else:
                logger.error(f"Invalid result format for provider {prov}: {result}")
                provider_errors[prov] = "Invalid result format"
                continue

        # Apply client-side search filter
        if q:
            q_low = q.lower()
            contacts = [
                c
                for c in contacts
                if (c.full_name and q_low in c.full_name.lower())
                or any(q_low in e.email.lower() for e in c.emails)
            ]

        if company:
            comp_low = company.lower()

            def _domain_from_email(e: str) -> Optional[str]:
                return e.split("@", 1)[1].lower() if "@" in e else None

            filtered: List[Contact] = []
            for c in contacts:
                if c.company and comp_low in c.company.lower():
                    filtered.append(c)
                    continue
                # fall back to email domain match
                for e in c.emails:
                    dom = _domain_from_email(e.email)
                    if dom and comp_low in dom:
                        filtered.append(c)
                        break
            contacts = filtered

        # Trim to limit
        contacts = contacts[:limit]

        response_data: Dict[str, Any] = {
            "contacts": [c.model_dump() for c in contacts],
            "total_count": len(contacts),
            "providers_used": providers_used,
            "provider_errors": provider_errors if provider_errors else None,
            "request_metadata": {
                "user_id": user_id,
                "providers_requested": valid_providers,
                "limit": limit,
                "query": q or "",
                "company": company or "",
            },
        }

        if providers_used:
            await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=900)

        return ContactList(
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
        logger.error(f"Contacts list failed: {e}")
        raise ServiceError(message=f"Failed to fetch contacts: {str(e)}")


@router.post("/", response_model=ContactCreateResponse)
async def create_contact(
    request: Request,
    service_name: str = Depends(service_permission_required(["write_contacts"])),
    provider: Optional[str] = Query(
        None,
        description="Provider to create contact in (google, microsoft) - optional if provided in JSON body",
    ),
    full_name: Optional[str] = Query(None),
    given_name: Optional[str] = Query(None),
    family_name: Optional[str] = Query(None),
    emails: Optional[List[str]] = Query(None),
    company: Optional[str] = Query(None),
    job_title: Optional[str] = Query(None),
    phones: Optional[List[str]] = Query(None),
    payload: Optional[_ContactCreatePayload] = Body(None),
) -> ContactCreateResponse:
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    # Prefer JSON body if present, else use query params for backward compatibility
    if payload is not None:
        provider = payload.provider or provider
        full_name = payload.full_name if payload.full_name is not None else full_name
        given_name = (
            payload.given_name if payload.given_name is not None else given_name
        )
        family_name = (
            payload.family_name if payload.family_name is not None else family_name
        )
        emails = (
            _extract_email_strings(payload.emails)
            if payload.emails is not None
            else emails
        )
        company = payload.company if payload.company is not None else company
        job_title = payload.job_title if payload.job_title is not None else job_title
        phones = payload.phones if payload.phones is not None else phones

    if not provider:
        raise ValidationError(message="Invalid provider", field="provider")

    prov_enum = get_provider_enum(provider)
    if prov_enum is None:
        raise ValidationError(message="Invalid provider", field="provider")

    factory = await get_api_client_factory()
    scopes = _get_contact_scopes(provider, write=True)
    client = await factory.create_client(user_id, provider, scopes=scopes)
    if client is None:
        raise ServiceError(message=f"No client for provider {provider}")

    account_email, account_name = get_user_account_info(user_id, provider)

    try:
        if provider == "google":
            person: Dict[str, Any] = {}
            if full_name or given_name or family_name:
                person["names"] = [
                    {
                        k: v
                        for k, v in {
                            "displayName": full_name,
                            "givenName": given_name,
                            "familyName": family_name,
                        }.items()
                        if v
                    }
                ]
            if emails:
                person["emailAddresses"] = [{"value": e} for e in emails]
            if company or job_title:
                person["organizations"] = [
                    {
                        k: v
                        for k, v in {"name": company, "title": job_title}.items()
                        if v
                    }
                ]
            if phones:
                person["phoneNumbers"] = [{"value": p} for p in phones]
            created = await client.create_contact(person)
            normalized = normalize_google_contact(created, account_email, account_name)
        elif provider == "microsoft":
            ms_payload: Dict[str, Any] = {}
            if full_name:
                ms_payload["displayName"] = full_name
            if given_name:
                ms_payload["givenName"] = given_name
            if family_name:
                ms_payload["surname"] = family_name
            if emails:
                ms_payload["emailAddresses"] = [{"address": e} for e in emails]
            if company:
                ms_payload["companyName"] = company
            if job_title:
                ms_payload["jobTitle"] = job_title
            if phones:
                ms_payload["businessPhones"] = phones
            created = await client.create_contact(ms_payload)
            normalized = normalize_microsoft_contact(
                created, account_email, account_name
            )
        else:
            raise ServiceError(message=f"Unsupported provider: {provider}")

        # Invalidate contacts cache for this user
        await _invalidate_contacts_cache(user_id)
        return ContactCreateResponse(
            success=True,
            contact=normalized,
            request_id=request_id,
        )
    except Exception as e:
        raise ServiceError(message=f"Failed to create contact: {str(e)}")


@router.put("/{contact_id:path}", response_model=ContactUpdateResponse)
async def update_contact(
    request: Request,
    contact_id: str = Path(
        ...,
        description="Unified contact id (provider_originalId) or provider id for write-through",
    ),
    service_name: str = Depends(service_permission_required(["write_contacts"])),
    provider: Optional[str] = Query(
        None,
        description="Provider to update in (if unified id not used) - optional if provided in JSON body",
    ),
    full_name: Optional[str] = Query(None),
    given_name: Optional[str] = Query(None),
    family_name: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    job_title: Optional[str] = Query(None),
    emails: Optional[List[str]] = Query(None),
    phones: Optional[List[str]] = Query(None),
    payload: Optional[_ContactUpdatePayload] = Body(None),
) -> ContactUpdateResponse:
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()

    # Prefer JSON body if present, else use query params for backward compatibility
    if payload is not None:
        provider = payload.provider or provider
        full_name = payload.full_name if payload.full_name is not None else full_name
        given_name = (
            payload.given_name if payload.given_name is not None else given_name
        )
        family_name = (
            payload.family_name if payload.family_name is not None else family_name
        )
        company = payload.company if payload.company is not None else company
        job_title = payload.job_title if payload.job_title is not None else job_title
        emails = (
            _extract_email_strings(payload.emails)
            if payload.emails is not None
            else emails
        )
        phones = payload.phones if payload.phones is not None else phones

    prov = provider
    prov_id = contact_id
    if "_" in contact_id and not provider:
        prov, prov_id = contact_id.split("_", 1)
    # Normalize provider aliases
    if prov:
        if prov.lower() in ("gmail", "google"):
            prov = "google"
        elif prov.lower() in ("outlook", "microsoft"):
            prov = "microsoft"
    if prov is None:
        raise ValidationError(
            message="Provider required when contact_id is provider-native id",
            field="provider",
        )

    prov_enum = get_provider_enum(prov)
    if prov_enum is None:
        raise ValidationError(message="Invalid provider", field="provider")

    factory = await get_api_client_factory()
    scopes = _get_contact_scopes(prov, write=True)
    client = await factory.create_client(user_id, prov, scopes=scopes)
    if client is None:
        raise ServiceError(message=f"No client for provider {prov}")

    account_email, account_name = get_user_account_info(user_id, prov)

    try:
        if prov == "google":
            person: Dict[str, Any] = {}
            if full_name or given_name or family_name:
                person["names"] = [
                    {
                        k: v
                        for k, v in {
                            "displayName": full_name,
                            "givenName": given_name,
                            "familyName": family_name,
                        }.items()
                        if v
                    }
                ]
            if emails is not None:
                person["emailAddresses"] = [{"value": e} for e in emails]
            if company is not None or job_title is not None:
                person["organizations"] = [
                    {
                        k: v
                        for k, v in {"name": company, "title": job_title}.items()
                        if v
                    }
                ]
            if phones is not None:
                person["phoneNumbers"] = [{"value": p} for p in phones]
            updated = await client.update_contact(
                f"people/{prov_id}" if not prov_id.startswith("people/") else prov_id,
                person,
            )
            normalized = normalize_google_contact(updated, account_email, account_name)
        elif prov == "microsoft":
            ms_payload: Dict[str, Any] = {}
            if full_name is not None:
                ms_payload["displayName"] = full_name
            if given_name is not None:
                ms_payload["givenName"] = given_name
            if family_name is not None:
                ms_payload["surname"] = family_name
            if company is not None:
                ms_payload["companyName"] = company
            if job_title is not None:
                ms_payload["jobTitle"] = job_title
            if emails is not None:
                ms_payload["emailAddresses"] = [{"address": e} for e in emails]
            if phones is not None:
                ms_payload["businessPhones"] = phones
            updated = await client.update_contact(prov_id, ms_payload)
            normalized = normalize_microsoft_contact(
                updated, account_email, account_name
            )
        else:
            raise ServiceError(message=f"Unsupported provider: {prov}")

        await _invalidate_contacts_cache(user_id)
        return ContactUpdateResponse(
            success=True,
            contact=normalized,
            request_id=request_id,
        )
    except Exception as e:
        raise ServiceError(message=f"Failed to update contact: {str(e)}")


@router.delete("/{contact_id:path}", response_model=ContactDeleteResponse)
async def delete_contact(
    contact_id: str,
    request: Request,
    service_name: str = Depends(service_permission_required(["write_contacts"])),
    provider: Optional[str] = Query(
        None, description="Provider to delete in (if unified id not used)"
    ),
) -> ContactDeleteResponse:
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()

    prov = provider
    prov_id = contact_id
    if "_" in contact_id and not provider:
        prov, prov_id = contact_id.split("_", 1)
    if prov is None:
        raise ValidationError(
            message="Provider required when contact_id is provider-native id",
            field="provider",
        )

    prov_enum = get_provider_enum(prov)
    if prov_enum is None:
        raise ValidationError(message="Invalid provider", field="provider")

    factory = await get_api_client_factory()
    scopes = _get_contact_scopes(prov, write=True)
    client = await factory.create_client(user_id, prov, scopes=scopes)
    if client is None:
        raise ServiceError(message=f"No client for provider {prov}")

    try:
        # Normalize provider aliases
        prov_norm = prov.lower()
        if prov_norm in ("gmail", "google"):
            prov_norm = "google"
        elif prov_norm in ("outlook", "microsoft"):
            prov_norm = "microsoft"

        if prov_norm == "google":
            await client.delete_contact(
                f"people/{prov_id}" if not prov_id.startswith("people/") else prov_id
            )
        elif prov_norm == "microsoft":
            await client.delete_contact(prov_id)
        else:
            raise ServiceError(message=f"Unsupported provider: {prov}")
        # Invalidate caches for this user's contacts
        await _invalidate_contacts_cache(user_id)
        return ContactDeleteResponse(
            success=True,
            deleted_contact_id=contact_id,
            request_id=request_id,
        )
    except Exception as e:
        raise ServiceError(message=f"Failed to delete contact: {str(e)}")
