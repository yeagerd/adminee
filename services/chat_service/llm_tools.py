from typing import Any, Dict, Optional

import requests


class CalendarTool:
    """
    Retrieve calendar events from office-service via REST API.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self, office_service_url: str):
        self.office_service_url = office_service_url

    def __call__(
        self,
        user_token: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_timezone: Optional[str] = None,
        provider_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {user_token}"}
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if user_timezone:
            params["user_timezone"] = user_timezone
        if provider_type:
            params["provider_type"] = provider_type
        try:
            response = requests.get(
                f"{self.office_service_url}/events",
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if "events" not in data:
                return {"error": "Malformed response from office-service."}
            return {"events": data["events"]}
        except requests.Timeout:
            return {"error": "Request to office-service timed out."}
        except requests.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


class EmailTool:
    """
    Retrieve emails from office-service via REST API.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self, office_service_url: str):
        self.office_service_url = office_service_url

    def __call__(
        self,
        user_token: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        unread_only: Optional[bool] = None,
        folder: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve emails from office-service.
        
        Args:
            user_token: User authentication token
            start_date: Start date for email retrieval (ISO format)
            end_date: End date for email retrieval (ISO format)
            unread_only: Filter for unread emails only
            folder: Email folder to search in (e.g., 'inbox', 'sent')
            max_results: Maximum number of emails to return
        
        Returns:
            Dict containing emails or error information
        """
        headers = {"Authorization": f"Bearer {user_token}"}
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if unread_only is not None:
            params["unread_only"] = str(unread_only).lower()
        if folder:
            params["folder"] = folder
        if max_results:
            params["max_results"] = max_results
            
        try:
            response = requests.get(
                f"{self.office_service_url}/emails",
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if "emails" not in data:
                return {"error": "Malformed response from office-service."}
            return {"emails": data["emails"]}
        except requests.Timeout:
            return {"error": "Request to office-service timed out."}
        except requests.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


class NotesTool:
    """
    Retrieve notes from office-service via REST API.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self, office_service_url: str):
        self.office_service_url = office_service_url

    def __call__(
        self,
        user_token: str,
        notebook: Optional[str] = None,
        tags: Optional[str] = None,
        search_query: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve notes from office-service.
        
        Args:
            user_token: User authentication token
            notebook: Filter by specific notebook name
            tags: Filter by tags (comma-separated)
            search_query: Search within note content
            max_results: Maximum number of notes to return
        
        Returns:
            Dict containing notes or error information
        """
        headers = {"Authorization": f"Bearer {user_token}"}
        params = {}
        if notebook:
            params["notebook"] = notebook
        if tags:
            params["tags"] = tags
        if search_query:
            params["search_query"] = search_query
        if max_results:
            params["max_results"] = max_results
            
        try:
            response = requests.get(
                f"{self.office_service_url}/notes",
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if "notes" not in data:
                return {"error": "Malformed response from office-service."}
            return {"notes": data["notes"]}
        except requests.Timeout:
            return {"error": "Request to office-service timed out."}
        except requests.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

class DocumentsTool:
    """
    Retrieve documents from office-service via REST API.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self, office_service_url: str):
        self.office_service_url = office_service_url

    def __call__(
        self,
        user_token: str,
        document_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search_query: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve documents from office-service.
        
        Args:
            user_token: User authentication token
            document_type: Filter by document type (e.g., 'word', 'excel', 'powerpoint', 'pdf')
            start_date: Start date for document retrieval (ISO format)
            end_date: End date for document retrieval (ISO format)
            search_query: Search within document content/title
            max_results: Maximum number of documents to return
        
        Returns:
            Dict containing documents or error information
        """
        headers = {"Authorization": f"Bearer {user_token}"}
        params = {}
        if document_type:
            params["document_type"] = document_type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if search_query:
            params["search_query"] = search_query
        if max_results:
            params["max_results"] = max_results
            
        try:
            response = requests.get(
                f"{self.office_service_url}/documents",
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if "documents" not in data:
                return {"error": "Malformed response from office-service."}
            return {"documents": data["documents"]}
        except requests.Timeout:
            return {"error": "Request to office-service timed out."}
        except requests.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

# Draft storage - in a real implementation, this would be in a database
_draft_storage: Dict[str, Dict[str, Any]] = {}


class CreateDraftEmailTool:
    """
    Create or update the active draft email for a thread.
    This tool manages drafts locally without calling office-service.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self):
        pass

    def __call__(
        self,
        thread_id: str,
        to: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update the active draft email for a thread.
        
        Args:
            thread_id: Thread identifier
            to: Email recipients (comma-separated)
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)
            subject: Email subject
            body: Email body content
        
        Returns:
            Dict containing draft information or error
        """
        try:
            # Create draft key for this thread
            draft_key = f"{thread_id}_email"
            
            # Get existing draft or create new one
            if draft_key in _draft_storage:
                draft = _draft_storage[draft_key].copy()
            else:
                draft = {
                    "type": "email",
                    "thread_id": thread_id,
                    "created_at": "2025-06-07T00:00:00Z",
                }
            
            # Update draft with provided fields
            if to is not None:
                draft["to"] = to
            if cc is not None:
                draft["cc"] = cc
            if bcc is not None:
                draft["bcc"] = bcc
            if subject is not None:
                draft["subject"] = subject
            if body is not None:
                draft["body"] = body
            
            draft["updated_at"] = "2025-06-07T00:00:00Z"
            
            # Store the draft
            _draft_storage[draft_key] = draft
            
            return {"success": True, "draft": draft}
            
        except Exception as e:
            return {"error": f"Failed to create/update draft: {str(e)}"}


class DeleteDraftEmailTool:
    """
    Delete the active draft email for a thread.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self):
        pass

    def __call__(self, thread_id: str) -> Dict[str, Any]:
        """
        Delete the active draft email for a thread.
        
        Args:
            thread_id: Thread identifier
        
        Returns:
            Dict containing success status or error
        """
        try:
            draft_key = f"{thread_id}_email"
            
            if draft_key in _draft_storage:
                del _draft_storage[draft_key]
                return {"success": True, "message": "Draft email deleted"}
            else:
                return {"success": False, "message": "No draft email found for this thread"}
                
        except Exception as e:
            return {"error": f"Failed to delete draft: {str(e)}"}

