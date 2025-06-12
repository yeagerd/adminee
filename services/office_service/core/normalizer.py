"""
Data normalization utilities for the Office Service.

Provides functions to normalize API responses from different providers
(Google, Microsoft) into consistent internal data structures.
"""

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser
from services.office_service.models import Provider
from services.office_service.schemas import (
    CalendarEvent,
    DriveFile,
    EmailAddress,
    EmailMessage,
)

logger = logging.getLogger(__name__)


def normalize_google_email(
    raw_data: Dict[str, Any], account_email: str, account_name: Optional[str] = None
) -> EmailMessage:
    """
    Convert a raw Gmail API message response into a unified EmailMessage model.

    Args:
        raw_data: Raw JSON response from Gmail API
        account_email: Email address of the account this message belongs to
        account_name: Display name for the account

    Returns:
        EmailMessage: Unified email message model

    Raises:
        ValueError: If required fields are missing from raw_data
    """
    try:
        # Extract basic message info
        message_id = raw_data.get("id")
        if not message_id:
            raise ValueError("Missing required field 'id' in Gmail response")

        thread_id = raw_data.get("threadId")
        snippet = raw_data.get("snippet", "")
        label_ids = raw_data.get("labelIds", [])

        # Parse message payload
        payload = raw_data.get("payload", {})
        headers = payload.get("headers", [])

        # Extract headers
        header_map = {header["name"].lower(): header["value"] for header in headers}

        subject = header_map.get("subject")
        date_str = header_map.get("date")

        # Parse date
        date = datetime.now(timezone.utc)
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
                # Ensure timezone awareness
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
            except Exception as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")

        # Parse email addresses
        from_address = _parse_email_address(header_map.get("from"))
        to_addresses = _parse_email_addresses(header_map.get("to", ""))
        cc_addresses = _parse_email_addresses(header_map.get("cc", ""))
        bcc_addresses = _parse_email_addresses(header_map.get("bcc", ""))

        # Extract body content
        body_text, body_html = _extract_gmail_body(payload)

        # Determine read status (UNREAD label absence means read)
        is_read = "UNREAD" not in label_ids

        # Check for attachments
        has_attachments = _has_gmail_attachments(payload)

        # Convert Gmail labels to standardized labels
        labels = _normalize_gmail_labels(label_ids)

        return EmailMessage(
            id=f"gmail_{message_id}",
            thread_id=f"gmail_{thread_id}" if thread_id else None,
            subject=subject,
            snippet=snippet,
            body_text=body_text,
            body_html=body_html,
            from_address=from_address,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            bcc_addresses=bcc_addresses,
            date=date,
            labels=labels,
            is_read=is_read,
            has_attachments=has_attachments,
            provider=Provider.GOOGLE,
            provider_message_id=message_id,
            account_email=account_email,
            account_name=account_name,
        )

    except Exception as e:
        logger.error(f"Failed to normalize Gmail message: {e}")
        logger.error(f"Raw data: {raw_data}")
        raise


def normalize_microsoft_email(
    raw_data: Dict[str, Any], account_email: str, account_name: Optional[str] = None
) -> EmailMessage:
    """
    Convert a raw Microsoft Graph API message response into a unified EmailMessage model.

    Args:
        raw_data: Raw JSON response from Microsoft Graph API
        account_email: Email address of the account this message belongs to
        account_name: Display name for the account

    Returns:
        EmailMessage: Unified email message model

    Raises:
        ValueError: If required fields are missing from raw_data
    """
    try:
        # Extract basic message info
        message_id = raw_data.get("id")
        if not message_id:
            raise ValueError("Missing required field 'id' in Microsoft Graph response")

        conversation_id = raw_data.get("conversationId")
        subject = raw_data.get("subject")
        body_preview = raw_data.get("bodyPreview", "")

        # Parse date
        date_str = raw_data.get("receivedDateTime") or raw_data.get("sentDateTime")
        date = datetime.now(timezone.utc)
        if date_str:
            try:
                # Microsoft Graph uses ISO 8601 format
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")

        # Parse email addresses
        from_address = _parse_microsoft_email_address(raw_data.get("from"))
        to_addresses = _parse_microsoft_email_addresses(
            raw_data.get("toRecipients", [])
        )
        cc_addresses = _parse_microsoft_email_addresses(
            raw_data.get("ccRecipients", [])
        )
        bcc_addresses = _parse_microsoft_email_addresses(
            raw_data.get("bccRecipients", [])
        )

        # Extract body content
        body_text, body_html = _extract_microsoft_body(raw_data.get("body", {}))

        # Determine read status
        is_read = raw_data.get("isRead", False)

        # Check for attachments
        has_attachments = raw_data.get("hasAttachments", False)

        # Convert Microsoft categories to standardized labels
        categories = raw_data.get("categories", [])
        labels = _normalize_microsoft_categories(categories)

        # Add importance as a label if high
        importance = raw_data.get("importance", "").lower()
        if importance == "high":
            labels.append("important")

        return EmailMessage(
            id=f"outlook_{message_id}",
            thread_id=f"outlook_{conversation_id}" if conversation_id else None,
            subject=subject,
            snippet=body_preview,
            body_text=body_text,
            body_html=body_html,
            from_address=from_address,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            bcc_addresses=bcc_addresses,
            date=date,
            labels=labels,
            is_read=is_read,
            has_attachments=has_attachments,
            provider=Provider.MICROSOFT,
            provider_message_id=message_id,
            account_email=account_email,
            account_name=account_name,
        )

    except Exception as e:
        logger.error(f"Failed to normalize Microsoft Graph message: {e}")
        logger.error(f"Raw data: {raw_data}")
        raise


