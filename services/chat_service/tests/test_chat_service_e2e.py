import os
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
    initial_threads = resp.json()
    initial_count = len(initial_threads)

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
    resp = client.post("/chat", json={"user_id": user_id, "thread_id": thread_id, "message": msg2})
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
    resp = client.post("/feedback", json={
        "user_id": user_id,
        "thread_id": thread_id,
        "message_id": last_msg["message_id"],
        "feedback": "up"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
