import time
from typing import Any, Dict, List

import requests


class MicrosoftGraphClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"

    def fetch_emails_from_notification(
        self, notification: Dict[str, Any], max_retries: int = 5
    ) -> List[Dict[str, Any]]:
        backoff = 1
        for attempt in range(max_retries):
            try:
                # TODO: Real implementation: call Microsoft Graph API
                # Example: GET /me/messages/{id} or /users/{user_id}/messages/{id}
                # resp = requests.get(...)
                # if resp.status_code == 401: ...
                # return resp.json().get("value", [])
                return []
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status in [429, 500, 503]:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                elif status == 401:
                    # TODO: Attempt token refresh
                    raise
                else:
                    raise
        raise Exception("Max retries exceeded for Microsoft Graph API fetch")