def normalize_google_calendar_event(
    raw_data: Dict[str, Any],
    account_email: str,
    account_name: Optional[str] = None,
    calendar_name: str = "Default",
) -> CalendarEvent:
    """
    Convert a raw Google Calendar API event response into a unified CalendarEvent model.

    Args:
        raw_data: Raw JSON response from Google Calendar API
        account_email: Email address of the account this calendar belongs to
        account_name: Display name for the account
        calendar_name: Name of the specific calendar

    Returns:
        CalendarEvent: Unified calendar event model

    Raises:
        ValueError: If required fields are missing from raw_data
    """
    try:
        # Extract basic event info
        event_id = raw_data.get("id")
        if not event_id:
            raise ValueError("Missing required field 'id' in Google Calendar response")

        calendar_id = raw_data.get("calendarId", "primary")
        title = raw_data.get("summary", "")
        description = raw_data.get("description")
        location = raw_data.get("location")
        status = raw_data.get("status", "confirmed")
        visibility = raw_data.get("visibility", "default")

        # Parse start and end times
        start_time, all_day = _parse_google_datetime(raw_data.get("start", {}))
        end_time, _ = _parse_google_datetime(raw_data.get("end", {}))

        # Parse attendees
        attendees = []
        for attendee_data in raw_data.get("attendees", []):
            email_addr = _parse_email_address(attendee_data.get("email"))
            if email_addr:
                attendees.append(email_addr)

        # Parse organizer
        organizer_data = raw_data.get("organizer", {})
        organizer = _parse_email_address(organizer_data.get("email"))

        # Parse timestamps
        created_at = _parse_iso_datetime(raw_data.get("created"))
        updated_at = _parse_iso_datetime(raw_data.get("updated"))

        return CalendarEvent(
            id=f"google_{event_id}",
            calendar_id=f"google_{calendar_id}",
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            location=location,
            attendees=attendees,
            organizer=organizer,
            status=status,
            visibility=visibility,
            provider=Provider.GOOGLE,
            provider_event_id=event_id,
            account_email=account_email,
            account_name=account_name,
            calendar_name=calendar_name,
            created_at=created_at,
            updated_at=updated_at,
        )

    except Exception as e:
        logger.error(f"Failed to normalize Google Calendar event: {e}")
        logger.error(f"Raw data: {raw_data}")
        raise


