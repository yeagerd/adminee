"""
Test configuration and fixtures for Office Service tests.

This module provides reusable fixtures and configurations for testing
the Office Service with proper mocking of external dependencies.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import fakeredis.aioredis
import pytest

# Add the parent directory to sys.path to enable relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from core.token_manager import TokenData
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def mock_redis():
    """Replace Redis with fakeredis for all tests."""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with patch("core.cache_manager.redis.from_url", return_value=fake_redis):
        yield fake_redis


@pytest.fixture(autouse=True)
def mock_database():
    """Mock database operations for all tests."""

    async def mock_check_database():
        return True

    async def mock_check_redis():
        return True

    async def mock_check_service(url):
        return True

    # Mock the database execute method that's actually called
    async def mock_database_execute(query):
        return None

    with (
        patch("api.health.check_database_connection", side_effect=mock_check_database),
        patch("api.health.check_redis_connection", side_effect=mock_check_redis),
        patch("api.health.check_service_connection", side_effect=mock_check_service),
        patch("models.database.execute", side_effect=mock_database_execute),
        patch("models.database.is_connected", True),
    ):
        yield


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def google_token():
    """Create a mock Google token."""
    return TokenData(
        access_token="mock-google-token-12345",
        refresh_token="mock-google-refresh-token",
        expires_at=datetime.now(timezone.utc),
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
        provider="google",
        user_id="test-user-123",
    )


@pytest.fixture
def microsoft_token():
    """Create a mock Microsoft token."""
    return TokenData(
        access_token="mock-microsoft-token-67890",
        refresh_token="mock-microsoft-refresh-token",
        expires_at=datetime.now(timezone.utc),
        scopes=[
            "https://graph.microsoft.com/Mail.Read",
            "https://graph.microsoft.com/Mail.Send",
            "https://graph.microsoft.com/Calendars.ReadWrite",
            "https://graph.microsoft.com/Files.Read",
        ],
        provider="microsoft",
        user_id="test-user-123",
    )


@pytest.fixture
def mock_google_email_response():
    """Mock Google Gmail API response."""
    return {
        "messages": [
            {
                "id": "google-msg-1",
                "threadId": "google-thread-1",
                "labelIds": ["INBOX", "UNREAD"],
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Test Email from Gmail"},
                        {"name": "From", "value": "sender@gmail.com"},
                        {"name": "To", "value": "recipient@example.com"},
                        {"name": "Date", "value": "Thu, 01 Jan 2024 12:00:00 +0000"},
                    ],
                    "body": {
                        "data": "VGVzdCBlbWFpbCBib2R5IGZyb20gR21haWw="
                    },  # Base64: "Test email body from Gmail"
                    "parts": [],
                },
                "snippet": "Test email body from Gmail",
            },
            {
                "id": "google-msg-2",
                "threadId": "google-thread-2",
                "labelIds": ["INBOX"],
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Another Gmail Email"},
                        {"name": "From", "value": "another@gmail.com"},
                        {"name": "To", "value": "recipient@example.com"},
                        {"name": "Date", "value": "Fri, 02 Jan 2024 14:30:00 +0000"},
                    ],
                    "body": {
                        "data": "QW5vdGhlciB0ZXN0IGVtYWls"
                    },  # Base64: "Another test email"
                    "parts": [],
                },
                "snippet": "Another test email",
            },
        ]
    }


@pytest.fixture
def mock_microsoft_email_response():
    """Mock Microsoft Graph API email response."""
    return {
        "value": [
            {
                "id": "microsoft-msg-1",
                "conversationId": "microsoft-conv-1",
                "subject": "Test Email from Outlook",
                "bodyPreview": "Test email body from Outlook",
                "receivedDateTime": "2024-01-01T12:00:00Z",
                "from": {
                    "emailAddress": {
                        "address": "sender@outlook.com",
                        "name": "Sender Name",
                    }
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": "recipient@example.com",
                            "name": "Recipient Name",
                        }
                    }
                ],
                "body": {
                    "content": "Test email body from Outlook",
                    "contentType": "text",
                },
                "isRead": False,
                "hasAttachments": False,
                "categories": ["Important"],
            },
            {
                "id": "microsoft-msg-2",
                "conversationId": "microsoft-conv-2",
                "subject": "Another Outlook Email",
                "bodyPreview": "Another test email from Outlook",
                "receivedDateTime": "2024-01-02T14:30:00Z",
                "from": {
                    "emailAddress": {
                        "address": "another@outlook.com",
                        "name": "Another Sender",
                    }
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": "recipient@example.com",
                            "name": "Recipient Name",
                        }
                    }
                ],
                "body": {
                    "content": "Another test email from Outlook",
                    "contentType": "text",
                },
                "isRead": True,
                "hasAttachments": True,
                "categories": [],
            },
        ]
    }


@pytest.fixture
def mock_google_calendar_response():
    """Mock Google Calendar API response."""
    return {
        "items": [
            {
                "id": "google-event-1",
                "summary": "Team Meeting",
                "description": "Weekly team sync",
                "start": {"dateTime": "2024-01-01T10:00:00Z"},
                "end": {"dateTime": "2024-01-01T11:00:00Z"},
                "creator": {"email": "organizer@company.com"},
                "organizer": {"email": "organizer@company.com"},
                "attendees": [
                    {"email": "attendee1@company.com", "responseStatus": "accepted"},
                    {"email": "attendee2@company.com", "responseStatus": "tentative"},
                ],
            }
        ]
    }


@pytest.fixture
def mock_microsoft_calendar_response():
    """Mock Microsoft Graph Calendar API response."""
    return {
        "value": [
            {
                "id": "microsoft-event-1",
                "subject": "Project Review",
                "body": {"content": "Monthly project review meeting"},
                "start": {"dateTime": "2024-01-01T14:00:00Z", "timeZone": "UTC"},
                "end": {"dateTime": "2024-01-01T15:00:00Z", "timeZone": "UTC"},
                "organizer": {
                    "emailAddress": {
                        "address": "manager@company.com",
                        "name": "Manager",
                    }
                },
                "attendees": [
                    {
                        "emailAddress": {
                            "address": "team1@company.com",
                            "name": "Team Member 1",
                        },
                        "status": {"response": "accepted"},
                    }
                ],
            }
        ]
    }


@pytest.fixture
def mock_google_drive_response():
    """Mock Google Drive API response."""
    return {
        "files": [
            {
                "id": "google-file-1",
                "name": "Important Document.pdf",
                "mimeType": "application/pdf",
                "size": "1048576",
                "createdTime": "2024-01-01T10:00:00Z",
                "modifiedTime": "2024-01-01T12:00:00Z",
                "webViewLink": "https://drive.google.com/file/d/google-file-1/view",
                "owners": [{"emailAddress": "owner@company.com"}],
            }
        ]
    }


@pytest.fixture
def mock_microsoft_drive_response():
    """Mock Microsoft OneDrive API response."""
    return {
        "value": [
            {
                "id": "microsoft-file-1",
                "name": "Quarterly Report.xlsx",
                "file": {
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                },
                "size": 2097152,
                "createdDateTime": "2024-01-01T14:00:00Z",
                "lastModifiedDateTime": "2024-01-01T16:00:00Z",
                "webUrl": "https://company-my.sharepoint.com/personal/user_company_com/_layouts/15/onedrive.aspx?id=/personal/user_company_com/Documents/Quarterly%20Report.xlsx",
                "createdBy": {"user": {"email": "creator@company.com"}},
            }
        ]
    }


@pytest.fixture
def mock_successful_tokens(google_token, microsoft_token):
    """Mock successful token retrieval for both providers."""

    def token_side_effect(user_id, provider, scopes=None):
        if provider == "google":
            return google_token
        elif provider == "microsoft":
            return microsoft_token
        else:
            raise ValueError(f"Unknown provider: {provider}")

    return token_side_effect


@pytest.fixture
def mock_http_responses(
    mock_google_email_response,
    mock_microsoft_email_response,
    mock_google_calendar_response,
    mock_microsoft_calendar_response,
    mock_google_drive_response,
    mock_microsoft_drive_response,
):
    """Mock HTTP responses for different API endpoints."""

    def create_response(response_data, status_code=200):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = (
            response_data  # Use return_value instead of lambda
        )
        mock_response.raise_for_status = lambda: None
        return mock_response

    # Map URL patterns to responses
    response_map = {
        "gmail.googleapis.com": create_response(mock_google_email_response),
        "www.googleapis.com/calendar": create_response(mock_google_calendar_response),
        "www.googleapis.com/drive": create_response(mock_google_drive_response),
        "graph.microsoft.com/v1.0/me/messages": create_response(
            mock_microsoft_email_response
        ),
        "graph.microsoft.com/v1.0/me/events": create_response(
            mock_microsoft_calendar_response
        ),
        "graph.microsoft.com/v1.0/me/drive": create_response(
            mock_microsoft_drive_response
        ),
    }

    def http_side_effect(*args, **kwargs):
        url = (
            kwargs.get("url", "")
            if "url" in kwargs
            else str(args[1]) if len(args) > 1 else ""
        )

        # Handle token requests to user management service
        if "tokens/get" in url:
            json_data = kwargs.get("json", {})
            provider = json_data.get("provider", "google")
            user_id = json_data.get("user_id", "test-user@example.com")

            if provider == "google":
                return create_response(
                    {
                        "access_token": "mock-google-token-12345",
                        "refresh_token": "mock-google-refresh-token",
                        "expires_at": "2024-12-31T23:59:59Z",
                        "scopes": [
                            "https://www.googleapis.com/auth/gmail.readonly",
                            "https://www.googleapis.com/auth/gmail.send",
                            "https://www.googleapis.com/auth/calendar",
                            "https://www.googleapis.com/auth/drive.readonly",
                        ],
                        "provider": "google",
                        "user_id": user_id,
                    }
                )
            elif provider == "microsoft":
                return create_response(
                    {
                        "access_token": "mock-microsoft-token-67890",
                        "refresh_token": "mock-microsoft-refresh-token",
                        "expires_at": "2024-12-31T23:59:59Z",
                        "scopes": [
                            "https://graph.microsoft.com/Mail.Read",
                            "https://graph.microsoft.com/Mail.Send",
                            "https://graph.microsoft.com/Calendars.ReadWrite",
                            "https://graph.microsoft.com/Files.Read",
                        ],
                        "provider": "microsoft",
                        "user_id": user_id,
                    }
                )

        # Handle individual message requests specifically
        if "/messages/msg-1" in url and "gmail" in url:
            return create_response(mock_google_email_response["messages"][0])

        for pattern, response in response_map.items():
            if pattern in url:
                return response

        # Default response
        return create_response({"default": "response"})

    return http_side_effect


@pytest.fixture
def test_user_id():
    """Standard test user ID."""
    return "test-user@example.com"


@pytest.fixture
def integration_test_setup(
    mock_successful_tokens,
    mock_http_responses,
    test_user_id,
    mock_google_email_response,
    mock_microsoft_email_response,
    mock_google_calendar_response,
    mock_microsoft_calendar_response,
    mock_google_drive_response,
    mock_microsoft_drive_response,
):
    """Complete setup for integration tests with all necessary mocks."""

    # Mock API client methods
    async def mock_google_get_messages(**kwargs):
        return mock_google_email_response

    async def mock_microsoft_get_messages(**kwargs):
        return mock_microsoft_email_response

    async def mock_google_get_message(message_id, **kwargs):
        # Return first message from mock data
        return mock_google_email_response["messages"][0]

    async def mock_microsoft_get_message(message_id, **kwargs):
        # Return first message from mock data
        return mock_microsoft_email_response["value"][0]

    async def mock_google_get_events(**kwargs):
        return mock_google_calendar_response

    async def mock_microsoft_get_events(**kwargs):
        return mock_microsoft_calendar_response

    async def mock_google_get_files(**kwargs):
        return mock_google_drive_response

    async def mock_microsoft_get_drive_items(**kwargs):
        return mock_microsoft_drive_response

    # Create an async version of the token mock
    async def async_mock_successful_tokens(user_id, provider, scopes=None):
        return mock_successful_tokens(user_id, provider, scopes)

    with (
        patch(
            "core.token_manager.TokenManager.get_user_token",
            side_effect=async_mock_successful_tokens,
        ),
        patch("core.cache_manager.cache_manager.get_from_cache", return_value=None),
        patch("core.cache_manager.cache_manager.set_to_cache", return_value=True),
        patch("httpx.AsyncClient.request", side_effect=mock_http_responses),
        patch("httpx.AsyncClient.__aenter__", return_value=MagicMock()),
        patch("httpx.AsyncClient.__aexit__", return_value=None),
        patch(
            "core.clients.google.GoogleAPIClient.get_messages",
            side_effect=mock_google_get_messages,
        ),
        patch(
            "core.clients.microsoft.MicrosoftAPIClient.get_messages",
            side_effect=mock_microsoft_get_messages,
        ),
        patch(
            "core.clients.google.GoogleAPIClient.get_message",
            side_effect=mock_google_get_message,
        ),
        patch(
            "core.clients.microsoft.MicrosoftAPIClient.get_message",
            side_effect=mock_microsoft_get_message,
        ),
        patch(
            "core.clients.google.GoogleAPIClient.get_events",
            side_effect=mock_google_get_events,
        ),
        patch(
            "core.clients.microsoft.MicrosoftAPIClient.get_events",
            side_effect=mock_microsoft_get_events,
        ),
        patch(
            "core.clients.google.GoogleAPIClient.get_files",
            side_effect=mock_google_get_files,
        ),
        patch(
            "core.clients.microsoft.MicrosoftAPIClient.get_drive_items",
            side_effect=mock_microsoft_get_drive_items,
        ),
    ):
        yield {
            "user_id": test_user_id,
            "tokens": mock_successful_tokens,
            "http_responses": mock_http_responses,
        }
