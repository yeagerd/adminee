from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

# Re-defining Provider enum for clarity, same as in common_schemas.py
class Provider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"

class ApiError(BaseModel):
    type: str  # "validation_error", "auth_error", "provider_error", etc.
    message: str
    details: Optional[Dict[str, Any]] = None
    provider: Optional[Provider] = None
    retry_after: Optional[int] = None  # seconds
    # request_id will be added by a middleware or decorator ideally
    request_id: Optional[str] = None
