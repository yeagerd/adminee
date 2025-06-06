import requests
from typing import Any, Dict, Optional
from langchain.tools import BaseTool

class CalendarTool(BaseTool):
    name = "calendar_tool"
    description = "Retrieve calendar events from office-service via REST API."

    def __init__(self, office_service_url: str):
        self.office_service_url = office_service_url

    def _run(self, user_token: str, start_date: Optional[str] = None, end_date: Optional[str] = None, user_timezone: Optional[str] = None, provider_type: Optional[str] = None) -> Dict[str, Any]:
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
            response = requests.get(f"{self.office_service_url}/events", headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Validate response structure
            if "events" not in data:
                return {"error": "Malformed response from office-service."}
            return {"events": data["events"]}  # Suitable for LLM context and tool command schema
        except requests.Timeout:
            return {"error": "Request to office-service timed out."}
        except requests.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async not implemented for CalendarTool.")
