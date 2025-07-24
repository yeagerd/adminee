import requests
from typing import List, Dict, Any

class MicrosoftGraphClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"

    def fetch_emails_from_notification(self, notification: Dict[str, Any]) -> List[Dict[str, Any]]:
        # This is a stub; real implementation will call Microsoft Graph API
        # Example: GET /me/messages/{id} or /users/{user_id}/messages/{id}
        return [] 