class CreateDraftCalendarEventTool:
    """
    Create or update the active draft calendar event for a thread.
    This tool manages drafts locally without calling office-service.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self):
        pass

    def __call__(
        self,
        thread_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        attendees: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update the active draft calendar event for a thread.
        
        Args:
            thread_id: Thread identifier
            title: Event title
            start_time: Event start time (ISO format)
            end_time: Event end time (ISO format)
            attendees: Event attendees (comma-separated emails)
            location: Event location
            description: Event description
        
        Returns:
            Dict containing draft information or error
        """
        try:
            # Create draft key for this thread
            draft_key = f"{thread_id}_calendar_event"
            
            # Get existing draft or create new one
            if draft_key in _draft_storage:
                draft = _draft_storage[draft_key].copy()
            else:
                draft = {
                    "type": "calendar_event",
                    "thread_id": thread_id,
                    "created_at": "2025-06-07T00:00:00Z",
                }
            
            # Update draft with provided fields
            if title is not None:
                draft["title"] = title
            if start_time is not None:
                draft["start_time"] = start_time
            if end_time is not None:
                draft["end_time"] = end_time
            if attendees is not None:
                draft["attendees"] = attendees
            if location is not None:
                draft["location"] = location
            if description is not None:
                draft["description"] = description
            
            draft["updated_at"] = "2025-06-07T00:00:00Z"
            
            # Store the draft
            _draft_storage[draft_key] = draft
            
            return {"success": True, "draft": draft}
            
        except Exception as e:
            return {"error": f"Failed to create/update draft: {str(e)}"}


