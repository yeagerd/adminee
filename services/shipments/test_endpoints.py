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
def patch_settings_and_engine(monkeypatch):
    """Patch settings and engine to use a shared in-memory SQLite DB for all connections."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import services.shipments.settings as shipments_settings

    # Use shared in-memory SQLite URI
    shared_db_url = "sqlite+aiosqlite:///file::memory:?cache=shared"
    test_settings = shipments_settings.Settings(
        db_url_shipments=shared_db_url,
        api_frontend_shipments_key="test-api-key",
    )
    monkeypatch.setattr("services.shipments.settings._settings", test_settings)

    # Patch get_engine to always return the same engine instance
    engine = create_async_engine(shared_db_url, future=True)
    monkeypatch.setattr(shipments_database, "get_engine", lambda: engine)
    yield


@pytest.fixture
def client():
    from services.shipments.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-api-key", "X-User-Id": "test-user-123"}


@pytest_asyncio.fixture
async def db_session():
    from services.shipments.database import get_async_session_dep, get_engine
    from services.shipments.models import SQLModel

    # Create tables (only once per test session)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    # Get session
    async for session in get_async_session_dep():
        yield session
        break


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
        """Test tracking search when only one package exists."""
        # Create a test package
        package = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        db_session.add(package)
        await db_session.commit()

        # Search by tracking number
        response = client.get(
            "/v1/shipments/packages/?tracking_number=123456789", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["tracking_number"] == "123456789"
        assert data["data"][0]["carrier"] == "fedex"

    async def test_tracking_search_multiple_packages_no_carrier(
        self, client, auth_headers, db_session
    ):
        """Test tracking search when multiple packages exist but no carrier specified."""
        # Create multiple packages with same tracking number but different carriers
        package1 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        package2 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="ups",
            status=PackageStatus.DELIVERED,
        )
        db_session.add_all([package1, package2])
        await db_session.commit()

        # Search by tracking number without carrier
        response = client.get(
            "/v1/shipments/packages/?tracking_number=123456789", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        carriers = [pkg["carrier"] for pkg in data["data"]]
        assert "fedex" in carriers
        assert "ups" in carriers

    async def test_tracking_search_multiple_packages_with_carrier_filter(
        self, client, auth_headers, db_session
    ):
        """Test tracking search with carrier filter - this would have caught the bug."""
        # Create multiple packages with same tracking number but different carriers
        package1 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        package2 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="ups",
            status=PackageStatus.DELIVERED,
        )
        package3 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="unknown",
            status=PackageStatus.PENDING,
        )
        db_session.add_all([package1, package2, package3])
        await db_session.commit()

        # Search by tracking number with carrier filter
        response = client.get(
            "/v1/shipments/packages/?tracking_number=123456789&carrier=fedex",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return packages with carrier "fedex" or "unknown"
        assert len(data["data"]) == 2
        carriers = [pkg["carrier"] for pkg in data["data"]]
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
            tracking_number="123456789",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        package2 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="ups",
            status=PackageStatus.DELIVERED,
        )
        package3 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="usps",
            status=PackageStatus.PENDING,
        )
        db_session.add_all([package1, package2, package3])
        await db_session.commit()

        # Search by tracking number with specific carrier filter
        response = client.get(
            "/v1/shipments/packages/?tracking_number=123456789&carrier=ups",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return packages with carrier "ups" or "unknown"
        assert len(data["data"]) == 1
        assert data["data"][0]["carrier"] == "ups"

    async def test_tracking_search_carrier_unknown_handling(
        self, client, auth_headers, db_session
    ):
        """Test that carrier filter handles 'unknown' carrier correctly."""
        # Create packages with same tracking number
        package1 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        package2 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="unknown",
            status=PackageStatus.PENDING,
        )
        db_session.add_all([package1, package2])
        await db_session.commit()

        # Search by tracking number with carrier="unknown"
        response = client.get(
            "/v1/shipments/packages/?tracking_number=123456789&carrier=unknown",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should return all packages (no additional filtering when carrier is "unknown")
        assert len(data["data"]) == 2

    async def test_tracking_search_different_users_isolation(
        self, client, auth_headers, db_session
    ):
        """Test that tracking search only returns packages for the authenticated user."""
        # Create packages for different users with same tracking number
        package1 = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        package2 = Package(
            user_id="other-user-456",
            tracking_number="123456789",
            carrier="ups",
            status=PackageStatus.DELIVERED,
        )
        db_session.add_all([package1, package2])
        await db_session.commit()

        # Search by tracking number
        response = client.get(
            "/v1/shipments/packages/?tracking_number=123456789", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should only return package for the authenticated user
        assert len(data["data"]) == 1
        assert data["data"][0]["user_id"] == "test-user-123"
        assert data["data"][0]["carrier"] == "fedex"

    async def test_tracking_search_with_email_message_id(
        self, client, auth_headers, db_session
    ):
        """Test tracking search by email message ID."""
        # Create a package
        package = Package(
            user_id="test-user-123",
            tracking_number="123456789",
            carrier="fedex",
            status=PackageStatus.IN_TRANSIT,
        )
        db_session.add(package)
        await db_session.commit()

        # Create a tracking event with email message ID
        event = TrackingEvent(
            package_id=package.id,
            event_date=package.created_at,
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
        assert len(data["data"]) == 1
        assert data["data"][0]["tracking_number"] == "123456789"

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
        assert len(data["data"]) == 0
        assert data["pagination"]["total"] == 0
