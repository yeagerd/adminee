import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GmailAPIClient:
    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        token_uri: str,
    ):
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri=token_uri,
        )
        self.service = build("gmail", "v1", credentials=self.creds)

    def fetch_emails_since_history_id(
        self, user_id: str, history_id: str, max_retries: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails that have changed since the given history ID.
        
        Args:
            user_id: Gmail user ID (usually 'me')
            history_id: The history ID to start from
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of email objects with metadata and content
        """
        backoff = 1
        for attempt in range(max_retries):
            try:
                # Get history of changes since the given history ID
                history_result = self.service.users().history().list(
                    userId=user_id,
                    startHistoryId=history_id,
                    historyTypes=['messageAdded', 'messageDeleted', 'labelAdded', 'labelRemoved']
                ).execute()
                
                # Extract message IDs from history
                message_ids = set()
                for history in history_result.get('history', []):
                    # Add messages that were added
                    for message in history.get('messagesAdded', []):
                        message_ids.add(message['message']['id'])
                    
                    # Add messages that had labels added (might be new messages)
                    for message in history.get('labelsAdded', []):
                        message_ids.add(message['message']['id'])
                
                if not message_ids:
                    return []
                
                # Fetch full email details for each message ID
                emails = []
                for msg_id in message_ids:
                    try:
                        email = self._fetch_email_details(user_id, msg_id)
                        if email:
                            emails.append(email)
                    except Exception as e:
                        # Log error but continue with other emails
                        print(f"Error fetching email {msg_id}: {e}")
                        continue
                
                return emails
                
            except HttpError as e:
                if e.resp.status in [429, 500, 503]:
                    print(f"Rate limit/server error, retrying in {backoff}s: {e}")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                elif e.resp.status == 401:
                    # TODO: Attempt token refresh
                    print(f"Authentication error: {e}")
                    raise
                else:
                    print(f"HTTP error: {e}")
                    raise
            except Exception as e:
                print(f"Unexpected error: {e}")
                raise
                
        raise Exception("Max retries exceeded for Gmail API fetch")

    def _fetch_email_details(self, user_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed email information including headers and body.
        
        Args:
            user_id: Gmail user ID
            message_id: Gmail message ID
            
        Returns:
            Email object with metadata and content, or None if not found
        """
        try:
            # Get the full message
            message = self.service.users().messages().get(
                userId=user_id,
                id=message_id,
                format='full'  # Get full message with body
            ).execute()
            
            # Extract email data
            email_data = {
                'id': message['id'],
                'threadId': message['threadId'],
                'labelIds': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'internalDate': message.get('internalDate'),
                'from': '',
                'to': '',
                'subject': '',
                'body': '',
                'provider': 'gmail'
            }
            
            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                if name == 'from':
                    email_data['from'] = value
                elif name == 'to':
                    email_data['to'] = value
                elif name == 'subject':
                    email_data['subject'] = value
            
            # Extract body content
            email_data['body'] = self._extract_email_body(message.get('payload', {}))
            
            return email_data
            
        except HttpError as e:
            if e.resp.status == 404:
                # Message not found (might have been deleted)
                return None
            else:
                raise
        except Exception as e:
            print(f"Error fetching email details for {message_id}: {e}")
            return None

    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract email body content from Gmail message payload.
        
        Args:
            payload: Gmail message payload
            
        Returns:
            Email body as text
        """
        body = ""
        
        # Handle multipart messages
        if payload.get('mimeType') == 'multipart/alternative' or payload.get('mimeType') == 'multipart/mixed':
            parts = payload.get('parts', [])
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    # Prefer plain text
                    body = self._decode_body(part.get('body', {}))
                    break
                elif part.get('mimeType') == 'text/html' and not body:
                    # Fall back to HTML if no plain text
                    body = self._decode_body(part.get('body', {}))
        else:
            # Single part message
            body = self._decode_body(payload.get('body', {}))
        
        return body

    def _decode_body(self, body_data: Dict[str, Any]) -> str:
        """
        Decode email body data.
        
        Args:
            body_data: Gmail body data with encoding information
            
        Returns:
            Decoded body content
        """
        import base64
        
        data = body_data.get('data', '')
        if not data:
            return ""
        
        # Gmail uses URL-safe base64 encoding
        try:
            decoded = base64.urlsafe_b64decode(data)
            return decoded.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error decoding body: {e}")
            return ""

    def get_latest_history_id(self, user_id: str = 'me') -> Optional[str]:
        """
        Get the latest history ID for the user.
        
        Args:
            user_id: Gmail user ID (defaults to 'me')
            
        Returns:
            Latest history ID, or None if error
        """
        try:
            # Get profile to get the latest history ID
            profile = self.service.users().getProfile(userId=user_id).execute()
            return profile.get('historyId')
        except Exception as e:
            print(f"Error getting latest history ID: {e}")
            return None

    def get_email_count(self, user_id: str = 'me') -> int:
        """
        Get the total number of emails for the user.
        
        Args:
            user_id: Gmail user ID (defaults to 'me')
            
        Returns:
            Total email count
        """
        try:
            # Get profile to get email count
            profile = self.service.users().getProfile(userId=user_id).execute()
            return profile.get('messagesTotal', 0)
        except Exception as e:
            print(f"Error getting email count: {e}")
            return 0
