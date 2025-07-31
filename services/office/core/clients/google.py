from typing import Any, Dict, Optional, List

from services.office.core.clients.base import BaseAPIClient
from services.office.models import Provider


class GoogleAPIClient(BaseAPIClient):
    """
    Google API client for accessing Gmail, Google Calendar, and Google Drive APIs.

    This client handles authentication and provides methods for interacting with
    Google's APIs using OAuth2 access tokens.
    """

    def __init__(self, access_token: str, user_id: str):
        """
        Initialize Google API client.

        Args:
            access_token: OAuth2 access token for Google APIs
            user_id: User ID for tracking and logging
        """
        super().__init__(access_token, user_id, Provider.GOOGLE)

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Google API requests"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "BrieflyOfficeService/1.0",
        }

    def _get_base_url(self) -> str:
        """Get base URL for Google APIs"""
        return "https://www.googleapis.com"

    # Gmail API methods
    async def get_messages(
        self,
        max_results: int = 100,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get list of Gmail messages.

        Args:
            max_results: Maximum number of messages to return
            page_token: Token for pagination
            query: Gmail search query

        Returns:
            Dictionary containing messages list and pagination info
        """
        params: Dict[str, Any] = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        if query:
            params["q"] = query

        response = await self.get("/gmail/v1/users/me/messages", params=params)
        return response.json()

    async def get_message(
        self, message_id: str, format: str = "full"
    ) -> Dict[str, Any]:
        """
        Get a specific Gmail message.

        Args:
            message_id: Gmail message ID
            format: Message format (minimal, full, raw, metadata)

        Returns:
            Dictionary containing message details
        """
        params = {"format": format}
        response = await self.get(
            f"/gmail/v1/users/me/messages/{message_id}", params=params
        )
        return response.json()

    async def send_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a Gmail message.

        Args:
            message_data: Message data in Gmail API format

        Returns:
            Dictionary containing sent message details
        """
        response = await self.post(
            "/gmail/v1/users/me/messages/send", json_data=message_data
        )
        return response.json()

    async def get_labels(self) -> Dict[str, Any]:
        """
        Get list of Gmail labels.

        Returns:
            Dictionary containing labels list
        """
        response = await self.get("/gmail/v1/users/me/labels")
        return response.json()

    async def get_messages_from_label(
        self,
        label_id: str,
        max_results: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get list of Gmail messages from a specific label.

        Args:
            label_id: Gmail label ID
            max_results: Maximum number of messages to return
            page_token: Token for pagination

        Returns:
            Dictionary containing messages list and pagination info
        """
        params: Dict[str, Any] = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token

        # Use the label query parameter to filter messages by label
        params["q"] = f"label:{label_id}"

        response = await self.get("/gmail/v1/users/me/messages", params=params)
        return response.json()

    # Google Calendar API methods
    async def get_calendar_list(self) -> Dict[str, Any]:
        """
        Get list of user's calendars.

        Returns:
            Dictionary containing calendar list
        """
        response = await self.get("/calendar/v3/users/me/calendarList")
        return response.json()

    async def get_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 250,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get calendar events.

        Args:
            calendar_id: Calendar ID (default: primary)
            time_min: RFC3339 timestamp for earliest event time
            time_max: RFC3339 timestamp for latest event time
            max_results: Maximum number of events to return
            page_token: Token for pagination

        Returns:
            Dictionary containing events list and pagination info
        """
        params: Dict[str, Any] = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if page_token:
            params["pageToken"] = page_token

        response = await self.get(
            f"/calendar/v3/calendars/{calendar_id}/events", params=params
        )
        return response.json()

    async def create_event(
        self, calendar_id: str, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a calendar event.

        Args:
            calendar_id: Calendar ID to create event in
            event_data: Event data in Google Calendar API format

        Returns:
            Dictionary containing created event details
        """
        response = await self.post(
            f"/calendar/v3/calendars/{calendar_id}/events", json_data=event_data
        )
        return response.json()

    async def update_event(
        self, calendar_id: str, event_id: str, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a calendar event.

        Args:
            calendar_id: Calendar ID containing the event
            event_id: Event ID to update
            event_data: Updated event data in Google Calendar API format

        Returns:
            Dictionary containing updated event details
        """
        response = await self.put(
            f"/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            json_data=event_data,
        )
        return response.json()

    async def delete_event(self, calendar_id: str, event_id: str) -> None:
        """
        Delete a calendar event.

        Args:
            calendar_id: Calendar ID containing the event
            event_id: Event ID to delete
        """
        await self.delete(f"/calendar/v3/calendars/{calendar_id}/events/{event_id}")

    # Google Drive API methods
    async def get_files(
        self,
        page_size: int = 100,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get list of Drive files.

        Args:
            page_size: Number of files to return per page
            page_token: Token for pagination
            query: Search query
            fields: Fields to include in response

        Returns:
            Dictionary containing files list and pagination info
        """
        params: Dict[str, Any] = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        if query:
            params["q"] = query
        if fields:
            params["fields"] = fields
        else:
            params["fields"] = (
                "nextPageToken,files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,thumbnailLink,parents)"
            )

        response = await self.get("/drive/v3/files", params=params)
        return response.json()

    async def get_file(
        self, file_id: str, fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            file_id: Drive file ID
            fields: Fields to include in response

        Returns:
            Dictionary containing file metadata
        """
        params = {}
        if fields:
            params["fields"] = fields
        else:
            params["fields"] = (
                "id,name,mimeType,size,createdTime,modifiedTime,webViewLink,downloadUrl,thumbnailLink,parents"
            )

        response = await self.get(f"/drive/v3/files/{file_id}", params=params)
        return response.json()

    async def search_files(self, query: str, max_results: int = 100) -> Dict[str, Any]:
        """
        Search for files in Drive.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            Dictionary containing search results
        """
        return await self.get_files(
            page_size=max_results,
            query=query,
            fields="files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,thumbnailLink,parents)",
        )

    # Gmail Threading API methods
    async def get_threads(
        self,
        max_results: int = 100,
        page_token: Optional[str] = None,
        q: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get list of Gmail threads.

        Args:
            max_results: Maximum number of threads to return
            page_token: Token for pagination
            q: Gmail search query
            label_ids: List of label IDs to filter by

        Returns:
            Dictionary containing threads list and pagination info
        """
        params: Dict[str, Any] = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        if q:
            params["q"] = q
        if label_ids:
            params["labelIds"] = label_ids

        response = await self.get("/gmail/v1/users/me/threads", params=params)
        return response.json()

    async def get_thread(
        self, thread_id: str, format: str = "full"
    ) -> Dict[str, Any]:
        """
        Get a specific Gmail thread with all its messages.

        Args:
            thread_id: Gmail thread ID
            format: Message format (minimal, full, raw, metadata)

        Returns:
            Dictionary containing thread details with all messages
        """
        params = {"format": format}
        response = await self.get(
            f"/gmail/v1/users/me/threads/{thread_id}", params=params
        )
        return response.json()

    async def get_messages_with_threads(
        self,
        max_results: int = 100,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get messages with thread information.

        Args:
            max_results: Maximum number of messages to return
            page_token: Token for pagination
            query: Gmail search query
            label_ids: List of label IDs to filter by

        Returns:
            Dictionary containing messages list with thread info and pagination info
        """
        params: Dict[str, Any] = {"maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids

        # Include thread information in the response
        params["fields"] = "nextPageToken,messages(id,threadId,labelIds,internalDate,snippet,payload,sizeEstimate)"

        response = await self.get("/gmail/v1/users/me/messages", params=params)
        return response.json()
