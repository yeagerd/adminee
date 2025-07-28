import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


class MicrosoftGraphClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"

    def fetch_emails_from_notification(
        self, notification: Dict[str, Any], max_retries: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from Microsoft Graph based on change notification.
        
        Args:
            notification: Microsoft Graph change notification
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of email objects with metadata and content
        """
        emails = []
        
        # Process each change in the notification
        for change in notification.get('value', []):
            change_type = change.get('changeType')
            resource = change.get('resource')
            
            # Only process created and updated emails
            if change_type in ['created', 'updated'] and resource:
                try:
                    email = self._fetch_email_by_resource(resource, max_retries)
                    if email:
                        emails.append(email)
                except Exception as e:
                    print(f"Error fetching email from resource {resource}: {e}")
                    continue
        
        return emails

    def _fetch_email_by_resource(self, resource: str, max_retries: int = 5) -> Optional[Dict[str, Any]]:
        """
        Fetch email details by resource URL.
        
        Args:
            resource: Microsoft Graph resource URL
            max_retries: Maximum number of retry attempts
            
        Returns:
            Email object with metadata and content, or None if not found
        """
        backoff = 1
        for attempt in range(max_retries):
            try:
                # Extract message ID from resource URL
                # Resource format: /me/messages/{id} or /users/{user_id}/messages/{id}
                if '/messages/' in resource:
                    message_id = resource.split('/messages/')[-1]
                    return self._fetch_email_by_id(message_id)
                else:
                    print(f"Unexpected resource format: {resource}")
                    return None
                    
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status in [429, 500, 503]:
                    print(f"Rate limit/server error, retrying in {backoff}s: {e}")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                elif status == 401:
                    # TODO: Attempt token refresh
                    print(f"Authentication error: {e}")
                    raise
                elif status == 404:
                    # Message not found (might have been deleted)
                    return None
                else:
                    print(f"HTTP error: {e}")
                    raise
            except Exception as e:
                print(f"Unexpected error: {e}")
                raise
                
        raise Exception("Max retries exceeded for Microsoft Graph API fetch")

    def _fetch_email_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch email details by message ID.
        
        Args:
            message_id: Microsoft Graph message ID
            
        Returns:
            Email object with metadata and content, or None if not found
        """
        try:
            # Get the full message with body
            url = f"{self.base_url}/me/messages/{message_id}"
            params = {
                '$select': 'id,subject,from,toRecipients,receivedDateTime,body,bodyPreview,importance,isRead,hasAttachments',
                '$expand': 'attachments'
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            message = response.json()
            
            # Extract email data
            email_data = {
                'id': message['id'],
                'subject': message.get('subject', ''),
                'from': self._extract_email_address(message.get('from', {})),
                'to': self._extract_email_addresses(message.get('toRecipients', [])),
                'receivedDateTime': message.get('receivedDateTime'),
                'body': self._extract_email_body(message.get('body', {})),
                'bodyPreview': message.get('bodyPreview', ''),
                'importance': message.get('importance', 'normal'),
                'isRead': message.get('isRead', False),
                'hasAttachments': message.get('hasAttachments', False),
                'provider': 'microsoft'
            }
            
            return email_data
            
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # Message not found
                return None
            else:
                raise
        except Exception as e:
            print(f"Error fetching email details for {message_id}: {e}")
            return None

    def _extract_email_address(self, address_obj: Dict[str, Any]) -> str:
        """
        Extract email address from Microsoft Graph address object.
        
        Args:
            address_obj: Microsoft Graph address object
            
        Returns:
            Email address string
        """
        if isinstance(address_obj, dict):
            return address_obj.get('emailAddress', {}).get('address', '')
        return str(address_obj) if address_obj else ''

    def _extract_email_addresses(self, address_objs: List[Dict[str, Any]]) -> str:
        """
        Extract email addresses from list of Microsoft Graph address objects.
        
        Args:
            address_objs: List of Microsoft Graph address objects
            
        Returns:
            Comma-separated email addresses
        """
        addresses = []
        for addr_obj in address_objs:
            addr = self._extract_email_address(addr_obj)
            if addr:
                addresses.append(addr)
        return ', '.join(addresses)

    def _extract_email_body(self, body_obj: Dict[str, Any]) -> str:
        """
        Extract email body content from Microsoft Graph body object.
        
        Args:
            body_obj: Microsoft Graph body object
            
        Returns:
            Email body as text
        """
        if not body_obj:
            return ""
        
        content_type = body_obj.get('contentType', 'text')
        content = body_obj.get('content', '')
        
        if content_type == 'html':
            # For HTML content, we might want to strip HTML tags
            # For now, return as-is
            return content
        else:
            # Plain text
            return content

    def get_delta_emails(self, delta_link: Optional[str] = None, max_retries: int = 5) -> Dict[str, Any]:
        """
        Get emails using delta query for incremental sync.
        
        Args:
            delta_link: Previous delta link for incremental sync
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with emails and next delta link
        """
        backoff = 1
        for attempt in range(max_retries):
            try:
                if delta_link:
                    # Use existing delta link for incremental sync
                    url = delta_link
                else:
                    # Start new delta query
                    url = f"{self.base_url}/me/messages/delta"
                
                params = {
                    '$select': 'id,subject,from,toRecipients,receivedDateTime,body,bodyPreview,importance,isRead,hasAttachments',
                    '$expand': 'attachments',
                    '$top': 50  # Limit batch size
                }
                
                headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                result = response.json()
                
                # Extract emails
                emails = []
                for item in result.get('value', []):
                    if '@odata.type' in item and item['@odata.type'] == '#microsoft.graph.message':
                        email_data = {
                            'id': item['id'],
                            'subject': item.get('subject', ''),
                            'from': self._extract_email_address(item.get('from', {})),
                            'to': self._extract_email_addresses(item.get('toRecipients', [])),
                            'receivedDateTime': item.get('receivedDateTime'),
                            'body': self._extract_email_body(item.get('body', {})),
                            'bodyPreview': item.get('bodyPreview', ''),
                            'importance': item.get('importance', 'normal'),
                            'isRead': item.get('isRead', False),
                            'hasAttachments': item.get('hasAttachments', False),
                            'provider': 'microsoft'
                        }
                        emails.append(email_data)
                
                return {
                    'emails': emails,
                    'next_link': result.get('@odata.nextLink'),
                    'delta_link': result.get('@odata.deltaLink')
                }
                
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status in [429, 500, 503]:
                    print(f"Rate limit/server error, retrying in {backoff}s: {e}")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                elif status == 401:
                    # TODO: Attempt token refresh
                    print(f"Authentication error: {e}")
                    raise
                else:
                    print(f"HTTP error: {e}")
                    raise
            except Exception as e:
                print(f"Unexpected error: {e}")
                raise
                
        raise Exception("Max retries exceeded for Microsoft Graph delta query")

    def get_email_count(self) -> int:
        """
        Get the total number of emails for the user.
        
        Returns:
            Total email count
        """
        try:
            url = f"{self.base_url}/me/messages/$count"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            return int(response.text)
        except Exception as e:
            print(f"Error getting email count: {e}")
            return 0
