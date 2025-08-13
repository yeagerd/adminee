from typing import Any, Dict, List, Optional, Tuple
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, Path

from services.common.http_errors import ServiceError, ValidationError
from services.common.logging_config import get_logger, request_id_var
from services.office.core.api_client_factory import APIClientFactory
from services.office.core.auth import service_permission_required
from services.office.core.cache_manager import cache_manager, generate_cache_key
from services.office.core.clients.google import GoogleAPIClient
from services.office.core.clients.microsoft import MicrosoftAPIClient
from services.office.core.normalizer import normalize_google_contact, normalize_microsoft_contact
from services.office.models import Provider
from services.office.schemas import ContactsListApiResponse, Contact
from services.office.api.email import get_user_account_info, get_provider_enum

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


async def get_user_id_from_gateway(request: Request) -> str:
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise ValidationError(message="X-User-Id header is required", field="X-User-Id")
    return user_id


def _get_contact_scopes(provider: str, write: bool = False) -> List[str]:
    if provider == "google":
        return [
            "https://www.googleapis.com/auth/contacts.readonly" if not write else "https://www.googleapis.com/auth/contacts",
        ]
    elif provider == "microsoft":
        return [
            "https://graph.microsoft.com/Contacts.ReadWrite" if write else "https://graph.microsoft.com/Contacts.Read",
        ]
    return []


@router.get("/", response_model=ContactsListApiResponse)
async def list_contacts(
    request: Request,
    service_name: str = Depends(service_permission_required(["read_contacts"])),
    providers: Optional[List[str]] = Query(None, description="Providers to fetch from (google, microsoft)."),
    limit: int = Query(100, ge=1, le=500),
    q: Optional[str] = Query(None, description="Free-text search (name or email)"),
    company: Optional[str] = Query(None, description="Filter by company or email domain"),
    no_cache: bool = Query(False, description="Bypass cache and fetch fresh data from providers"),
) -> ContactsListApiResponse:
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()

    try:
        if not providers:
            providers = ["google", "microsoft"]
        valid_providers = [p for p in providers if p in ["google", "microsoft"]]
        if not valid_providers:
            raise ValidationError(message="No valid providers specified", field="providers")

        cache_params = {"providers": valid_providers, "limit": limit, "q": q or "", "company": company or ""}
        cache_key = generate_cache_key(user_id, "unified", "contacts", cache_params)

        if not no_cache:
            cached = await cache_manager.get_from_cache(cache_key)
            if cached:
                return ContactsListApiResponse(success=True, data=cached, cache_hit=True, request_id=request_id)

        factory = await get_api_client_factory()

        async def _fetch(provider: str) -> Tuple[List[Contact], str]:
            scopes = _get_contact_scopes(provider, write=False)
            client = await factory.create_client(user_id, provider, scopes=scopes)
            if client is None:
                raise ServiceError(message=f"No client for provider {provider}")

            results: List[Contact] = []
            # Determine account context for this provider
            account_email, account_name = get_user_account_info(user_id, provider)
            if isinstance(client, GoogleAPIClient):
                data = await client.get_contacts(page_size=limit)
                for c in data.get("connections", []) or []:
                    normalized = normalize_google_contact(c, account_email=account_email, account_name=account_name)
                    results.append(Contact(**normalized))
            elif isinstance(client, MicrosoftAPIClient):
                select = "id,displayName,givenName,surname,emailAddresses,companyName,jobTitle,businessPhones,mobilePhone,homePhones"
                data = await client.get_contacts(top=limit, select=select, order_by="lastModifiedDateTime desc")
                for c in data.get("value", []) or []:
                    normalized = normalize_microsoft_contact(c, account_email=account_email, account_name=account_name)
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
                provider_errors[prov] = str(result)
                continue
            if isinstance(result, tuple) and len(result) == 2:
                res_contacts, prov_used = result
                contacts.extend(res_contacts)
                providers_used.append(prov_used)
            else:
                provider_errors[prov] = "Invalid result format"
                continue

        # Apply client-side search filter
        if q:
            q_low = q.lower()
            contacts = [c for c in contacts if (c.full_name and q_low in c.full_name.lower()) or any(q_low in e.email.lower() for e in c.emails)]

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

        return ContactsListApiResponse(success=True, data=response_data, cache_hit=False, provider_used=(Provider(providers_used[0]) if len(providers_used) == 1 else None), request_id=request_id)
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Contacts list failed: {e}")
        raise ServiceError(message=f"Failed to fetch contacts: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_contact(
    request: Request,
    service_name: str = Depends(service_permission_required(["write_contacts"])),
    provider: str = Query(..., description="Provider to create contact in (google, microsoft)"),
    full_name: Optional[str] = None,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    emails: Optional[List[str]] = Query(None),
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    phones: Optional[List[str]] = Query(None),
) -> Dict[str, Any]:
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
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
        if isinstance(client, GoogleAPIClient):
            person: Dict[str, Any] = {}
            if full_name or given_name or family_name:
                person["names"] = [{k: v for k, v in {"displayName": full_name, "givenName": given_name, "familyName": family_name}.items() if v}]
            if emails:
                person["emailAddresses"] = [{"value": e} for e in emails]
            if company or job_title:
                person["organizations"] = [{k: v for k, v in {"name": company, "title": job_title}.items() if v}]
            if phones:
                person["phoneNumbers"] = [{"value": p} for p in phones]
            created = await client.create_contact(person)
            normalized = normalize_google_contact(created, account_email, account_name)
        elif isinstance(client, MicrosoftAPIClient):
            payload: Dict[str, Any] = {}
            if full_name:
                payload["displayName"] = full_name
            if given_name:
                payload["givenName"] = given_name
            if family_name:
                payload["surname"] = family_name
            if emails:
                payload["emailAddresses"] = [{"address": e} for e in emails]
            if company:
                payload["companyName"] = company
            if job_title:
                payload["jobTitle"] = job_title
            if phones:
                payload["businessPhones"] = phones
            created = await client.create_contact(payload)
            normalized = normalize_microsoft_contact(created, account_email, account_name)
        else:
            raise ServiceError(message=f"Unsupported provider: {provider}")

        # Invalidate cache for this user
        await cache_manager.invalidate_user_cache(user_id)
        return {"success": True, "data": {"contact": normalized}, "request_id": request_id}
    except Exception as e:
        raise ServiceError(message=f"Failed to create contact: {str(e)}")


