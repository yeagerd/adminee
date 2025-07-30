import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Patch the _settings global to return test settings."""
    import services.shipments.settings as shipments_settings

    test_settings = shipments_settings.Settings(
        db_url_shipments="sqlite:///:memory:",
        api_frontend_shipments_key="test-api-key",
    )

    monkeypatch.setattr("services.shipments.settings._settings", test_settings)


@pytest.fixture
def client():
    from services.shipments.main import app

    return TestClient(app)


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
