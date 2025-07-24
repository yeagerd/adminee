import pytest
from microsoft_subscription_manager import refresh_microsoft_subscription, scheduled_refresh_job

def test_refresh_microsoft_subscription_logs(caplog):
    user_id = "user1@example.com"
    with caplog.at_level("INFO"):
        result = refresh_microsoft_subscription(user_id)
    assert result is True
    assert f"Refreshing Microsoft Graph subscription for user {user_id}" in caplog.text

def test_scheduled_refresh_job_logs(monkeypatch, caplog):
    calls = []
    def fake_refresh(user_id):
        calls.append(user_id)
        return True
    monkeypatch.setattr("microsoft_subscription_manager.refresh_microsoft_subscription", fake_refresh)
    with caplog.at_level("INFO"):
        scheduled_refresh_job()
    assert "user1@example.com" in calls
    assert "user2@example.com" in calls 