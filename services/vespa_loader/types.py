"""
Type definitions for the Vespa Loader service
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class VespaDocumentType:
    """Typed document structure for Vespa ingestion"""
    id: str
    user_id: str
    type: str
    provider: str
    subject: str
    body: str
    from_address: str
    to_addresses: List[str]
    thread_id: Optional[str] = None
    folder: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    content_chunks: Optional[List[str]] = None
    quoted_content: Optional[str] = None
    thread_summary: Optional[Dict[str, Any]] = None
    search_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by Vespa"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "provider": self.provider,
            "subject": self.subject,
            "body": self.body,
            "from": self.from_address,
            "to": self.to_addresses,
            "thread_id": self.thread_id or "",
            "folder": self.folder or "",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata or {},
            "content_chunks": self.content_chunks or [],
            "quoted_content": self.quoted_content or "",
            "thread_summary": self.thread_summary or {},
            "search_text": self.search_text or "",
        }
