"""
Data normalization utilities for the Office Service.

Provides functions to normalize API responses from different providers
(Google, Microsoft) into consistent internal data structures.
"""

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from services.common.logging_config import get_logger
from services.office.models import Provider
from services.office.schemas import (
    CalendarEvent,
    Contact,
    ContactPhone,
    DriveFile,
    EmailAddress,
    EmailMessage,
    EmailThread,
)

logger = get_logger(__name__)


def _safe_log_raw_data(raw_data: Dict[str, Any], max_content_length: int = 100) -> str:
    """
    Safely log raw API response data without exposing sensitive content.

    Args:
        raw_data: Raw API response dictionary
        max_content_length: Maximum length of content to show in logs

    Returns:
        Safe string representation of the data
    """
    safe_data = {}

    # Copy non-sensitive fields
    for key, value in raw_data.items():
        if key in [
            "id",
            "conversationId",
            "subject",
            "bodyPreview",
            "receivedDateTime",
            "sentDateTime",
            "isRead",
            "hasAttachments",
            "categories",
            "importance",
        ]:
            safe_data[key] = value
        elif key == "body":
            # Log body structure but not content
            if isinstance(value, dict):
                safe_data[key] = (
                    f"<body_content> (type: dict, keys: {list(value.keys()) if isinstance(value, dict) else 'unknown'})"
                )
            else:
                safe_data[key] = f"<body_content> (type: {type(value).__name__})"
        elif key in ["from", "toRecipients", "ccRecipients", "bccRecipients"]:
            # Log email address structure but not full addresses
            if isinstance(value, dict):
                safe_data[key] = f"<email_address> (type: {type(value).__name__})"
            elif isinstance(value, list):
                safe_data[key] = f"<{len(value)} email_addresses> (type: list)"
            else:
                safe_data[key] = f"<email_address> (type: {type(value).__name__})"
        else:
            # For other fields, show type and length if applicable
            if isinstance(value, str) and len(value) > max_content_length:
                safe_data[key] = f"{str(value)[:max_content_length]}... [TRUNCATED]"
            else:
                safe_data[key] = value

    return str(safe_data)


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
        
        # Use content splitting to separate visible content from quoted content
        from services.office.core.email_content_splitter import split_email_content
        
        split_result = split_email_content(
            html_content=body_html,
            text_content=body_text
        )
        
        # Extract visible content (non-quoted part) for the unquoted fields
        visible_content = split_result.get("visible_content", "")
        quoted_content = split_result.get("quoted_content", "")
        
        # Determine which unquoted field to populate based on available content
        body_text_unquoted = None
        body_html_unquoted = None
        
        if visible_content:
            if body_html:
                # If we have HTML content, populate body_html_unquoted
                body_html_unquoted = visible_content
                # Also extract text version for body_text_unquoted
                import re
                body_text_unquoted = re.sub(r"<[^>]+>", "", visible_content)
                body_text_unquoted = (
                    body_text_unquoted.replace("&nbsp;", " ")
                    .replace("&amp;", "&")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                )
                body_text_unquoted = re.sub(r"\s+", " ", body_text_unquoted).strip()
            else:
                # If we only have text content, populate body_text_unquoted
                body_text_unquoted = visible_content
        
        # Fallback to original content if splitting didn't work
        if not visible_content:
            if body_html:
                # Simple HTML to text extraction as fallback
                import re
                visible_content = re.sub(r"<[^>]+>", "", body_html)
                visible_content = (
                    visible_content.replace("&nbsp;", " ")
                    .replace("&amp;", "&")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                )
                visible_content = re.sub(r"\s+", " ", visible_content).strip()
                body_text_unquoted = visible_content
            else:
                visible_content = body_text or ""
                body_text_unquoted = visible_content
        
        # Ensure we have some content
        if not visible_content:
            visible_content = snippet or "No content available"
            body_text_unquoted = visible_content

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
            body_text_unquoted=body_text_unquoted,  # the non-quoted email body content
            body_html_unquoted=body_html_unquoted,  # the non-quoted email HTML content
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
        logger.error(f"Safe raw data: {_safe_log_raw_data(raw_data)}")
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
        # Debug logging to see what we're getting from Microsoft Graph API
        logger.debug(
            f"Normalizing Microsoft email with raw data keys: {list(raw_data.keys())}"
        )
        logger.debug(f"Safe raw data sample: {_safe_log_raw_data(raw_data)}")

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
        body_data = raw_data.get("body", {})
        logger.debug(
            f"Microsoft body data for message {message_id}: <body_content> (type: {type(body_data).__name__})"
        )
        logger.debug(f"Body data type: {type(body_data)}")
        logger.debug(
            f"Body data keys: {list(body_data.keys()) if isinstance(body_data, dict) else 'Not a dict'}"
        )

        body_text, body_html = _extract_microsoft_body(body_data)
        
        # Use content splitting to separate visible content from quoted content
        from services.office.core.email_content_splitter import split_email_content
        
        split_result = split_email_content(
            html_content=body_html,
            text_content=body_text
        )
        
        # Extract visible content (non-quoted part) for the unquoted fields
        visible_content = split_result.get("visible_content", "")
        quoted_content = split_result.get("quoted_content", "")
        
        # Determine which unquoted field to populate based on available content
        body_text_unquoted = None
        body_html_unquoted = None
        
        if visible_content:
            if body_html:
                # If we have HTML content, populate body_html_unquoted
                body_html_unquoted = visible_content
                # Also extract text version for body_text_unquoted
                import re
                body_text_unquoted = re.sub(r"<[^>]+>", "", visible_content)
                body_text_unquoted = (
                    body_text_unquoted.replace("&nbsp;", " ")
                    .replace("&amp;", "&")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                )
                body_text_unquoted = re.sub(r"\s+", " ", body_text_unquoted).strip()
            else:
                # If we only have text content, populate body_text_unquoted
                body_text_unquoted = visible_content
        
        # Fallback to original content if splitting didn't work
        if not visible_content:
            if body_html:
                # Simple HTML to text extraction as fallback
                import re
                visible_content = re.sub(r"<[^>]+>", "", body_html)
                visible_content = (
                    visible_content.replace("&nbsp;", " ")
                    .replace("&amp;", "&")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                )
                visible_content = re.sub(r"\s+", " ", visible_content).strip()
                body_text_unquoted = visible_content
            else:
                visible_content = body_text or ""
                body_text_unquoted = visible_content
        
        # Ensure we have some content
        if not visible_content:
            visible_content = body_preview or "No content available"
            body_text_unquoted = visible_content

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
            body_text_unquoted=body_text_unquoted,  # the non-quoted email body content
            body_html_unquoted=body_html_unquoted,  # the non-quoted email HTML content
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
        logger.error(f"Safe raw data: {_safe_log_raw_data(raw_data)}")
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
        created_at = _parse_iso_datetime(raw_data.get("created")) or datetime.now(
            timezone.utc
        )
        updated_at = _parse_iso_datetime(raw_data.get("updated")) or datetime.now(
            timezone.utc
        )

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
        logger.error(f"Safe raw data: {_safe_log_raw_data(raw_data)}")
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
        created_time = _parse_iso_datetime(raw_data.get("createdTime")) or datetime.now(
            timezone.utc
        )
        modified_time = _parse_iso_datetime(
            raw_data.get("modifiedTime")
        ) or datetime.now(timezone.utc)

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
        logger.error(f"Safe raw data: {_safe_log_raw_data(raw_data)}")
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
        created_time = _parse_iso_datetime(
            raw_data.get("createdDateTime")
        ) or datetime.now(timezone.utc)
        modified_time = _parse_iso_datetime(
            raw_data.get("lastModifiedDateTime")
        ) or datetime.now(timezone.utc)

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
        logger.error(f"Safe raw data: {_safe_log_raw_data(raw_data)}")
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

    def extract_part(part: Dict[str, Any]) -> None:
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
    logger.debug(
        f"Extracting Microsoft body from: <body_data> (type: {type(body_data).__name__})"
    )
    logger.debug(f"Body data type: {type(body_data)}")
    logger.debug(
        f"Body data keys: {list(body_data.keys()) if isinstance(body_data, dict) else 'Not a dict'}"
    )

    content_type = body_data.get("contentType", "").lower()
    content = body_data.get("content")

    logger.debug(f"Content type: {content_type}")
    logger.debug(f"Content length: {len(content) if content else 0}")
    logger.debug(
        f"Content sample: <content_truncated> (length: {len(content) if content else 0})"
    )

    if content_type == "html":
        logger.debug(
            f"Returning HTML content, length: {len(content) if content else 0}"
        )
        return None, content
    elif content_type == "text":
        logger.debug(
            f"Returning text content, length: {len(content) if content else 0}"
        )
        return content, None
    else:
        # Default to text
        logger.debug(
            f"Defaulting to text content, length: {len(content) if content else 0}"
        )
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


