from fastapi.testclient import TestClient

from services.meetings.main import app
from services.meetings.tests.meetings_test_base import BaseMeetingsTest

client = TestClient(app)


class TestHealth(BaseMeetingsTest):
    """Test health endpoint."""

    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
