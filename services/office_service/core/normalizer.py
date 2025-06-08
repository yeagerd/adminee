import logging
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import EmailStr, ValidationError

from schemas.common_schemas import EmailMessage, EmailAddress, CalendarEvent, DriveFile, Provider

logger = logging.getLogger(__name__)

def _parse_email_string(email_header: Optional[str]) -> Optional[EmailAddress]:
    if not email_header:
        return None
    try:
        if '<' in email_header and '>' in email_header:
            name_part = email_header.split('<')[0].strip()
            email_part = email_header.split('<')[1].split('>')[0].strip()
            return EmailAddress(name=name_part if name_part else None, email=email_part)
        return EmailAddress(email=email_header.strip())
    except ValidationError:
        logger.warning(f"Could not parse email string: {email_header}", exc_info=True)
        return None

def _parse_microsoft_email_recipients(recipient_list: Optional[List[Dict[str, Any]]]) -> List[EmailAddress]:
    parsed_list = []
    if not recipient_list:
        return parsed_list
    for entry in recipient_list:
        if isinstance(entry, dict) and 'emailAddress' in entry and isinstance(entry['emailAddress'], dict):
            email_addr_info = entry['emailAddress']
            try:
                email_str = email_addr_info.get('address')
                if email_str:
                    parsed_list.append(EmailAddress(
                        email=email_str,
                        name=email_addr_info.get('name')
                    ))
            except ValidationError:
                logger.warning(f"Could not parse Microsoft recipient entry: {entry}", exc_info=True)
    return parsed_list

def _parse_google_email_participants(headers: List[Dict[str, str]], header_name: str) -> List[EmailAddress]:
    parsed_list = []
    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            participants_str = header.get("value", "")
            for part_str in participants_str.split(','):
                if part_str.strip():
                    parsed = _parse_email_string(part_str.strip())
                    if parsed:
                        parsed_list.append(parsed)
            break
    return parsed_list

def normalize_google_email(
    raw_email: Dict[str, Any], account_email: EmailStr, account_name: Optional[str] = None
) -> Optional[EmailMessage]:
    try:
        payload = raw_email.get("payload", {})
        headers = payload.get("headers", [])

        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), None)
        from_str = next((h["value"] for h in headers if h["name"].lower() == "from"), None)

        date_str = next((h["value"] for h in headers if h["name"].lower() == "date"), None)
        email_date = datetime.now(timezone.utc)
        if date_str:
            try:
                # Handle cases like "Thu, 29 Feb 2024 10:30:00 -0800 (PST)"
                email_date = datetime.strptime(date_str.split(' (')[0].strip(), '%d %b %Y %H:%M:%S %z')
            except ValueError:
                try:
                    # Handle cases like "29 Feb 2024 10:30:00 -0800" or "Thu, 29 Feb 2024 10:30:00 +0000"
                    email_date = datetime.strptime(date_str.split(' (')[0].strip(), '%a, %d %b %Y %H:%M:%S %z')
                except ValueError:
                    logger.warning(f"Could not parse date string: {date_str} for email {raw_email.get('id')}")
                    internal_date_ms = raw_email.get("internalDate")
                    if internal_date_ms:
                        try:
                            email_date = datetime.fromtimestamp(int(internal_date_ms) / 1000, timezone.utc)
                        except ValueError:
                            logger.error(f"Could not parse internalDate: {internal_date_ms}")

        body_text = None
        body_html = None
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "").lower()
                if "data" in part.get("body", {}):
                    try:
                        decoded_data = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                        if mime_type == "text/plain":
                            body_text = decoded_data
                        elif mime_type == "text/html":
                            body_html = decoded_data
                    except Exception as e:
                        logger.warning(f"Error decoding part data for email {raw_email.get('id')}: {e}")
                if body_text and body_html: break
        elif "body" in payload and "data" in payload["body"]:
            try:
                decoded_body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
                if "text/html" in payload.get("mimeType", "").lower():
                    body_html = decoded_body
                else:
                    body_text = decoded_body
            except Exception as e:
                 logger.warning(f"Error decoding main body data for email {raw_email.get('id')}: {e}")

        has_attachments = False
        if "parts" in payload:
            for part in payload.get("parts", []):
                if part.get("filename"): # Attachments usually have a filename
                    has_attachments = True
                    break

        return EmailMessage(
            id=f"google_{raw_email['id']}",
            provider_message_id=raw_email["id"],
            thread_id=raw_email.get("threadId"),
            subject=subject,
            snippet=raw_email.get("snippet"),
            body_text=body_text,
            body_html=body_html,
            from_address=_parse_email_string(from_str),
            to_addresses=_parse_google_email_participants(headers, "To"),
            cc_addresses=_parse_google_email_participants(headers, "Cc"),
            bcc_addresses=_parse_google_email_participants(headers, "Bcc"),
            date=email_date,
            labels=raw_email.get("labelIds", []),
            is_read="UNREAD" not in raw_email.get("labelIds", []),
            has_attachments=has_attachments,
            provider=Provider.GOOGLE,
            account_email=account_email,
            account_name=account_name,
        )
    except Exception as e:
        logger.error(f"Error normalizing Google email (ID: {raw_email.get('id')}): {e}", exc_info=True)
        return None