def _parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO datetime string to datetime object.

    Args:
        dt_str: ISO datetime string

    Returns:
        datetime object or None if parsing fails
    """
    if not dt_str:
        return None

    try:
        # Try parsing with timezone info
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt
    except ValueError:
        try:
            # Try parsing without timezone info (assume UTC)
            dt = datetime.fromisoformat(dt_str)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Failed to parse datetime: {dt_str}")
            return None


def normalize_google_thread(
    raw_data: Dict[str, Any], account_email: str, account_name: Optional[str] = None
) -> EmailThread:
    """
    Convert a raw Gmail API thread response into a unified EmailThread model.

    Args:
        raw_data: Raw JSON response from Gmail API threads endpoint
        account_email: Email address of the account this thread belongs to
        account_name: Display name for the account

    Returns:
        EmailThread: Unified email thread model

    Raises:
        ValueError: If required fields are missing from raw_data
    """
    try:
        # Extract basic thread info
        thread_id = raw_data.get("id")
        if not thread_id:
            raise ValueError("Missing required field 'id' in Gmail thread response")

        # Extract messages from thread
        messages_data = raw_data.get("messages", [])
        if not messages_data:
            raise ValueError("No messages found in Gmail thread")

        # Normalize each message
        messages = []
        for msg_data in messages_data:
            try:
                normalized_msg = normalize_google_email(
                    msg_data, account_email, account_name
                )
                messages.append(normalized_msg)
            except Exception as e:
                logger.warning(
                    f"Failed to normalize message in thread {thread_id}: {e}"
                )
                continue

        if not messages:
            raise ValueError(f"No valid messages found in thread {thread_id}")

        # Sort messages by date
        messages.sort(key=lambda msg: msg.date)

        # Calculate thread metadata
        first_message = messages[0]
        last_message = messages[-1]

        # Count unique participants
        participants = set()
        for msg in messages:
            if msg.from_address:
                participants.add(msg.from_address.email)
            for addr in msg.to_addresses:
                participants.add(addr.email)
            for addr in msg.cc_addresses:
                participants.add(addr.email)

        # Determine read status (thread is read if all messages are read)
        is_read = all(msg.is_read for msg in messages)

        return EmailThread(
            id=f"gmail_{thread_id}",
            subject=first_message.subject,
            messages=messages,
            participant_count=len(participants),
            last_message_date=last_message.date,
            is_read=is_read,
            providers=[Provider.GOOGLE],
        )

    except Exception as e:
        logger.error(f"Failed to normalize Gmail thread: {e}")
        raise


def normalize_microsoft_conversation(
    raw_data: Dict[str, Any],
    messages_data: List[Dict[str, Any]],
    account_email: str,
    account_name: Optional[str] = None,
) -> EmailThread:
    """
    Convert a raw Microsoft Graph API conversation response into a unified EmailThread model.

    Args:
        raw_data: Raw JSON response from Microsoft Graph conversations endpoint
        messages_data: List of message data from the conversation
        account_email: Email address of the account this conversation belongs to
        account_name: Display name for the account

    Returns:
        EmailThread: Unified email thread model

    Raises:
        ValueError: If required fields are missing from raw_data
    """
    try:
        # Extract basic conversation info
        conversation_id = raw_data.get("id")
        if not conversation_id:
            raise ValueError(
                "Missing required field 'id' in Microsoft conversation response"
            )

        if not messages_data:
            raise ValueError("No messages found in Microsoft conversation")

        # Normalize each message
        messages = []
        for msg_data in messages_data:
            try:
                normalized_msg = normalize_microsoft_email(
                    msg_data, account_email, account_name
                )
                messages.append(normalized_msg)
            except Exception as e:
                logger.warning(
                    f"Failed to normalize message in conversation {conversation_id}: {e}"
                )
                continue

        if not messages:
            raise ValueError(
                f"No valid messages found in conversation {conversation_id}"
            )

        # Sort messages by date
        messages.sort(key=lambda msg: msg.date)

        # Calculate thread metadata
        first_message = messages[0]
        last_message = messages[-1]

        # Count unique participants
        participants = set()
        for msg in messages:
            if msg.from_address:
                participants.add(msg.from_address.email)
            for addr in msg.to_addresses:
                participants.add(addr.email)
            for addr in msg.cc_addresses:
                participants.add(addr.email)

        # Determine read status (thread is read if all messages are read)
        is_read = all(msg.is_read for msg in messages)

        return EmailThread(
            id=f"microsoft_{conversation_id}",
            subject=raw_data.get("topic") or first_message.subject,
            messages=messages,
            participant_count=len(participants),
            last_message_date=last_message.date,
            is_read=is_read,
            providers=[Provider.MICROSOFT],
        )

    except Exception as e:
        logger.error(f"Failed to normalize Microsoft conversation: {e}")
        raise


def normalize_thread_id(provider: str, original_id: str) -> str:
    """
    Normalize a thread ID to the unified format.

    Args:
        provider: Provider name (google, microsoft)
        original_id: Original thread ID from the provider

    Returns:
        Unified thread ID in format "provider_originalId"
    """
    provider_map = {
        "google": "gmail",
        "gmail": "gmail",
        "microsoft": "microsoft",
        "outlook": "microsoft",
    }

    normalized_provider = provider_map.get(provider.lower(), provider.lower())
    return f"{normalized_provider}_{original_id}"


def merge_threads(threads: List[EmailThread]) -> List[EmailThread]:
    """
    Merge threads that represent the same conversation across providers.

    Args:
        threads: List of threads to merge

    Returns:
        List of merged threads
    """
    if not threads:
        return []

    # Group threads by subject and participants
    thread_groups: Dict[Tuple[str, frozenset], List[EmailThread]] = {}

    for thread in threads:
        # Create a key based on subject and participants
        participants = set()
        for msg in thread.messages:
            if msg.from_address:
                participants.add(msg.from_address.email)
            for addr in msg.to_addresses:
                participants.add(addr.email)
            for addr in msg.cc_addresses:
                participants.add(addr.email)

        # Normalize subject for comparison
        subject_key = (thread.subject or "").lower().strip()

        # Create a composite key
        key = (subject_key, frozenset(participants))

        if key not in thread_groups:
            thread_groups[key] = []
        thread_groups[key].append(thread)

    # Merge threads in each group
    merged_threads = []

    for key, group_threads in thread_groups.items():
        if len(group_threads) == 1:
            # No merging needed
            merged_threads.append(group_threads[0])
        else:
            # Merge multiple threads
            merged_thread = _merge_thread_group(group_threads)
            merged_threads.append(merged_thread)

    # Sort by last message date
    merged_threads.sort(key=lambda t: t.last_message_date, reverse=True)

    return merged_threads


def _merge_thread_group(threads: List[EmailThread]) -> EmailThread:
    """
    Merge a group of threads that represent the same conversation.

    Args:
        threads: List of threads to merge

    Returns:
        Merged thread
    """
    if not threads:
        raise ValueError("Cannot merge empty thread group")

    if len(threads) == 1:
        return threads[0]

    # Combine all messages from all threads
    all_messages = []
    all_providers = set()

    for thread in threads:
        all_messages.extend(thread.messages)
        all_providers.update(thread.providers)

    # Remove duplicates based on message ID
    seen_ids = set()
    unique_messages = []

    for msg in all_messages:
        if msg.id not in seen_ids:
            seen_ids.add(msg.id)
            unique_messages.append(msg)

    # Sort messages by date
    unique_messages.sort(key=lambda msg: msg.date)

    if not unique_messages:
        raise ValueError("No valid messages found after merging")

    # Calculate merged thread metadata
    first_message = unique_messages[0]
    last_message = unique_messages[-1]

    # Count unique participants
    participants = set()
    for msg in unique_messages:
        if msg.from_address:
            participants.add(msg.from_address.email)
        for addr in msg.to_addresses:
            participants.add(addr.email)
        for addr in msg.cc_addresses:
            participants.add(addr.email)

    # Determine read status (thread is read if all messages are read)
    is_read = all(msg.is_read for msg in unique_messages)

    # Use the first thread's ID as the merged ID
    merged_id = threads[0].id

    return EmailThread(
        id=merged_id,
        subject=first_message.subject,
        messages=unique_messages,
        participant_count=len(participants),
        last_message_date=last_message.date,
        is_read=is_read,
        providers=list(all_providers),
    )


def _derive_company_from_email(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return None
    try:
        domain = email.split("@", 1)[1]
        # Strip common subdomains
        parts = domain.split(".")
        if len(parts) >= 2:
            core = parts[-2]
        else:
            core = parts[0]
        if not core:
            return None
        # Capitalize core name
        return core.capitalize()
    except Exception:
        return None


def normalize_google_contact(
    raw: Dict[str, Any], account_email: str, account_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Normalize a Google People API contact into unified Contact dict (model_dump-like).
    """
    resource_name = raw.get("resourceName") or raw.get("id")
    names = raw.get("names", [])
    primary_name = next(
        (n for n in names if n.get("metadata", {}).get("primary")),
        names[0] if names else {},
    )
    full_name = primary_name.get("displayName")
    given_name = primary_name.get("givenName")
    family_name = primary_name.get("familyName")

    email_addrs = []
    primary_email_obj = None
    for e in raw.get("emailAddresses", []) or []:
        addr = e.get("value") or e.get("email")
        if not addr:
            continue
        name = e.get("displayName") or None
        email_model = EmailAddress(email=addr, name=name)
        email_addrs.append(email_model)
        if e.get("metadata", {}).get("primary") and primary_email_obj is None:
            primary_email_obj = email_model
    if primary_email_obj is None and email_addrs:
        primary_email_obj = email_addrs[0]

    organizations = raw.get("organizations", []) or []
    primary_org = next(
        (o for o in organizations if o.get("metadata", {}).get("primary")),
        organizations[0] if organizations else {},
    )
    company = primary_org.get("name") or _derive_company_from_email(
        primary_email_obj.email if primary_email_obj else None
    )
    job_title = primary_org.get("title")

    phones: List[ContactPhone] = []
    for p in raw.get("phoneNumbers", []) or []:
        number = p.get("value")
        if not isinstance(number, str) or not number:
            continue
        type_label = p.get("type") or p.get("formattedType")
        phones.append(ContactPhone(type=type_label, number=number))

    photos = raw.get("photos", []) or []
    primary_photo = next(
        (p for p in photos if p.get("metadata", {}).get("primary")),
        photos[0] if photos else {},
    )
    photo_url = primary_photo.get("url")

    contact = Contact(
        id=f"google_{resource_name}",
        full_name=full_name,
        given_name=given_name,
        family_name=family_name,
        emails=email_addrs,
        primary_email=primary_email_obj,
        company=company,
        job_title=job_title,
        phones=phones,
        photo_url=photo_url,
        provider=Provider.GOOGLE,
        provider_contact_id=str(resource_name or ""),
        account_email=account_email,
        account_name=account_name,
    )
    return contact.model_dump()


