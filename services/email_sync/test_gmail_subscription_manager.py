from services.email_sync.gmail_subscription_manager import (
    refresh_gmail_subscription,
    scheduled_refresh_job,
)


def test_refresh_gmail_subscription_logs(caplog):
    user_id = "user1@example.com"
    with caplog.at_level("INFO"):
        result = refresh_gmail_subscription(user_id)
    assert result is True
    assert f"Refreshing Gmail watch subscription for user {user_id}" in caplog.text


def test_scheduled_refresh_job_logs(monkeypatch, caplog):
    calls = []

    def fake_refresh(user_id):
        calls.append(user_id)
        return True

    monkeypatch.setattr(
        "services.email_sync.gmail_subscription_manager.refresh_gmail_subscription", fake_refresh
    )
    with caplog.at_level("INFO"):
        scheduled_refresh_job()
    assert "user1@example.com" in calls
    assert "user2@example.com" in calls