def normalize_microsoft_email(
    raw_email: Dict[str, Any], account_email: EmailStr, account_name: Optional[str] = None
) -> Optional[EmailMessage]:
    try:
        received_dt_str = raw_email.get("receivedDateTime")
        email_date = datetime.now(timezone.utc)
        if received_dt_str:
            try:
                email_date = datetime.fromisoformat(received_dt_str.replace("Z", "+00:00"))
            except ValueError:
                 logger.warning(f"Could not parse date string: {received_dt_str} for MS email {raw_email.get('id')}")

        body_preview = raw_email.get("bodyPreview")
        body_data = raw_email.get("body", {})
        body_content_type = body_data.get("contentType", "text").lower()
        body_text = None
        body_html = None

        if body_content_type == "html":
            body_html = body_data.get("content")
            if not body_text and body_preview: body_text = body_preview
        else: # Plain text
            body_text = body_data.get("content")

        from_field = raw_email.get("from")
        if not from_field: from_field = raw_email.get("sender") # Fallback to sender if 'from' is not present

        return EmailMessage(
            id=f"microsoft_{raw_email['id']}",
            provider_message_id=raw_email["id"],
            thread_id=raw_email.get("conversationId"),
            subject=raw_email.get("subject"),
            snippet=body_preview,
            body_text=body_text,
            body_html=body_html,
            from_address=_parse_microsoft_email_recipients([from_field])[0] if from_field else None,
            to_addresses=_parse_microsoft_email_recipients(raw_email.get("toRecipients")),
            cc_addresses=_parse_microsoft_email_recipients(raw_email.get("ccRecipients")),
            bcc_addresses=_parse_microsoft_email_recipients(raw_email.get("bccRecipients")),
            date=email_date,
            labels=raw_email.get("categories", []),
            is_read=raw_email.get("isRead", False),
            has_attachments=raw_email.get("hasAttachments", False),
            provider=Provider.MICROSOFT,
            account_email=account_email,
            account_name=account_name,
        )
    except Exception as e:
        logger.error(f"Error normalizing Microsoft email (ID: {raw_email.get('id')}): {e}", exc_info=True)
        return None