class DeleteDraftCalendarEventTool:
    """
    Delete the active draft calendar event for a thread.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self):
        pass

    def __call__(self, thread_id: str) -> Dict[str, Any]:
        """
        Delete the active draft calendar event for a thread.
        
        Args:
            thread_id: Thread identifier
        
        Returns:
            Dict containing success status or error
        """
        try:
            draft_key = f"{thread_id}_calendar_event"
            
            if draft_key in _draft_storage:
                del _draft_storage[draft_key]
                return {"success": True, "message": "Draft calendar event deleted"}
            else:
                return {"success": False, "message": "No draft calendar event found for this thread"}
                
        except Exception as e:
            return {"error": f"Failed to delete draft: {str(e)}"}


class CreateDraftCalendarChangeTool:
    """
    Create or update the active draft calendar change for a thread.
    This tool manages drafts locally without calling office-service.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self):
        pass

    def __call__(
        self,
        thread_id: str,
        event_id: Optional[str] = None,
        change_type: Optional[str] = None,
        new_title: Optional[str] = None,
        new_start_time: Optional[str] = None,
        new_end_time: Optional[str] = None,
        new_attendees: Optional[str] = None,
        new_location: Optional[str] = None,
        new_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update the active draft calendar change for a thread.
        
        Args:
            thread_id: Thread identifier
            event_id: ID of the event to change
            change_type: Type of change (e.g., 'update', 'cancel', 'reschedule')
            new_title: New event title
            new_start_time: New event start time (ISO format)
            new_end_time: New event end time (ISO format)
            new_attendees: New event attendees (comma-separated emails)
            new_location: New event location
            new_description: New event description
        
        Returns:
            Dict containing draft information or error
        """
        try:
            # Create draft key for this thread
            draft_key = f"{thread_id}_calendar_change"
            
            # Get existing draft or create new one
            if draft_key in _draft_storage:
                draft = _draft_storage[draft_key].copy()
            else:
                draft = {
                    "type": "calendar_change",
                    "thread_id": thread_id,
                    "created_at": "2025-06-07T00:00:00Z",
                }
            
            # Update draft with provided fields
            if event_id is not None:
                draft["event_id"] = event_id
            if change_type is not None:
                draft["change_type"] = change_type
            if new_title is not None:
                draft["new_title"] = new_title
            if new_start_time is not None:
                draft["new_start_time"] = new_start_time
            if new_end_time is not None:
                draft["new_end_time"] = new_end_time
            if new_attendees is not None:
                draft["new_attendees"] = new_attendees
            if new_location is not None:
                draft["new_location"] = new_location
            if new_description is not None:
                draft["new_description"] = new_description
            
            draft["updated_at"] = "2025-06-07T00:00:00Z"
            
            # Store the draft
            _draft_storage[draft_key] = draft
            
            return {"success": True, "draft": draft}
            
        except Exception as e:
            return {"error": f"Failed to create/update draft: {str(e)}"}


class DeleteDraftCalendarChangeTool:
    """
    Delete the active draft calendar change for a thread.
    Compatible with LLM Lite tool interface (callable class).
    """

    def __init__(self):
        pass

    def __call__(self, thread_id: str) -> Dict[str, Any]:
        """
        Delete the active draft calendar change for a thread.
        
        Args:
            thread_id: Thread identifier
        
        Returns:
            Dict containing success status or error
        """
        try:
            draft_key = f"{thread_id}_calendar_change"
            
            if draft_key in _draft_storage:
                del _draft_storage[draft_key]
                return {"success": True, "message": "Draft calendar change deleted"}
            else:
                return {"success": False, "message": "No draft calendar change found for this thread"}
                
        except Exception as e:
            return {"error": f"Failed to delete draft: {str(e)}"}