@router.put("/{contact_id}", response_model=Dict[str, Any])
async def update_contact(
    contact_id: str = Path(..., description="Unified contact id (provider_originalId) or provider id for write-through"),
    request: Request = None,
    service_name: str = Depends(service_permission_required(["write_contacts"])),
    provider: Optional[str] = Query(None, description="Provider to update in (if unified id not used)"),
    full_name: Optional[str] = None,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    emails: Optional[List[str]] = Query(None),
    phones: Optional[List[str]] = Query(None),
) -> Dict[str, Any]:
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()

    prov = provider
    prov_id = contact_id
    if "_" in contact_id and not provider:
        prov, prov_id = contact_id.split("_", 1)
    if prov is None:
        raise ValidationError(message="Provider required when contact_id is provider-native id", field="provider")

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
        if isinstance(client, GoogleAPIClient):
            person: Dict[str, Any] = {}
            if full_name or given_name or family_name:
                person["names"] = [{k: v for k, v in {"displayName": full_name, "givenName": given_name, "familyName": family_name}.items() if v}]
            if emails is not None:
                person["emailAddresses"] = [{"value": e} for e in emails]
            if company is not None or job_title is not None:
                person["organizations"] = [{k: v for k, v in {"name": company, "title": job_title}.items() if v}]
            if phones is not None:
                person["phoneNumbers"] = [{"value": p} for p in phones]
            updated = await client.update_contact(f"people/{prov_id}" if not prov_id.startswith("people/") else prov_id, person)
            normalized = normalize_google_contact(updated, account_email, account_name)
        elif isinstance(client, MicrosoftAPIClient):
            payload: Dict[str, Any] = {}
            if full_name is not None:
                payload["displayName"] = full_name
            if given_name is not None:
                payload["givenName"] = given_name
            if family_name is not None:
                payload["surname"] = family_name
            if company is not None:
                payload["companyName"] = company
            if job_title is not None:
                payload["jobTitle"] = job_title
            if emails is not None:
                payload["emailAddresses"] = [{"address": e} for e in emails]
            if phones is not None:
                payload["businessPhones"] = phones
            updated = await client.update_contact(prov_id, payload)
            normalized = normalize_microsoft_contact(updated, account_email, account_name)
        else:
            raise ServiceError(message=f"Unsupported provider: {prov}")

        await cache_manager.invalidate_user_cache(user_id)
        return {"success": True, "data": {"contact": normalized}, "request_id": request_id}
    except Exception as e:
        raise ServiceError(message=f"Failed to update contact: {str(e)}")


@router.delete("/{contact_id}", response_model=Dict[str, Any])
async def delete_contact(
    contact_id: str,
    request: Request,
    service_name: str = Depends(service_permission_required(["write_contacts"])),
    provider: Optional[str] = Query(None, description="Provider to delete in (if unified id not used)"),
) -> Dict[str, Any]:
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()

    prov = provider
    prov_id = contact_id
    if "_" in contact_id and not provider:
        prov, prov_id = contact_id.split("_", 1)
    if prov is None:
        raise ValidationError(message="Provider required when contact_id is provider-native id", field="provider")

    prov_enum = get_provider_enum(prov)
    if prov_enum is None:
        raise ValidationError(message="Invalid provider", field="provider")

    factory = await get_api_client_factory()
    scopes = _get_contact_scopes(prov, write=True)
    client = await factory.create_client(user_id, prov, scopes=scopes)
    if client is None:
        raise ServiceError(message=f"No client for provider {prov}")

    try:
        if isinstance(client, GoogleAPIClient):
            await client.delete_contact(f"people/{prov_id}" if not prov_id.startswith("people/") else prov_id)
        elif isinstance(client, MicrosoftAPIClient):
            await client.delete_contact(prov_id)
        else:
            raise ServiceError(message=f"Unsupported provider: {prov}")
        await cache_manager.invalidate_user_cache(user_id)
        return {"success": True, "data": {"deleted": True}, "request_id": request_id}
    except Exception as e:
        raise ServiceError(message=f"Failed to delete contact: {str(e)}")