def normalize_google_drive_file(
    raw_data: Dict[str, Any], account_email: str, account_name: Optional[str] = None
) -> DriveFile:
    """
    Convert a raw Google Drive API file response into a unified DriveFile model.

    Args:
        raw_data: Raw JSON response from Google Drive API
        account_email: Email address of the account this file belongs to
        account_name: Display name for the account

    Returns:
        DriveFile: Unified drive file model

    Raises:
        ValueError: If required fields are missing from raw_data
    """
    try:
        # Extract basic file info
        file_id = raw_data.get("id")
        if not file_id:
            raise ValueError("Missing required field 'id' in Google Drive response")

        name = raw_data.get("name", "")
        mime_type = raw_data.get("mimeType", "")
        size = raw_data.get("size")
        if size:
            size = int(size)

        # Parse timestamps
        created_time = _parse_iso_datetime(raw_data.get("createdTime"))
        modified_time = _parse_iso_datetime(raw_data.get("modifiedTime"))

        # Extract links
        web_view_link = raw_data.get("webViewLink")
        download_link = raw_data.get("webContentLink")
        thumbnail_link = raw_data.get("thumbnailLink")

        # Check if it's a folder
        is_folder = mime_type == "application/vnd.google-apps.folder"

        # Extract parent folder (first parent)
        parents = raw_data.get("parents", [])
        parent_folder_id = f"google_{parents[0]}" if parents else None

        return DriveFile(
            id=f"google_{file_id}",
            name=name,
            mime_type=mime_type,
            size=size,
            created_time=created_time,
            modified_time=modified_time,
            web_view_link=web_view_link,
            download_link=download_link,
            thumbnail_link=thumbnail_link,
            parent_folder_id=parent_folder_id,
            is_folder=is_folder,
            provider=Provider.GOOGLE,
            provider_file_id=file_id,
            account_email=account_email,
            account_name=account_name,
        )

    except Exception as e:
        logger.error(f"Failed to normalize Google Drive file: {e}")
        logger.error(f"Raw data: {raw_data}")
        raise


def normalize_microsoft_drive_file(
    raw_data: Dict[str, Any], account_email: str, account_name: Optional[str] = None
) -> DriveFile:
    """
    Convert a raw Microsoft OneDrive API file response into a unified DriveFile model.

    Args:
        raw_data: Raw JSON response from Microsoft Graph API (OneDrive)
        account_email: Email address of the account this file belongs to
        account_name: Display name for the account

    Returns:
        DriveFile: Unified drive file model

    Raises:
        ValueError: If required fields are missing from raw_data
    """
    try:
        # Extract basic file info
        file_id = raw_data.get("id")
        if not file_id:
            raise ValueError(
                "Missing required field 'id' in Microsoft OneDrive response"
            )

        name = raw_data.get("name", "")

        # Microsoft stores size as an integer directly
        size = raw_data.get("size")

        # Parse timestamps
        created_time = _parse_iso_datetime(raw_data.get("createdDateTime"))
        modified_time = _parse_iso_datetime(raw_data.get("lastModifiedDateTime"))

        # Extract links
        web_view_link = raw_data.get("webUrl")
        download_link = raw_data.get("@microsoft.graph.downloadUrl")
        thumbnail_link = None

        # Extract thumbnail from thumbnails array if available
        thumbnails = raw_data.get("thumbnails", [])
        if thumbnails and len(thumbnails) > 0:
            large_thumb = thumbnails[0].get("large", {})
            thumbnail_link = large_thumb.get("url")

        # Check if it's a folder
        is_folder = "folder" in raw_data

        # Get MIME type - Microsoft stores it in file.mimeType
        file_data = raw_data.get("file", {})
        mime_type = file_data.get("mimeType", "")

        # If it's a folder, use the standard folder MIME type
        if is_folder:
            mime_type = "application/vnd.microsoft.onedrive.folder"

        # Extract parent folder info
        parent_reference = raw_data.get("parentReference", {})
        parent_folder_id = parent_reference.get("id")
        if parent_folder_id:
            parent_folder_id = f"microsoft_{parent_folder_id}"

        return DriveFile(
            id=f"microsoft_{file_id}",
            name=name,
            mime_type=mime_type,
            size=size,
            created_time=created_time,
            modified_time=modified_time,
            web_view_link=web_view_link,
            download_link=download_link,
            thumbnail_link=thumbnail_link,
            parent_folder_id=parent_folder_id,
            is_folder=is_folder,
            provider=Provider.MICROSOFT,
            provider_file_id=file_id,
            account_email=account_email,
            account_name=account_name,
        )

    except Exception as e:
        logger.error(f"Failed to normalize Microsoft OneDrive file: {e}")
        logger.error(f"Raw data: {raw_data}")
        raise


# Helper functions


