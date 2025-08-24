"""
Type definitions for the Vespa Loader service
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentIngestionResult(BaseModel):
    """Result of document ingestion operation"""

    status: str = Field(..., description="Ingestion status (success/failure)")
    document_id: str = Field(..., description="ID of the ingested document")
    vespa_result: Any = Field(
        ..., description="Raw result from Vespa indexing operation"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp of ingestion completion",
    )


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
            "doc_id": self.id,  # Map 'id' to 'doc_id' for Vespa schema
            "user_id": self.user_id,
            "source_type": self.type,  # Map 'type' to 'source_type' for Vespa schema
            "provider": self.provider,
            "title": self.subject,  # Map 'subject' to 'title' for Vespa schema
            "content": self.body,  # Map 'body' to 'content' for Vespa schema
            "sender": self.from_address,  # Map 'from_address' to 'sender' for Vespa schema
            "recipients": self.to_addresses,  # Map 'to_addresses' to 'recipients' for Vespa schema
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
