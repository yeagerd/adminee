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
        response = client.get("/api/v1/carriers/")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test with invalid API key
        response = client.get(
            "/api/v1/carriers/", headers={"Authorization": "Bearer invalid-key"}
        )
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["message"]

    def test_labels_endpoints_require_auth(self, client):
        """Test that labels endpoints require authentication."""
        # Test list labels without API key
        response = client.get("/api/v1/labels/")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test create label without API key
        response = client.post("/api/v1/labels/", json={})
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test update label without API key
        response = client.put("/api/v1/labels/1", json={})
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test delete label without API key
        response = client.delete("/api/v1/labels/1")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

    def test_tracking_events_endpoint_requires_auth(self, client):
        """Test that tracking events endpoint requires authentication."""
        # Test without API key
        response = client.get("/api/v1/tracking/packages/1/events")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

    def test_packages_endpoints_require_auth(self, client):
        """Test that packages endpoints require authentication."""
        # Test list packages without API key
        response = client.get("/api/v1/packages/")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test create package without API key
        response = client.post("/api/v1/packages/", json={})
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test get package without API key
        response = client.get("/api/v1/packages/1")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test update package without API key
        response = client.put("/api/v1/packages/1", json={})
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test delete package without API key
        response = client.delete("/api/v1/packages/1")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test refresh package without API key
        response = client.post("/api/v1/packages/1/refresh")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test add label to package without API key
        response = client.post("/api/v1/packages/1/labels")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

        # Test remove label from package without API key
        response = client.delete("/api/v1/packages/1/labels/1")
        assert response.status_code == 401
        assert "API key required" in response.json()["message"]

    def test_valid_api_key_works(self, client):
        """Test that valid API key allows access."""
        # Test with valid API key
        response = client.get(
            "/api/v1/carriers/", headers={"Authorization": "Bearer test-api-key"}
        )
        # Should not return 401 (authentication error)
        assert response.status_code != 401
