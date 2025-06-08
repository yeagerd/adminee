import os

# Set shared in-memory SQLite DB before any app/model import
os.environ["DATABASE_URL"] = "sqlite:///file::memory:?cache=shared"


import pytest
from fastapi.testclient import TestClient

from services.chat_service.main import app


@pytest.fixture(autouse=True)
def fake_llm_env(monkeypatch):
    # Simulate no OpenAI API key for tests
    monkeypatch.setenv("OPENAI_API_KEY", "")
    yield


def test_end_to_end_chat_flow():
    client = TestClient(app)
    user_id = "testuser"

    # List threads (record initial count)
    resp = client.get("/threads", params={"user_id": user_id})
    assert resp.status_code == 200

    # Start a chat (should create a new thread and echo response)
    msg = "Hello, world!"
    resp = client.post("/chat", json={"user_id": user_id, "message": msg})
    assert resp.status_code == 200
    data = resp.json()
    assert "thread_id" in data
    assert data["messages"][-1]["content"].startswith("ack:")

    thread_id = data["thread_id"]

    # Send another message in the same thread
    msg2 = "How are you?"
    resp = client.post(
        "/chat", json={"user_id": user_id, "thread_id": thread_id, "message": msg2}
    )
    assert resp.status_code == 200
    data2 = resp.json()
    assert data2["thread_id"] == thread_id
    assert data2["messages"][-1]["content"].startswith("ack:")

    # List threads (should contain the thread we just used)
    resp = client.get("/threads", params={"user_id": user_id})
    assert resp.status_code == 200
    threads = resp.json()
    assert any(t["thread_id"] == thread_id for t in threads)

    # Get thread history
    resp = client.get(f"/threads/{thread_id}/history")
    assert resp.status_code == 200
    history = resp.json()
    assert history["thread_id"] == thread_id
    assert len(history["messages"]) >= 2

    # Feedback endpoint
    last_msg = history["messages"][-1]
    resp = client.post(
        "/feedback",
        json={
            "user_id": user_id,
            "thread_id": thread_id,
            "message_id": last_msg["message_id"],
            "feedback": "up",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_multiple_blank_thread_creates_distinct_threads():
    client = TestClient(app)
    user_id = "testuser_multi"

    # Send first message with blank thread_id
    resp1 = client.post("/chat", json={"user_id": user_id, "message": "First message"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    thread_id1 = data1["thread_id"]

    # Send second message with blank thread_id
    resp2 = client.post("/chat", json={"user_id": user_id, "message": "Second message"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    thread_id2 = data2["thread_id"]

    # The thread IDs should be different
    assert thread_id1 != thread_id2

    # List threads and verify both thread IDs are present
    resp = client.get("/threads", params={"user_id": user_id})
    assert resp.status_code == 200
    threads = resp.json()
    thread_ids = {t["thread_id"] for t in threads}
    assert thread_id1 in thread_ids
    assert thread_id2 in thread_ids
