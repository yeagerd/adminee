"""
Document event models for PubSub messages.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base_events import BaseEvent


class DocumentData(BaseModel):
    """Base document data structure."""

    id: str = Field(..., description="Unique document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content")
    content_type: str = Field(..., description="Document type (word, sheet, presentation)")
    provider: str = Field(..., description="Document provider (google, microsoft, etc.)")
    provider_document_id: str = Field(..., description="Provider's internal document ID")
    owner_email: str = Field(..., description="Document owner's email")
    permissions: List[str] = Field(
        default_factory=list, description="Document permissions"
    )
    tags: List[str] = Field(default_factory=list, description="Document tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional document metadata"
    )


class WordDocumentData(DocumentData):
    """Word document specific data."""

    content_type: str = Field(default="word", description="Document type")
    word_count: Optional[int] = Field(None, description="Word count")
    page_count: Optional[int] = Field(None, description="Page count")
    language: Optional[str] = Field(None, description="Document language")
    template: Optional[str] = Field(None, description="Document template used")


class SheetDocumentData(DocumentData):
    """Sheet document specific data."""

    content_type: str = Field(default="sheet", description="Document type")
    row_count: Optional[int] = Field(None, description="Number of rows")
    column_count: Optional[int] = Field(None, description="Number of columns")
    sheet_count: Optional[int] = Field(None, description="Number of sheets")
    formulas: List[str] = Field(default_factory=list, description="Formulas in the sheet")


class PresentationDocumentData(DocumentData):
    """Presentation document specific data."""

    content_type: str = Field(default="presentation", description="Document type")
    slide_count: Optional[int] = Field(None, description="Number of slides")
    theme: Optional[str] = Field(None, description="Presentation theme")
    transition_effects: List[str] = Field(
        default_factory=list, description="Transition effects used"
    )


class DocumentEvent(BaseEvent):
    """Event for document operations (create, update, delete)."""

    user_id: str = Field(..., description="User ID for the document operation")
    document: DocumentData = Field(..., description="Document data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(None, description="Batch identifier for batch operations")
    last_updated: datetime = Field(..., description="When the document was last updated")
    sync_timestamp: datetime = Field(..., description="When the data was last synced from provider")
    provider: str = Field(..., description="Document provider (google, microsoft, etc.)")
    content_type: str = Field(..., description="Document type (word, sheet, presentation)")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"


class DocumentFragmentData(BaseModel):
    """Document fragment data for chunked documents."""

    id: str = Field(..., description="Unique fragment ID")
    document_id: str = Field(..., description="Parent document ID")
    content: str = Field(..., description="Fragment content")
    fragment_type: str = Field(..., description="Fragment type (section, page, chunk)")
    sequence_number: int = Field(..., description="Fragment sequence in document")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Fragment metadata"
    )


class DocumentFragmentEvent(BaseEvent):
    """Event for document fragment operations."""

    user_id: str = Field(..., description="User ID for the fragment operation")
    fragment: DocumentFragmentData = Field(..., description="Fragment data")
    operation: str = Field(..., description="Operation type (create, update, delete)")
    batch_id: Optional[str] = Field(None, description="Batch identifier for batch operations")
    last_updated: datetime = Field(..., description="When the fragment was last updated")
    sync_timestamp: datetime = Field(..., description="When the data was last synced from provider")
    document_id: str = Field(..., description="Parent document ID")

    def model_post_init(self, __context: Any) -> None:
        """Set default source service if not provided."""
        super().model_post_init(__context)
        if not self.metadata.source_service:
            self.metadata.source_service = "office-service"