def _parse_email_address(email_str: Optional[str]) -> Optional[EmailAddress]:
    """Parse email address string into EmailAddress model."""
    if not email_str:
        return None

    # Handle format: "Name <email@domain.com>" or just "email@domain.com"
    match = re.match(r"^(.+?)\s*<(.+?)>$", email_str.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip()
    else:
        name = None
        email = email_str.strip()

    try:
        return EmailAddress(email=email, name=name)
    except Exception:
        return None


def _parse_email_addresses(email_str: str) -> List[EmailAddress]:
    """Parse comma-separated email addresses."""
    if not email_str:
        return []

    addresses = []
    for addr in email_str.split(","):
        parsed = _parse_email_address(addr.strip())
        if parsed:
            addresses.append(parsed)

    return addresses


def _parse_microsoft_email_address(
    addr_data: Optional[Dict[str, Any]],
) -> Optional[EmailAddress]:
    """Parse Microsoft Graph email address object."""
    if not addr_data:
        return None

    email_addr = addr_data.get("emailAddress", {})
    email = email_addr.get("address")
    name = email_addr.get("name")

    if not email:
        return None

    try:
        return EmailAddress(email=email, name=name)
    except Exception:
        return None


def _parse_microsoft_email_addresses(
    addr_list: List[Dict[str, Any]],
) -> List[EmailAddress]:
    """Parse Microsoft Graph email address list."""
    addresses = []
    for addr_data in addr_list:
        parsed = _parse_microsoft_email_address(addr_data)
        if parsed:
            addresses.append(parsed)

    return addresses


def _extract_gmail_body(payload: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Extract text and HTML body from Gmail payload."""
    body_text = None
    body_html = None

    def extract_part(part: Dict[str, Any]):
        nonlocal body_text, body_html

        mime_type = part.get("mimeType", "")
        body = part.get("body", {})

        if mime_type == "text/plain" and not body_text:
            data = body.get("data")
            if data:
                import base64

                try:
                    body_text = base64.urlsafe_b64decode(data).decode("utf-8")
                except Exception:
                    pass

        elif mime_type == "text/html" and not body_html:
            data = body.get("data")
            if data:
                import base64

                try:
                    body_html = base64.urlsafe_b64decode(data).decode("utf-8")
                except Exception:
                    pass

        # Recursively check parts
        for sub_part in part.get("parts", []):
            extract_part(sub_part)

    extract_part(payload)
    return body_text, body_html


def _extract_microsoft_body(
    body_data: Dict[str, Any],
) -> tuple[Optional[str], Optional[str]]:
    """Extract text and HTML body from Microsoft Graph body object."""
    content_type = body_data.get("contentType", "").lower()
    content = body_data.get("content")

    if content_type == "html":
        return None, content
    elif content_type == "text":
        return content, None
    else:
        # Default to text
        return content, None


def _has_gmail_attachments(payload: Dict[str, Any]) -> bool:
    """Check if Gmail message has attachments."""

    def check_part(part: Dict[str, Any]) -> bool:
        # Check if this part has an attachment
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            return True

        # Check sub-parts
        for sub_part in part.get("parts", []):
            if check_part(sub_part):
                return True

        return False

    return check_part(payload)


def _normalize_gmail_labels(label_ids: List[str]) -> List[str]:
    """Convert Gmail label IDs to standardized labels."""
    label_map = {
        "INBOX": "inbox",
        "SENT": "sent",
        "DRAFT": "draft",
        "SPAM": "spam",
        "TRASH": "trash",
        "IMPORTANT": "important",
        "STARRED": "starred",
        "CATEGORY_PERSONAL": "personal",
        "CATEGORY_SOCIAL": "social",
        "CATEGORY_PROMOTIONS": "promotions",
        "CATEGORY_UPDATES": "updates",
        "CATEGORY_FORUMS": "forums",
    }

    labels = []
    for label_id in label_ids:
        if label_id in label_map:
            labels.append(label_map[label_id])
        else:
            # Keep custom labels as-is
            labels.append(label_id.lower())

    return labels


def _normalize_microsoft_categories(categories: List[str]) -> List[str]:
    """Convert Microsoft categories to standardized labels."""
    # Microsoft categories are already user-friendly strings
    return [cat.lower() for cat in categories]


def _parse_google_datetime(dt_data: Dict[str, Any]) -> tuple[datetime, bool]:
    """Parse Google Calendar datetime object."""
    # Check if it's a date-only event (all-day)
    date_str = dt_data.get("date")
    if date_str:
        # All-day event
        try:
            date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            return date, True
        except Exception:
            return datetime.now(timezone.utc), True

    # Regular datetime event
    datetime_str = dt_data.get("dateTime")
    if datetime_str:
        try:
            date = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            return date, False
        except Exception:
            return datetime.now(timezone.utc), False

    # Fallback
    return datetime.now(timezone.utc), False


def _parse_iso_datetime(dt_str: Optional[str]) -> datetime:
    """Parse ISO datetime string with fallback."""
    if not dt_str:
        return datetime.now(timezone.utc)

    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)
