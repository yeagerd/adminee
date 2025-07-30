from typing import Any, Dict, Optional

from services.office.core.clients.base import BaseAPIClient
from services.office.models import Provider


class MicrosoftAPIClient(BaseAPIClient):
    """
    Microsoft Graph API client for accessing Outlook, Microsoft Calendar, and OneDrive APIs.

    This client handles authentication and provides methods for interacting with
    Microsoft Graph APIs using OAuth2 access tokens.
    """

    def __init__(self, access_token: str, user_id: str):
        """
        Initialize Microsoft Graph API client.

        Args:
            access_token: OAuth2 access token for Microsoft Graph APIs
            user_id: User ID for tracking and logging
        """
        super().__init__(access_token, user_id, Provider.MICROSOFT)

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Microsoft Graph API requests"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "BrieflyOfficeService/1.0",
        }

    def _get_base_url(self) -> str:
        """Get base URL for Microsoft Graph API"""
        return "https://graph.microsoft.com/v1.0"

    # Outlook Mail API methods
    async def get_messages(
        self,
        top: int = 100,
        skip: int = 0,
        filter: Optional[str] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get list of Outlook messages.

        Args:
            top: Maximum number of messages to return
            skip: Number of messages to skip (for pagination)
            filter: OData filter expression
            search: Search query
            order_by: Order by expression

        Returns:
            Dictionary containing messages list and pagination info
        """
        params: Dict[str, Any] = {"$top": top, "$skip": skip}
        if filter:
            params["$filter"] = filter
        if search:
            params["$search"] = search
        if order_by:
            params["$orderby"] = order_by
        else:
            params["$orderby"] = "receivedDateTime desc"

        response = await self.get("/me/messages", params=params)
        return response.json()

    async def get_messages_from_folder(
        self,
        folder_id: str,
        top: int = 100,
        skip: int = 0,
        filter: Optional[str] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get list of Outlook messages from a specific folder.

        Args:
            folder_id: ID of the folder to fetch messages from
            top: Maximum number of messages to return
            skip: Number of messages to skip (for pagination)
            filter: OData filter expression
            search: Search query
            order_by: Order by expression

        Returns:
            Dictionary containing messages list and pagination info
        """
        params: Dict[str, Any] = {"$top": top, "$skip": skip}
        if filter:
            params["$filter"] = filter
        if search:
            params["$search"] = search
        if order_by:
            params["$orderby"] = order_by
        else:
            params["$orderby"] = "receivedDateTime desc"

        response = await self.get(
            f"/me/mailFolders/{folder_id}/messages", params=params
        )
        return response.json()

    async def get_message(
        self, message_id: str, select: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a specific Outlook message.

        Args:
            message_id: Outlook message ID
            select: Comma-separated list of properties to select

        Returns:
            Dictionary containing message details
        """
        params = {}
        if select:
            params["$select"] = select

        response = await self.get(f"/me/messages/{message_id}", params=params)
        return response.json()

    async def send_message(self, message_data: Dict[str, Any]) -> None:
        """
        Send an Outlook message.

        Args:
            message_data: Message data in Microsoft Graph API format
        """
        await self.post("/me/sendMail", json_data=message_data)

    async def get_mailboxes(self) -> Dict[str, Any]:
        """
        Get list of user's mailboxes/mail folders.

        Returns:
            Dictionary containing mailbox list
        """
        response = await self.get("/me/mailFolders")
        return response.json()

    # Microsoft Calendar API methods
    async def get_calendars(self) -> Dict[str, Any]:
        """
        Get list of user's calendars.

        Returns:
            Dictionary containing calendar list
        """
        response = await self.get("/me/calendars")
        return response.json()

    async def get_events(
        self,
        calendar_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        top: int = 250,
        skip: int = 0,
        order_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get calendar events including recurring event instances.

        Uses the calendarView endpoint when date filtering is needed to properly
        expand recurring events into individual instances.

        Args:
            calendar_id: Calendar ID (if None, uses primary calendar)
            start_time: ISO 8601 timestamp for earliest event time
            end_time: ISO 8601 timestamp for latest event time
            top: Maximum number of events to return
            skip: Number of events to skip (for pagination)
            order_by: Order by expression

        Returns:
            Dictionary containing events list and pagination info
        """
        # Use calendarView endpoint when filtering by date range to expand recurring events
        if start_time and end_time:
            # CalendarView endpoint automatically expands recurring events
            endpoint = (
                f"/me/calendars/{calendar_id}/calendarView"
                if calendar_id
                else "/me/calendarView"
            )

            params: Dict[str, Any] = {
                "$top": top,
                "startDateTime": start_time,
                "endDateTime": end_time,
            }
            if order_by:
                params["$orderby"] = order_by
            else:
                params["$orderby"] = "start/dateTime"

        else:
            # Use regular events endpoint when no date filtering
            endpoint = (
                f"/me/calendars/{calendar_id}/events" if calendar_id else "/me/events"
            )

            params = {"$top": top, "$skip": skip}
            if order_by:
                params["$orderby"] = order_by
            else:
                params["$orderby"] = "start/dateTime"

            # Add time range filter if only one date specified
            if start_time:
                params["$filter"] = f"start/dateTime ge '{start_time}'"
            elif end_time:
                params["$filter"] = f"end/dateTime le '{end_time}'"

        response = await self.get(endpoint, params=params)
        return response.json()

    async def create_event(
        self, event_data: Dict[str, Any], calendar_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a calendar event.

        Args:
            event_data: Event data in Microsoft Graph API format
            calendar_id: Calendar ID (if None, uses primary calendar)

        Returns:
            Dictionary containing created event details
        """
        endpoint = (
            f"/me/calendars/{calendar_id}/events" if calendar_id else "/me/events"
        )
        response = await self.post(endpoint, json_data=event_data)
        return response.json()

    async def update_event(
        self,
        event_id: str,
        event_data: Dict[str, Any],
        calendar_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a calendar event.

        Args:
            event_id: Event ID to update
            event_data: Updated event data in Microsoft Graph API format
            calendar_id: Calendar ID (if None, uses primary calendar)

        Returns:
            Dictionary containing updated event details
        """
        endpoint = (
            f"/me/calendars/{calendar_id}/events/{event_id}"
            if calendar_id
            else f"/me/events/{event_id}"
        )
        response = await self.patch(endpoint, json_data=event_data)
        return response.json()

    async def delete_event(
        self, event_id: str, calendar_id: Optional[str] = None
    ) -> None:
        """
        Delete a calendar event.

        Args:
            event_id: Event ID to delete
            calendar_id: Calendar ID (if None, uses primary calendar)
        """
        endpoint = (
            f"/me/calendars/{calendar_id}/events/{event_id}"
            if calendar_id
            else f"/me/events/{event_id}"
        )
        await self.delete(endpoint)

    # OneDrive API methods
    async def get_drive_items(
        self,
        top: int = 100,
        filter: Optional[str] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        skip_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get list of OneDrive items.

        Args:
            top: Number of items to return per page
            filter: OData filter expression
            search: Search query
            order_by: Order by expression
            skip_token: Token for cursor-based pagination (from @odata.nextLink)

        Returns:
            Dictionary containing items list and pagination info
        """
        # If search is provided, use the search endpoint instead
        if search:
            return await self.search_drive_items(search, top=top)

        params: Dict[str, Any] = {"$top": top}
        if filter:
            params["$filter"] = filter
        if order_by:
            params["$orderby"] = order_by
        else:
            params["$orderby"] = "lastModifiedDateTime desc"
        if skip_token:
            params["$skiptoken"] = skip_token

        response = await self.get("/me/drive/root/children", params=params)
        return response.json()

    async def get_drive_item(
        self, item_id: str, select: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get OneDrive item metadata.

        Args:
            item_id: OneDrive item ID
            select: Comma-separated list of properties to select

        Returns:
            Dictionary containing item metadata
        """
        params = {}
        if select:
            params["$select"] = select

        response = await self.get(f"/me/drive/items/{item_id}", params=params)
        return response.json()

    async def search_drive_items(self, query: str, top: int = 100) -> Dict[str, Any]:
        """
        Search for items in OneDrive.

        Args:
            query: Search query
            top: Maximum number of results

        Returns:
            Dictionary containing search results
        """
        params = {"$top": top}
        response = await self.get(f"/me/drive/root/search(q='{query}')", params=params)
        return response.json()

    async def get_recent_files(self, top: int = 100) -> Dict[str, Any]:
        """
        Get recently accessed files.

        Args:
            top: Maximum number of files to return

        Returns:
            Dictionary containing recent files
        """
        params = {"$top": top}
        response = await self.get("/me/drive/recent", params=params)
        return response.json()

    # User profile methods
    async def get_user_profile(self) -> Dict[str, Any]:
        """
        Get user profile information.

        Returns:
            Dictionary containing user profile data
        """
        response = await self.get("/me")
        return response.json()
