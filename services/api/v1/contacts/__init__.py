"""
Contact schemas for API requests and responses.

Moved from services/contacts/schemas/ to services/api/v1/contacts/
for shared usage across services.
"""

from services.api.v1.contacts.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactSearchRequest,
    ContactStatsResponse,
    EmailContactSearchResult,
    EmailContactUpdate,
)

__all__ = [
    "ContactCreate",
    "ContactListResponse",
    "ContactResponse",
    "ContactSearchRequest",
    "ContactStatsResponse",
    "EmailContactSearchResult",
    "EmailContactUpdate",
]