def normalize_google_calendar_event(
    raw_event: Dict[str, Any],
    account_email: EmailStr,
    calendar_id: str, # Unified calendar ID this event belongs to
    calendar_name: str,
    account_name: Optional[str] = None,
) -> Optional[CalendarEvent]:
    logger.debug(f"Normalizing Google Calendar event ID: {raw_event.get('id')} for account: {account_email}")
    try:
        start_obj = raw_event.get("start", {})
        end_obj = raw_event.get("end", {})
        start_time_str = start_obj.get("dateTime", start_obj.get("date"))
        end_time_str = end_obj.get("dateTime", end_obj.get("date"))

        if not start_time_str or not end_time_str:
            logger.error(f"Missing start or end time for Google event: {raw_event.get('id')}")
            return None

        all_day = "date" in start_obj # If "date" is present, it's an all-day event, no specific time.
        if all_day:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_time = datetime.strptime(end_time_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        else:
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

        attendees = []
        if raw_event.get("attendees"):
            for att in raw_event["attendees"]:
                if att.get("email"):
                    try:
                        attendees.append(EmailAddress(email=att["email"], name=att.get("displayName", att.get("email"))))
                    except ValidationError:
                         logger.warning(f"Invalid attendee email: {att.get('email')} in event {raw_event.get('id')}")

        organizer_info = raw_event.get("organizer")
        organizer = None
        if organizer_info and organizer_info.get("email"):
             try:
                organizer = EmailAddress(email=organizer_info["email"], name=organizer_info.get("displayName", organizer_info.get("email")))
             except ValidationError:
                logger.warning(f"Invalid organizer email: {organizer_info.get('email')} in event {raw_event.get('id')}")

        created_time_str = raw_event.get("created")
        updated_time_str = raw_event.get("updated")
        created_at = datetime.fromisoformat(created_time_str.replace("Z", "+00:00")) if created_time_str else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(updated_time_str.replace("Z", "+00:00")) if updated_time_str else datetime.now(timezone.utc)

        return CalendarEvent(
            id=f"google_{raw_event['id']}",
            provider_event_id=raw_event['id'],
            calendar_id=calendar_id, # Use the passed unified calendar ID
            title=raw_event.get("summary", "No Title"),
            description=raw_event.get("description"),
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            location=raw_event.get("location"),
            attendees=attendees,
            organizer=organizer,
            status=raw_event.get("status", "confirmed").lower(),
            visibility=raw_event.get("visibility", "default").lower(),
            provider=Provider.GOOGLE,
            account_email=account_email,
            account_name=account_name,
            calendar_name=calendar_name,
            created_at=created_at,
            updated_at=updated_at,
        )
    except Exception as e:
        logger.error(f"Error normalizing Google Calendar event (ID: {raw_event.get('id')}): {e}", exc_info=True)
        return None

def normalize_google_drive_file(
    raw_file: Dict[str, Any], account_email: EmailStr, account_name: Optional[str] = None
) -> Optional[DriveFile]:
    logger.debug(f"Normalizing Google Drive file ID: {raw_file.get('id')} for account: {account_email}")
    try:
        created_time_str = raw_file.get("createdTime")
        modified_time_str = raw_file.get("modifiedTime")
        created_time = datetime.fromisoformat(created_time_str.replace("Z", "+00:00")) if created_time_str else datetime.now(timezone.utc)
        modified_time = datetime.fromisoformat(modified_time_str.replace("Z", "+00:00")) if modified_time_str else datetime.now(timezone.utc)

        is_folder = raw_file.get("mimeType") == "application/vnd.google-apps.folder"
        parent_folder_id = None
        if raw_file.get("parents") and len(raw_file["parents"]) > 0:
            parent_folder_id = f"google_{raw_file['parents'][0]}"

        return DriveFile(
            id=f"google_{raw_file['id']}",
            provider_file_id=raw_file['id'],
            name=raw_file.get("name", "Untitled"),
            mime_type=raw_file.get("mimeType", "application/octet-stream"),
            size=int(raw_file["size"]) if raw_file.get("size") else None,
            created_time=created_time,
            modified_time=modified_time,
            web_view_link=raw_file.get("webViewLink"),
            download_link=raw_file.get("webContentLink"),
            thumbnail_link=raw_file.get("thumbnailLink"),
            parent_folder_id=parent_folder_id,
            is_folder=is_folder,
            provider=Provider.GOOGLE,
            account_email=account_email,
            account_name=account_name,
        )
    except Exception as e:
        logger.error(f"Error normalizing Google Drive file (ID: {raw_file.get('id')}): {e}", exc_info=True)
        return None

def normalize_microsoft_calendar_event(
    raw_event: Dict[str, Any],
    account_email: EmailStr,
    calendar_id: str, # Unified calendar ID
    calendar_name: str,
    account_name: Optional[str] = None,
) -> Optional[CalendarEvent]:
    logger.debug(f"Normalizing Microsoft Calendar event ID: {raw_event.get('id')} for account: {account_email}")
    try:
        start_obj = raw_event.get("start", {})
        end_obj = raw_event.get("end", {})

        start_time_str = start_obj.get("dateTime")
        end_time_str = end_obj.get("dateTime")

        if not start_time_str or not end_time_str:
            logger.error(f"Missing start or end dateTime for Microsoft event: {raw_event.get('id')}")
            return None

        # MS Graph times are typically ISO 8601. Pydantic handles this.
        # Timezones are specified in start/end objects if not UTC.
        # For simplicity, assume they are parsed correctly by fromisoformat if they include TZ info,
        # or are UTC if they end in 'Z'.
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

        all_day = raw_event.get("isAllDay", False)

        attendees = []
        if raw_event.get("attendees"):
            for att in raw_event["attendees"]:
                email_addr_info = att.get("emailAddress", {})
                if email_addr_info.get("address"):
                    try:
                        attendees.append(EmailAddress(email=email_addr_info["address"], name=email_addr_info.get("name")))
                    except ValidationError:
                        logger.warning(f"Invalid attendee email: {email_addr_info.get('address')} in MS event {raw_event.get('id')}")

        organizer_info = raw_event.get("organizer", {}).get("emailAddress", {})
        organizer = None
        if organizer_info.get("address"):
            try:
                organizer = EmailAddress(email=organizer_info["address"], name=organizer_info.get("name"))
            except ValidationError:
                logger.warning(f"Invalid organizer email: {organizer_info.get('address')} in MS event {raw_event.get('id')}")

        created_time_str = raw_event.get("createdDateTime")
        updated_time_str = raw_event.get("lastModifiedDateTime")
        created_at = datetime.fromisoformat(created_time_str.replace("Z", "+00:00")) if created_time_str else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(updated_time_str.replace("Z", "+00:00")) if updated_time_str else datetime.now(timezone.utc)

        # Mapping 'showAs' to a simple status; could be more nuanced
        raw_status = raw_event.get("showAs", "busy").lower()
        status_map = {
            "free": "free",
            "tentative": "tentative",
            "busy": "confirmed", # Assuming busy means confirmed for our model
            "oof": "confirmed", # Out of office typically means confirmed absence
            "workingelsewhere": "confirmed",
            "unknown": "tentative",
        }
        event_status = status_map.get(raw_status, "tentative")

        # Mapping 'sensitivity' to visibility
        raw_visibility = raw_event.get("sensitivity", "normal").lower()
        visibility_map = {
            "normal": "default",
            "personal": "private",
            "private": "private",
            "confidential": "private",
        }
        event_visibility = visibility_map.get(raw_visibility, "default")

        return CalendarEvent(
            id=f"microsoft_{raw_event['id']}",
            provider_event_id=raw_event['id'],
            calendar_id=calendar_id,
            title=raw_event.get("subject", "No Title"),
            description=raw_event.get("bodyPreview"),
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            location=raw_event.get("location", {}).get("displayName"),
            attendees=attendees,
            organizer=organizer,
            status=event_status,
            visibility=event_visibility,
            provider=Provider.MICROSOFT,
            account_email=account_email,
            account_name=account_name,
            calendar_name=calendar_name,
            created_at=created_at,
            updated_at=updated_at,
        )
    except Exception as e:
        logger.error(f"Error normalizing Microsoft Calendar event (ID: {raw_event.get('id')}): {e}", exc_info=True)
        return None


def normalize_microsoft_drive_file(
    raw_file: Dict[str, Any], account_email: EmailStr, account_name: Optional[str] = None
) -> Optional[DriveFile]:
    logger.debug(f"Normalizing Microsoft Drive file ID: {raw_file.get('id')} for account: {account_email}")
    try:
        created_time_str = raw_file.get("createdDateTime")
        modified_time_str = raw_file.get("lastModifiedDateTime")
        created_time = datetime.fromisoformat(created_time_str.replace("Z", "+00:00")) if created_time_str else datetime.now(timezone.utc)
        modified_time = datetime.fromisoformat(modified_time_str.replace("Z", "+00:00")) if modified_time_str else datetime.now(timezone.utc)

        is_folder = "folder" in raw_file
        parent_folder_id = None
        if raw_file.get("parentReference") and raw_file["parentReference"].get("id"):
            parent_folder_id = f"microsoft_{raw_file['parentReference']['id']}"

        mime_type = "application/vnd.microsoft-folder" if is_folder else raw_file.get("file", {}).get("mimeType", "application/octet-stream")

        return DriveFile(
            id=f"microsoft_{raw_file['id']}",
            provider_file_id=raw_file['id'],
            name=raw_file.get("name", "Untitled"),
            mime_type=mime_type,
            size=raw_file.get("size"),
            created_time=created_time,
            modified_time=modified_time,
            web_view_link=raw_file.get("webUrl"),
            download_link=raw_file.get("@microsoft.graph.downloadUrl"),
            thumbnail_link=None,
            parent_folder_id=parent_folder_id,
            is_folder=is_folder,
            provider=Provider.MICROSOFT,
            account_email=account_email,
            account_name=account_name,
        )
    except Exception as e:
        logger.error(f"Error normalizing Microsoft Drive file (ID: {raw_file.get('id')}): {e}", exc_info=True)
        return None