def normalize_microsoft_contact(
    raw: Dict[str, Any], account_email: str, account_name: Optional[str] = None
) -> Dict[str, Any]:
    """Normalize a Microsoft Graph contact into unified Contact dict."""
    contact_id = raw.get("id")
    full_name = raw.get("displayName")
    given_name = raw.get("givenName")
    family_name = raw.get("surname")

    email_addrs: List[EmailAddress] = []
    primary_email_obj = None
    for e in raw.get("emailAddresses", []) or []:
        addr = e.get("address")
        if not addr:
            continue
        name = e.get("name")
        email_model = EmailAddress(email=addr, name=name)
        email_addrs.append(email_model)
        if primary_email_obj is None:
            primary_email_obj = email_model

    company = raw.get("companyName") or _derive_company_from_email(
        primary_email_obj.email if primary_email_obj else None
    )
    job_title = raw.get("jobTitle")

    phones: List[ContactPhone] = []
    for number in raw.get("businessPhones") or []:
        if isinstance(number, str) and number:
            phones.append(ContactPhone(type="work", number=number))
    mobile_phone = raw.get("mobilePhone")
    if isinstance(mobile_phone, str) and mobile_phone:
        phones.append(ContactPhone(type="mobile", number=mobile_phone))
    for number in raw.get("homePhones") or []:
        if isinstance(number, str) and number:
            phones.append(ContactPhone(type="home", number=number))

    photo_url = None  # Could fetch via separate /photo endpoint if needed

    contact = Contact(
        id=f"outlook_{contact_id}",
        full_name=full_name,
        given_name=given_name,
        family_name=family_name,
        emails=email_addrs,
        primary_email=primary_email_obj,
        company=company,
        job_title=job_title,
        phones=phones,
        photo_url=photo_url,
        provider=Provider.MICROSOFT,
        provider_contact_id=contact_id or "",
        account_email=account_email,
        account_name=account_name,
    )
    return contact.model_dump()
