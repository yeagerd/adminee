import pytest
from fastapi.testclient import TestClient

from services.meetings.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def set_db_url_meetings(monkeypatch):
    monkeypatch.setenv("DB_URL_MEETINGS", "sqlite:///:memory:")


@pytest.fixture(autouse=True)
def reset_settings_cache():
    import services.meetings.settings

    services.meetings.settings._settings = None


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
