#!/usr/bin/env python3
"""
Interactive chat demo using the chat_service API.

Commands:
  help                Show this help message.
  list                List all threads for the user.
  new                 Start a new thread.
  switch <thread_id>  Switch to an existing thread.
  exit                Exit the chat.

Type any other text to send as a message to the active thread (or create a new thread if none active).

Environment variables:
  CHAT_SERVICE_URL    Base URL for the chat service API (default: http://localhost:8000)
  CHAT_USER_ID        User ID for chat (can be set here or entered at runtime).
"""

import os
import sys
import requests

def print_help():
    print(__doc__)

def main():
    # Load configuration
    chat_url = os.getenv("CHAT_SERVICE_URL", "http://localhost:8000").rstrip("/")
    user_id = os.getenv("CHAT_USER_ID")
    if not user_id:
        user_id = input("Enter user_id: ").strip()
        if not user_id:
            print("User ID is required.")
            sys.exit(1)

    active_thread = None
    print_help()

    while True:
        prompt = f"[{active_thread if active_thread else 'new'}]> "
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()

        if cmd == "help":
            print_help()
        elif cmd == "list":
            try:
                resp = requests.get(f"{chat_url}/threads", params={"user_id": user_id})
                resp.raise_for_status()
                threads = resp.json()
                if not threads:
                    print("No threads found.")
                else:
                    for t in threads:
                        print(f"{t['thread_id']}\t(created: {t['created_at']}, updated: {t['updated_at']})")
            except requests.RequestException as e:
                print(f"Error listing threads: {e}")
        elif cmd == "new":
            active_thread = None
            print("New thread started. Next message will create it.")
        elif cmd == "switch":
            if len(parts) < 2:
                print("Usage: switch <thread_id>")
            else:
                thread_id = parts[1]
                try:
                    resp = requests.get(f"{chat_url}/threads/{thread_id}/history")
                    resp.raise_for_status()
                    active_thread = thread_id
                    print(f"Switched to thread {thread_id}.")
                except requests.RequestException as e:
                    print(f"Error switching thread: {e}")
        elif cmd == "exit":
            print("Exiting.")
            break
        else:
            # Send message to chat
            payload = {"user_id": user_id, "message": line}
            if active_thread:
                payload["thread_id"] = active_thread

            try:
                resp = requests.post(f"{chat_url}/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                active_thread = data.get("thread_id")
                print(f"Thread: {active_thread}")
                messages = data.get("messages", [])
                for m in messages:
                    uid = m.get("user_id", "")
                    content = m.get("content", "")
                    print(f"{uid}: {content}")
                draft = data.get("draft")
                if draft:
                    print("Draft:")
                    print(draft)
            except requests.RequestException as e:
                print(f"Error sending message: {e}")

    sys.exit(0)

if __name__ == "__main__":
    main()
