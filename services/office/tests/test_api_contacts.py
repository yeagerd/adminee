from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.office.app.main import app


@pytest.fixture(autouse=True)
def patch_settings():
    import services.office.core.settings as office_settings

    test_settings = office_settings.Settings(
        db_url_office="sqlite:///:memory:",
        api_frontend_office_key="test-frontend-office-key",
        api_chat_office_key="test-chat-office-key",
        api_meetings_office_key="test-meetings-office-key",
        api_office_user_key="test-office-user-key",
    )
    office_settings._settings = test_settings
    yield
    office_settings._settings = None


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-User-Id": "test_user", "X-API-Key": "test-frontend-office-key"}


class TestContactsApi:
    @pytest.mark.asyncio
    async def test_list_contacts_success(self, client, auth_headers):
        with (
            patch("services.office.api.contacts.cache_manager") as mock_cache,
            patch(
                "services.office.api.contacts.get_api_client_factory"
            ) as mock_factory,
        ):
            mock_cache.get_from_cache = AsyncMock(return_value=None)
            mock_cache.set_to_cache = AsyncMock()

            # Mock factory.create_client to return fake clients with get_contacts
            class FakeGoogle:
                async def get_contacts(self, page_size=200):
                    return {
                        "connections": [
                            {
                                "resourceName": "people/123",
                                "names": [
                                    {
                                        "displayName": "Alice",
                                        "givenName": "Alice",
                                        "familyName": "A",
                                    }
                                ],
                                "emailAddresses": [{"value": "alice@example.com"}],
                                "organizations": [{"name": "Example", "title": "CEO"}],
                            }
                        ]
                    }

            class FakeMS:
                async def get_contacts(self, top=200, select=None, order_by=None):
                    return {
                        "value": [
                            {
                                "id": "abc",
                                "displayName": "Bob B",
                                "givenName": "Bob",
                                "surname": "B",
                                "emailAddresses": [
                                    {"address": "bob@contoso.com", "name": "Bob B"}
                                ],
                                "companyName": "Contoso",
                                "jobTitle": "CTO",
                                "businessPhones": ["+1-555-0100"],
                            }
                        ]
                    }

            class FakeFactory:
                async def create_client(self, user_id, provider, scopes=None):
                    if provider == "google":
                        return FakeGoogle()
                    if provider == "microsoft":
                        return FakeMS()
                    return None

            mock_factory.return_value = FakeFactory()

            resp = client.get("/v1/contacts?limit=10", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert isinstance(data["data"].get("contacts"), list)
            assert data["data"]["total_count"] >= 1

    @pytest.mark.asyncio
    async def test_list_contacts_cache_hit(self, client, auth_headers):
        with patch("services.office.api.contacts.cache_manager") as mock_cache:
            mock_cache.get_from_cache = AsyncMock(
                return_value={
                    "contacts": [],
                    "total_count": 0,
                    "providers_used": ["google"],
                }
            )
            resp = client.get("/v1/contacts?limit=5", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["cache_hit"] is True

    @pytest.mark.asyncio
    async def test_list_contacts_invalid_provider(self, client, auth_headers):
        resp = client.get("/v1/contacts?providers=invalid", headers=auth_headers)
        assert resp.status_code == 422
        assert "No valid providers specified" in resp.json()["message"]

    @pytest.mark.asyncio
    async def test_list_contacts_missing_user(self, client):
        headers = {"X-API-Key": "test-frontend-office-key"}
        resp = client.get("/v1/contacts", headers=headers)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_contact_google(self, client, auth_headers):
        with (
            patch(
                "services.office.api.contacts.get_api_client_factory"
            ) as mock_factory,
            patch("services.office.api.contacts.cache_manager") as mock_cache,
        ):
            mock_cache.invalidate_user_cache = AsyncMock()

            class FakeGoogle:
                async def create_contact(self, person):
                    # echo with an id
                    return {"resourceName": "people/xyz", **person}

            class FakeFactory:
                async def create_client(self, user_id, provider, scopes=None):
                    return FakeGoogle()

            mock_factory.return_value = FakeFactory()
            resp = client.post(
                "/v1/contacts?provider=google&full_name=Alice%20A&emails=alice@example.com",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["contact"]["id"].startswith("google_")

    @pytest.mark.asyncio
    async def test_update_contact_microsoft(self, client, auth_headers):
        with (
            patch(
                "services.office.api.contacts.get_api_client_factory"
            ) as mock_factory,
            patch("services.office.api.contacts.cache_manager") as mock_cache,
        ):
            mock_cache.invalidate_user_cache = AsyncMock()

            class FakeMS:
                async def update_contact(self, cid, payload):
                    return {"id": cid, **payload}

            class FakeFactory:
                async def create_client(self, user_id, provider, scopes=None):
                    return FakeMS()

            mock_factory.return_value = FakeFactory()
            resp = client.put(
                "/v1/contacts/outlook_abc?full_name=Bob%20B", headers=auth_headers
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["contact"]["id"].startswith("outlook_")

    @pytest.mark.asyncio
    async def test_update_contact_google_with_slash(self, client, auth_headers):
        with (
            patch(
                "services.office.api.contacts.get_api_client_factory"
            ) as mock_factory,
            patch("services.office.api.contacts.cache_manager") as mock_cache,
        ):
            mock_cache.invalidate_user_cache = AsyncMock()

            class FakeGoogle:
                async def update_contact(self, resource_name, payload):
                    return {"resourceName": resource_name, **payload}

            class FakeFactory:
                async def create_client(self, user_id, provider, scopes=None):
                    return FakeGoogle()

            mock_factory.return_value = FakeFactory()
            resp = client.put(
                "/v1/contacts/google_people%2Fxyz?full_name=Alice%20Updated", headers=auth_headers
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["contact"]["id"].startswith("google_")

    @pytest.mark.asyncio
    async def test_delete_contact_google(self, client, auth_headers):
        with (
            patch(
                "services.office.api.contacts.get_api_client_factory"
            ) as mock_factory,
            patch("services.office.api.contacts.cache_manager") as mock_cache,
        ):
            mock_cache.invalidate_user_cache = AsyncMock()

            class FakeGoogle:
                async def delete_contact(self, resource_name):
                    return None

            class FakeFactory:
                async def create_client(self, user_id, provider, scopes=None):
                    return FakeGoogle()

            mock_factory.return_value = FakeFactory()
            resp = client.delete(
                "/v1/contacts/google_people%2Fxyz", headers=auth_headers
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["data"]["deleted"] is True
