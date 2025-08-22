"""
Draft management tools for email and calendar content creation.
"""

import logging
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)

# Global draft storage for in-memory draft management
# This is used by the workflow system to maintain draft state during conversations
_draft_storage: Dict[str, Dict[str, Any]] = {}


class DraftTools:
    """Collection of draft management tools with pre-authenticated user context."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    def create_draft_email(
        self,
        thread_id: str,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a draft email for the given thread."""
        try:
            key = f"{thread_id}_email"
            email_data = {
                "to": to or "",
                "subject": subject or "",
                "body": body or "",
                "user_id": self.user_id,
                **kwargs,
            }
            _draft_storage[key] = email_data
            logger.info(f"📧 Created email draft for thread {thread_id}")
            return {"success": True, "draft": email_data}
        except Exception as e:
            logger.error(f"Failed to create email draft: {e}")
            return {"success": False, "error": str(e)}

    def create_draft_calendar_event(
        self,
        thread_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        attendees: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create or update a draft calendar event for the given thread."""
        try:
            key = f"{thread_id}_calendar_event"

            # Get existing draft if it exists
            existing_draft = _draft_storage.get(key, {})

            # Build event data, only including fields that are provided or already exist
            event_data = {
                "type": "calendar_event",
                "thread_id": thread_id,
                "user_id": self.user_id,
            }

            # Add fields that are provided or already exist
            if title is not None:
                event_data["title"] = title
            elif "title" in existing_draft:
                event_data["title"] = existing_draft["title"]

            if start_time is not None:
                event_data["start_time"] = start_time
            elif "start_time" in existing_draft:
                event_data["start_time"] = existing_draft["start_time"]

            if end_time is not None:
                event_data["end_time"] = end_time
            elif "end_time" in existing_draft:
                event_data["end_time"] = existing_draft["end_time"]

            if attendees is not None:
                event_data["attendees"] = attendees
            elif "attendees" in existing_draft:
                event_data["attendees"] = existing_draft["attendees"]

            if location is not None:
                event_data["location"] = location
            elif "location" in existing_draft:
                event_data["location"] = existing_draft["location"]

            if description is not None:
                event_data["description"] = description
            elif "description" in existing_draft:
                event_data["description"] = existing_draft["description"]

            # Add any additional kwargs
            event_data.update(kwargs)

            _draft_storage[key] = event_data
            logger.info(f"📅 Created/updated calendar event draft for thread {thread_id}")
            return {"success": True, "draft": event_data}
        except Exception as e:
            logger.error(f"Failed to create calendar event draft: {e}")
            return {"success": False, "error": str(e)}

    def create_draft_calendar_change(
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
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a draft calendar change for the given thread."""
        try:
            # Validate required parameters
            if not event_id or not event_id.strip():
                return {"success": False, "message": "event_id is required"}

            key = f"{thread_id}_calendar_edit"

            # Get existing draft if it exists
            existing_draft = _draft_storage.get(key, {})

            # Build change data, only including fields that are provided or already exist
            change_data: Dict[str, Any] = {}

            # Add fields that are provided or already exist
            if event_id is not None:
                change_data["event_id"] = event_id
            elif "event_id" in existing_draft:
                change_data["event_id"] = existing_draft["event_id"]

            if change_type is not None:
                change_data["change_type"] = change_type
            elif "change_type" in existing_draft:
                change_data["change_type"] = existing_draft["change_type"]

            # Initialize changes dict with proper typing
            changes: Dict[str, Any] = {}

            if new_title is not None:
                changes["title"] = new_title
            elif "changes" in existing_draft and "title" in existing_draft["changes"]:
                changes["title"] = existing_draft["changes"]["title"]

            if new_start_time is not None:
                changes["start_time"] = new_start_time
            elif "changes" in existing_draft and "start_time" in existing_draft["changes"]:
                changes["start_time"] = existing_draft["changes"]["start_time"]

            if new_end_time is not None:
                changes["end_time"] = new_end_time
            elif "changes" in existing_draft and "end_time" in existing_draft["changes"]:
                changes["end_time"] = existing_draft["changes"]["end_time"]

            if new_attendees is not None:
                attendee_list = []
                for email in new_attendees.split(","):
                    email = email.strip()
                    if email:
                        attendee_list.append({"email": email, "name": email.split("@")[0]})
                changes["attendees"] = attendee_list
            elif "changes" in existing_draft and "attendees" in existing_draft["changes"]:
                changes["attendees"] = existing_draft["changes"]["attendees"]

            if new_location is not None:
                changes["location"] = new_location
            elif "changes" in existing_draft and "location" in existing_draft["changes"]:
                changes["location"] = existing_draft["changes"]["location"]

            if new_description is not None:
                changes["description"] = new_description
            elif "changes" in existing_draft and "description" in existing_draft["changes"]:
                changes["description"] = existing_draft["changes"]["description"]

            # Add any additional kwargs to changes if they're not already handled
            for key_name, value in kwargs.items():
                if key_name not in ["event_id", "change_type"] and value is not None:
                    changes[key_name] = value

            # Check if any new changes were actually provided (not just existing ones)
            new_params_provided = any(
                [
                    new_title is not None,
                    new_start_time is not None,
                    new_end_time is not None,
                    new_attendees is not None,
                    new_location is not None,
                    new_description is not None,
                ]
            )

            if not new_params_provided and not kwargs:
                return {"success": False, "message": "No changes provided"}

            # Add the changes to the change data
            change_data["changes"] = changes

            _draft_storage[key] = change_data
            logger.info(f"✏️ Created/updated calendar edit draft for thread {thread_id}")
            return {"success": True, "draft": change_data}
        except Exception as e:
            logger.error(f"Failed to create calendar edit draft: {e}")
            return {"success": False, "error": str(e)}

    def get_draft_email(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get the email draft for the given thread."""
        key = f"{thread_id}_email"
        return _draft_storage.get(key)

    def get_draft_calendar_event(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get the calendar event draft for the given thread."""
        key = f"{thread_id}_calendar_event"
        return _draft_storage.get(key)

    def get_draft_calendar_edit(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get the calendar edit draft for the given thread."""
        key = f"{thread_id}_calendar_edit"
        return _draft_storage.get(key)

    def has_draft_email(self, thread_id: str) -> bool:
        """Check if there's an email draft for the given thread."""
        key = f"{thread_id}_email"
        return key in _draft_storage

    def has_draft_calendar_event(self, thread_id: str) -> bool:
        """Check if there's a calendar event draft for the given thread."""
        key = f"{thread_id}_calendar_event"
        return key in _draft_storage

    def has_draft_calendar_edit(self, thread_id: str) -> bool:
        """Check if there's a calendar edit draft for the given thread."""
        key = f"{thread_id}_calendar_edit"
        return key in _draft_storage

    def delete_draft_email(self, thread_id: str) -> Dict[str, Any]:
        """Delete the email draft for the given thread."""
        try:
            key = f"{thread_id}_email"
            if key in _draft_storage:
                del _draft_storage[key]
                logger.info(f"🗑️ Deleted email draft for thread {thread_id}")
                return {
                    "success": True,
                    "deleted": True,
                    "message": "Email draft deleted successfully",
                }
            return {"success": True, "deleted": False, "message": "No email draft found"}
        except Exception as e:
            logger.error(f"Failed to delete email draft: {e}")
            return {"success": False, "error": str(e)}

    def delete_draft_calendar_event(self, thread_id: str) -> Dict[str, Any]:
        """Delete the calendar event draft for the given thread."""
        try:
            key = f"{thread_id}_calendar_event"
            if key in _draft_storage:
                del _draft_storage[key]
                logger.info(f"🗑️ Deleted calendar event draft for thread {thread_id}")
                return {
                    "success": True,
                    "deleted": True,
                    "message": "Calendar event draft deleted successfully",
                }
            return {
                "success": True,
                "deleted": False,
                "message": "No calendar event draft found",
            }
        except Exception as e:
            logger.error(f"Failed to delete calendar event draft: {e}")
            return {"success": False, "error": str(e)}

    def delete_draft_calendar_edit(self, thread_id: str) -> Dict[str, Any]:
        """Delete the calendar edit draft for the given thread."""
        try:
            key = f"{thread_id}_calendar_edit"
            if key in _draft_storage:
                del _draft_storage[key]
                logger.info(f"🗑️ Deleted calendar edit draft for thread {thread_id}")
                return {
                    "success": True,
                    "deleted": True,
                    "message": "Calendar event edit draft deleted successfully",
                }
            return {"success": False, "message": "No calendar event edit draft found"}
        except Exception as e:
            logger.error(f"Failed to delete calendar edit draft: {e}")
            return {"success": False, "error": str(e)}

    def clear_all_drafts(self, thread_id: str) -> Dict[str, Any]:
        """Clear all drafts for the given thread."""
        try:
            thread_prefix = f"{thread_id}_"
            keys_to_remove = [
                key for key in _draft_storage.keys() if key.startswith(thread_prefix)
            ]

            # Extract draft types from keys
            cleared_drafts = []
            for key in keys_to_remove:
                if key.endswith("_email"):
                    cleared_drafts.append("email")
                elif key.endswith("_calendar_event"):
                    cleared_drafts.append("calendar_event")
                elif key.endswith("_calendar_edit"):
                    cleared_drafts.append("calendar_edit")
                else:
                    # For any other draft types, extract the type
                    draft_type = key.replace(thread_prefix, "")
                    cleared_drafts.append(draft_type)

            for key in keys_to_remove:
                del _draft_storage[key]

            logger.info(f"🗑️ Cleared {len(keys_to_remove)} drafts for thread {thread_id}")
            return {
                "success": True,
                "cleared_count": len(keys_to_remove),
                "cleared_drafts": cleared_drafts,
            }
        except Exception as e:
            logger.error(f"Failed to clear drafts: {e}")
            return {"success": False, "error": str(e)}

    def get_draft_data(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all draft data for the given thread."""
        try:
            thread_prefix = f"{thread_id}_"
            drafts = []
            
            for draft_key, draft_data in _draft_storage.items():
                if draft_key.startswith(thread_prefix):
                    draft_copy = draft_data.copy()
                    draft_copy["thread_id"] = thread_id
                    drafts.append(draft_copy)

            return drafts
        except Exception as e:
            logger.error(f"Error getting draft data: {e}")
            return []
