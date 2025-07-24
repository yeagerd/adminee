import os
import time
from typing import List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GmailAPIClient:
    def __init__(self, access_token: str, refresh_token: str, client_id: str, client_secret: str, token_uri: str):
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri=token_uri,
        )
        self.service = build("gmail", "v1", credentials=self.creds)

    def fetch_emails_since_history_id(self, user_id: str, history_id: str, max_retries: int = 5) -> List[Dict[str, Any]]:
        backoff = 1
        for attempt in range(max_retries):
            try:
                # TODO: Real implementation: call Gmail API
                # Example:
                # result = self.service.users().history().list(userId=user_id, startHistoryId=history_id).execute()
                # return result.get("messages", [])
                return []
            except HttpError as e:
                if e.resp.status in [429, 500, 503]:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                elif e.resp.status == 401:
                    # TODO: Attempt token refresh
                    raise
                else:
                    raise
        raise Exception("Max retries exceeded for Gmail API fetch") 