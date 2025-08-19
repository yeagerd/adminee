#!/usr/bin/env python3
"""
Pydantic models for Vespa loader data structures

These models replace sloppy get() calls with proper validation and structure.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class OfficeRouterDocument(BaseModel):
    """Data structure sent by the office router to vespa loader."""

    document_type: str = Field(
        ..., description="Document type (e.g., 'briefly_document')"
    )
    fields: Dict[str, Any] = Field(..., description="Document fields")


class VespaDocumentFields(BaseModel):
    """Fields expected by the vespa loader document mapper."""

    user_id: str = Field(..., description="User ID for the document")
    doc_id: str = Field(..., description="Document ID from the source system")
    provider: str = Field(..., description="Data provider (e.g., 'microsoft', 'gmail')")
    source_type: str = Field(
        ..., description="Type of document (e.g., 'email', 'calendar', 'contact')"
    )
    title: Optional[str] = Field(None, description="Document title")
    content: Optional[str] = Field(None, description="Document content")
    search_text: Optional[str] = Field(None, description="Searchable text content")
    sender: Optional[str] = Field(None, description="Document sender")
    recipients: Optional[List[str]] = Field(None, description="Document recipients")
    thread_id: Optional[str] = Field(None, description="Thread ID for emails")
    folder: Optional[str] = Field(None, description="Folder location")
    created_at: Optional[Union[str, datetime]] = Field(
        None, description="Creation timestamp"
    )
    updated_at: Optional[Union[str, datetime]] = Field(
        None, description="Last update timestamp"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class OfficeRouterVespaDocument(BaseModel):
    """Complete document structure sent by office router to vespa loader."""

    document_type: str = Field(..., description="Document type")
    fields: VespaDocumentFields = Field(..., description="Document fields")


class VespaLoaderExpectedDocument(BaseModel):
    """Data structure expected by the vespa loader document mapper."""

    user_id: str = Field(..., description="User ID for the document")
    id: str = Field(
        ..., description="Document ID (note: different from doc_id in router)"
    )
    provider: str = Field(..., description="Data provider")
    type: str = Field(
        ..., description="Document type (note: different from source_type in router)"
    )
    subject: Optional[str] = Field(
        None, description="Document subject (note: different from title in router)"
    )
    body: Optional[str] = Field(
        None, description="Document body (note: different from content in router)"
    )
    sender: Optional[str] = Field(
        None, description="Document sender (note: different from sender in router)"
    )
    to: Optional[List[str]] = Field(
        None,
        description="Document recipients (note: different from recipients in router)",
    )
    thread_id: Optional[str] = Field(None, description="Thread ID")
    folder: Optional[str] = Field(None, description="Folder location")
    created_at: Optional[Union[str, datetime]] = Field(
        None, description="Creation timestamp"
    )
    updated_at: Optional[Union[str, datetime]] = Field(
        None, description="Last update timestamp"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class VespaIndexedDocument(BaseModel):
    """Final document structure after vespa loader processing."""

    user_id: str = Field(..., description="User ID")
    doc_id: str = Field(..., description="Document ID")
    provider: str = Field(..., description="Data provider")
    source_type: str = Field(..., description="Document type")
    title: str = Field("", description="Document title")
    content: str = Field("", description="Document content")
    search_text: str = Field("", description="Searchable text")
    sender: str = Field("", description="Document sender")
    recipients: List[str] = Field(
        default_factory=list, description="Document recipients"
    )
    thread_id: str = Field("", description="Thread ID")
    folder: str = Field("", description="Folder location")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    embedding: Optional[List[float]] = Field(
        None, description="Document embedding vector"
    )


def convert_office_router_to_vespa_loader(
    router_doc: OfficeRouterVespaDocument,
) -> VespaLoaderExpectedDocument:
    """Convert office router document format to vespa loader expected format."""
    fields = router_doc.fields

    return VespaLoaderExpectedDocument(
        user_id=fields.user_id,
        id=fields.doc_id,  # Map doc_id to id
        provider=fields.provider,
        type=fields.source_type,  # Map source_type to type
        subject=fields.title,  # Map title to subject
        body=fields.content,  # Map content to body
        sender=fields.sender,  # Map sender to sender
        to=fields.recipients,  # Map recipients to to
        thread_id=fields.thread_id,
        folder=fields.folder,
        created_at=fields.created_at,
        updated_at=fields.updated_at,
        metadata=fields.metadata or {},
    )


def validate_office_router_document(data: Dict[str, Any]) -> OfficeRouterVespaDocument:
    """Validate and parse office router document data."""
    return OfficeRouterVespaDocument(**data)


def validate_vespa_loader_document(data: Dict[str, Any]) -> VespaLoaderExpectedDocument:
    """Validate and parse vespa loader expected document data."""
    return VespaLoaderExpectedDocument(**data)
