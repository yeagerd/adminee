import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import services.shipments.database as shipments_database
from services.shipments.models import (
    Package,
    PackageStatus,
    TrackingEvent,
)


@pytest.fixture(autouse=True)
def patch_settings_and_engine():
    """Patch settings and engine to use a shared in-memory SQLite DB for all connections."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    import services.shipments.settings as shipments_settings

    # Use file-based SQLite URI for shared access across async connections
    shared_db_url = "sqlite+aiosqlite:///./test_shipments.db"
    test_settings = shipments_settings.Settings(
        db_url_shipments=shared_db_url,
        api_frontend_shipments_key="test-frontend-shipments-key",
    )

    # Store original settings for cleanup
    original_settings = shipments_settings._settings

    # Directly set the singleton instead of using monkeypatch
    shipments_settings._settings = test_settings
    print(
        f"DEBUG: Patched API key in settings: {shipments_settings._settings.api_frontend_shipments_key}"
    )

    # Create a single engine instance that will be shared
    engine = create_async_engine(shared_db_url, future=True)

    # Store original functions for cleanup
    original_get_engine = shipments_database.get_engine
    original_get_async_session_dep = shipments_database.get_async_session_dep

    # Patch both functions to use the shared engine
    shipments_database.get_engine = lambda: engine

    # Create a new session dependency that uses the shared engine
    async def patched_get_async_session_dep():
        async with AsyncSession(engine) as session:
            yield session

    shipments_database.get_async_session_dep = patched_get_async_session_dep

    yield

    # Restore original functions
    shipments_settings._settings = original_settings
    shipments_database.get_engine = original_get_engine
    shipments_database.get_async_session_dep = original_get_async_session_dep


@pytest.fixture
def client(db_session):
    from services.shipments.database import get_async_session_dep
    from services.shipments.main import app

    # Override the database dependency to use our test session
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_async_session_dep] = override_get_session

    client = TestClient(app)
    yield client

    # Clean up the override
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-frontend-shipments-key", "X-User-Id": "test-user-123"}


@pytest_asyncio.fixture
async def db_session():
    from services.shipments.database import get_engine
    from services.shipments.models import SQLModel

    # Create tables (only once per test session)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create a single session that will be shared
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncSession(engine)

    yield session

    # Clean up database after each test
    await session.rollback()
    # Delete all data from tables to ensure clean state
    import sqlalchemy as sa

    await session.execute(sa.text("DELETE FROM trackingevent"))
    await session.execute(sa.text("DELETE FROM packagelabel"))
    await session.execute(sa.text("DELETE FROM package"))
    await session.execute(sa.text("DELETE FROM label"))
    await session.execute(sa.text("DELETE FROM carrierconfig"))
    await session.commit()
    await session.close()


class TestEndpointAuthentication:
    """Test that all endpoints require proper API key authentication."""

    def test_carrier_configs_endpoint_requires_auth(self, client):
        """Test that carrier configs endpoint requires authentication."""
        # Test without API key
        response = client.get("/v1/shipments/carriers/")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test with invalid API key
        response = client.get(
            "/v1/shipments/carriers/", headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

    def test_labels_endpoints_require_auth(self, client):
        """Test that labels endpoints require authentication."""
        # Test list labels without API key
        response = client.get("/v1/shipments/labels/")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test create label without API key
        response = client.post("/v1/shipments/labels/", json={})
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test update label without API key
        response = client.put("/v1/shipments/labels/1", json={})
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test delete label without API key
        response = client.delete("/v1/shipments/labels/1")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

    def test_tracking_events_endpoint_requires_auth(self, client):
        """Test that tracking events endpoint requires authentication."""
        # Test without any authentication
        response = client.get("/v1/shipments/packages/1/events")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

    def test_packages_endpoints_require_auth(self, client):
        """Test that packages endpoints require authentication."""
        # Test list packages without API key
        response = client.get("/v1/shipments/packages/")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test create package without API key
        response = client.post("/v1/shipments/packages/", json={})
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test get package without API key
        response = client.get("/v1/shipments/packages/1")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test update package without API key
        response = client.put("/v1/shipments/packages/1", json={})
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test delete package without API key
        response = client.delete("/v1/shipments/packages/1")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test refresh package without API key
        response = client.post("/v1/shipments/packages/1/refresh")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test add label to package without API key
        response = client.post("/v1/shipments/packages/1/labels")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

        # Test remove label from package without API key
        response = client.delete("/v1/shipments/packages/1/labels/1")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["message"]

    def test_valid_api_key_works(self, client):
        """Test that valid API key allows access."""
        # Test with valid API key and user authentication
        response = client.get(
            "/v1/shipments/carriers/",
            headers={"X-API-Key": "test-api-key", "X-User-Id": "test-user-123"},
        )
        # Should not return 401 (authentication error)
        assert response.status_code != 401


@pytest.mark.asyncio
class TestPackageTrackingSearch:
    """Test package tracking search functionality, including carrier filtering."""

    async def test_tracking_search_single_package(
        self, client, auth_headers, db_session
    ):
        import services.shipments.settings as shipments_settings

        print(
            f"DEBUG: API key in settings before API call: {shipments_settings._settings.api_frontend_shipments_key}"
        )
        # Create a test package using the API
        package_data = {
            "tracking_number": "123456789012",
            "carrier": "fedex",
            "status": "IN_TRANSIT",
        }
        create_response = client.post(
            "/v1/shipments/packages/", json=package_data, headers=auth_headers
        )
        print(
            f"DEBUG: POST response status: {create_response.status_code}, body: {create_response.json()}"
        )
        assert create_response.status_code == 200

        # Search by tracking number
        response = client.get(
            "/v1/shipments/packages/?tracking_number=123456789012", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["packages"]) == 1
        assert data["packages"][0]["tracking_number"] == "123456789012"
        assert data["packages"][0]["carrier"] == "fedex"

    async def test_tracking_search_multiple_packages_no_carrier(
        self, client, auth_headers, db_session
    ):
        """Test tracking search when multiple packages exist but no carrier specified."""
        # Create multiple packages with same tracking number but different carriers using the API
        package1_data = {
            "tracking_number": "123456789013",
            "carrier": "fedex",
            "status": "IN_TRANSIT",
        }
        package2_data = {
            "tracking_number": "123456789013",
            "carrier": "ups",
            "status": "DELIVERED",
        }
        create_response1 = client.post(
            "/v1/shipments/packages/", json=package1_data, headers=auth_headers
        )
        assert create_response1.status_code == 200
        create_response2 = client.post(
            "/v1/shipments/packages/", json=package2_data, headers=auth_headers
        )
        assert create_response2.status_code == 200

        # Search by tracking number without carrier
        response = client.get(
            "/v1/shipments/packages/?tracking_number=123456789013", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["packages"]) == 2
        carriers = [pkg["carrier"] for pkg in data["packages"]]
        assert "fedex" in carriers
        assert "ups" in carriers

    async def test_tracking_search_multiple_packages_with_carrier_filter(
        self, client, auth_headers, db_session
    ):
        """Test tracking search with carrier filter - this would have caught the bug."""
        # Create multiple packages with same tracking number but different carriers
        package1 = Package(
            user_id="test-user-123",
            tracking_number="TEST123456790B",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        package2 = Package(
            user_id="test-user-123",
            tracking_number="TEST123456790B",
            carrier="ups",
            status=PackageStatus.DELIVERED,
        )
        package3 = Package(
            user_id="test-user-123",
            tracking_number="TEST123456790B",
            carrier="unknown",
            status=PackageStatus.PENDING,
        )
        db_session.add_all([package1, package2, package3])
        await db_session.commit()

        # Search by tracking number with carrier filter
        response = client.get(
            "/v1/shipments/packages/?tracking_number=test-123456790B&carrier=fedex",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return packages with carrier "fedex" or "unknown"
        assert len(data["packages"]) == 2
        carriers = [pkg["carrier"] for pkg in data["packages"]]
        assert "fedex" in carriers
        assert "unknown" in carriers
        assert "ups" not in carriers

    async def test_tracking_search_carrier_filter_excludes_other_carriers(
        self, client, auth_headers, db_session
    ):
        """Test that carrier filter properly excludes packages with other carriers."""
        # Create packages with same tracking number but different carriers
        package1 = Package(
            user_id="test-user-123",
            tracking_number="TEST123456791C",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        package2 = Package(
            user_id="test-user-123",
            tracking_number="TEST123456791C",
            carrier="ups",
            status=PackageStatus.DELIVERED,
        )
        package3 = Package(
            user_id="test-user-123",
            tracking_number="TEST123456791C",
            carrier="usps",
            status=PackageStatus.PENDING,
        )
        db_session.add_all([package1, package2, package3])
        await db_session.commit()

        # Search by tracking number with specific carrier filter
        response = client.get(
            "/v1/shipments/packages/?tracking_number=test-123456791C&carrier=ups",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return packages with carrier "ups" or "unknown"
        assert len(data["packages"]) == 1
        assert data["packages"][0]["carrier"] == "ups"

    async def test_tracking_search_carrier_unknown_handling(
        self, client, auth_headers, db_session
    ):
        """Test that carrier filter handles 'unknown' carrier correctly."""
        # Use a valid FedEx tracking number
        tracking_number = "123456789014"
        # Create packages with same tracking number using the API
        package1_data = {
            "tracking_number": tracking_number,
            "carrier": "fedex",
            "status": "IN_TRANSIT",
        }
        package2_data = {
            "tracking_number": tracking_number,
            "carrier": "unknown",
            "status": "PENDING",
        }
        create_response1 = client.post(
            "/v1/shipments/packages/", json=package1_data, headers=auth_headers
        )
        assert create_response1.status_code == 200
        create_response2 = client.post(
            "/v1/shipments/packages/", json=package2_data, headers=auth_headers
        )
        assert create_response2.status_code == 200

        # Search by tracking number with carrier="unknown"
        response = client.get(
            f"/v1/shipments/packages/?tracking_number={tracking_number}&carrier=unknown",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should return all packages (no additional filtering when carrier is "unknown")
        assert len(data["packages"]) == 2

    async def test_tracking_search_different_users_isolation(
        self, client, auth_headers, db_session
    ):
        """Test that tracking search only returns packages for the authenticated user."""
        # Use a valid tracking number
        tracking_number = "123456789015"
        # Create package for the authenticated user using the API
        package1_data = {
            "tracking_number": tracking_number,
            "carrier": "fedex",
            "status": "IN_TRANSIT",
        }
        create_response1 = client.post(
            "/v1/shipments/packages/", json=package1_data, headers=auth_headers
        )
        assert create_response1.status_code == 200
        # Create package for a different user by direct DB insert
        package2 = Package(
            user_id="other-user-456",
            tracking_number=tracking_number,
            carrier="ups",
            status=PackageStatus.DELIVERED,
        )
        db_session.add(package2)
        await db_session.commit()

        # Search by tracking number
        response = client.get(
            f"/v1/shipments/packages/?tracking_number={tracking_number}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return package for the authenticated user
        assert len(data["packages"]) == 1
        assert data["packages"][0]["user_id"] == "test-user-123"
        assert data["packages"][0]["carrier"] == "fedex"

    async def test_tracking_search_with_email_message_id(
        self, client, auth_headers, db_session
    ):
        """Test tracking search by email message ID."""
        # Use a valid tracking number
        tracking_number = "123456789016"
        # Create a package using the API
        package_data = {
            "tracking_number": tracking_number,
            "carrier": "fedex",
            "status": "IN_TRANSIT",
        }
        create_response = client.post(
            "/v1/shipments/packages/", json=package_data, headers=auth_headers
        )
        assert create_response.status_code == 200
        # Fetch the package via the API to get its ID
        get_response = client.get(
            f"/v1/shipments/packages/?tracking_number={tracking_number}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200
        from uuid import UUID

        package_id = UUID(get_response.json()["packages"][0]["id"])
        # Create a tracking event with email message ID
        from datetime import datetime

        event_date = datetime.fromisoformat(
            get_response.json()["packages"][0]["updated_at"]
        )
        # Create a tracking event with email message ID
        event = TrackingEvent(
            package_id=package_id,
            event_date=event_date,
            status=PackageStatus.IN_TRANSIT,
            email_message_id="email-123",
        )
        db_session.add(event)
        await db_session.commit()

        # Search by email message ID
        response = client.get(
            "/v1/shipments/packages/?email_message_id=email-123", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["packages"]) == 1
        assert data["packages"][0]["tracking_number"] == tracking_number

    async def test_tracking_search_email_message_id_not_found(
        self, client, auth_headers, db_session
    ):
        """Test tracking search by email message ID when no matching event exists."""
        # Search by non-existent email message ID
        response = client.get(
            "/v1/shipments/packages/?email_message_id=nonexistent-email",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["packages"]) == 0
        # New pagination format doesn't include total count
        assert not data["has_next"]
        assert not data["has_prev"]
