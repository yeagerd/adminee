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

"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import argparse

import requests

from services.chat.models import ChatResponse


def print_help():
    print(__doc__)


def actor(message):
    """
    Returns a string indicating the actor of the message.
    """
    return "briefly" if message.llm_generated else message.user_id


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--chat-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL for the chat service API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--user-id", type=str, default="user", help="User ID for chat (default: user)"
    )
    args = parser.parse_args()

    chat_url = args.chat_url.rstrip("/")
    user_id = args.user_id

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
                        print(
                            f"{t['thread_id']}\t(created: {t['created_at']}, updated: {t['updated_at']})"
                        )
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
                    data = resp.json()
                    chat_resp = ChatResponse.model_validate(data)
                    messages = chat_resp.messages or []
                    print(f"Switched to thread {thread_id}.")
                    if not messages:
                        print("No messages in this thread.")
                    else:
                        for m in messages:
                            uid = actor(m)
                            content = m.content
                            print(f"{uid}: {content}")
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
                # Erase the previous input line (prompt + user input)
                print("\033[F\033[K", end="")  # Move cursor up and clear line
                print(f"{user_id}: {line}")
                resp = requests.post(f"{chat_url}/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                chat_resp = ChatResponse.model_validate(data)
                active_thread = chat_resp.thread_id
                messages = chat_resp.messages or []
                for m in messages:
                    uid = actor(m)
                    content = m.content
                    print(f"{uid}: {content}")
                if chat_resp.draft:
                    print("Draft:")
                    print(chat_resp.draft)
            except requests.RequestException as e:
                print(f"Error sending message: {e}")

    sys.exit(0)


if __name__ == "__main__":
    main()
