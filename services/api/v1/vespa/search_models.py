"""
Shared search models for vespa services.

This module contains Pydantic models that are shared between vespa_query and chat services
to ensure consistent data structures and type safety.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search query model for vespa searches."""

    yql: str = Field(..., description="YQL query string")
    hits: int = Field(default=20, description="Maximum number of results to return")
    ranking: str = Field(default="hybrid", description="Ranking profile to use")
    timeout: str = Field(default="5.0s", description="Search timeout")
    streaming_groupname: Optional[str] = Field(
        None, description="User ID for streaming"
    )
    offset: int = Field(default=0, description="Result offset for pagination")
    query_profile: Optional[str] = Field(None, description="Query profile to use")
    trace_level: Optional[int] = Field(None, description="Trace level for debugging")


class SearchResult(BaseModel):
    """Individual search result document."""

    id: str = Field(..., description="Document ID")
    user_id: str = Field(..., description="User ID who owns this document")
    source_type: str = Field(
        ..., description="Type of document (email, calendar, contact, etc.)"
    )
    provider: str = Field(..., description="Data provider (gmail, outlook, etc.)")
    title: str = Field(default="", description="Document title/subject")
    content: str = Field(default="", description="Document content")
    search_text: str = Field(default="", description="Searchable text content")
    created_at: Optional[int] = Field(None, description="Creation timestamp")
    updated_at: Optional[int] = Field(None, description="Last update timestamp")
    relevance_score: float = Field(default=0.0, description="Search relevance score")

    # Email-specific fields
    sender: Optional[str] = Field(None, description="Email sender address")
    recipients: List[str] = Field(default_factory=list, description="Email recipients")
    thread_id: Optional[str] = Field(None, description="Email thread ID")
    folder: Optional[str] = Field(None, description="Email folder")
    quoted_content: Optional[str] = Field(None, description="Quoted content in email")
    thread_summary: Optional[Dict[str, Any]] = Field(None, description="Thread summary")

    # Calendar-specific fields
    start_time: Optional[int] = Field(None, description="Event start time")
    end_time: Optional[int] = Field(None, description="Event end time")
    attendees: List[str] = Field(default_factory=list, description="Event attendees")
    location: Optional[str] = Field(None, description="Event location")
    is_all_day: Optional[bool] = Field(None, description="Whether event is all-day")
    recurring: Optional[bool] = Field(None, description="Whether event is recurring")

    # Contact-specific fields
    display_name: Optional[str] = Field(None, description="Contact display name")
    email_addresses: List[str] = Field(
        default_factory=list, description="Contact email addresses"
    )
    company: Optional[str] = Field(None, description="Contact company")
    job_title: Optional[str] = Field(None, description="Contact job title")
    phone_numbers: List[str] = Field(
        default_factory=list, description="Contact phone numbers"
    )
    address: Optional[str] = Field(None, description="Contact address")

    # Document-specific fields
    file_name: Optional[str] = Field(None, description="File name")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="File MIME type")

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Search-specific fields
    highlights: List[str] = Field(default_factory=list, description="Search highlights")
    snippet: Optional[str] = Field(None, description="Generated snippet")
    search_method: Optional[str] = Field(None, description="Search method used")
    match_confidence: Optional[str] = Field(None, description="Match confidence level")
    vector_similarity: Optional[float] = Field(
        None, description="Vector similarity score"
    )
    keyword_matches: Optional[Dict[str, Any]] = Field(
        None, description="Keyword match details"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SearchFacets(BaseModel):
    """Search result facets for aggregation."""

    source_types: Dict[str, int] = Field(
        default_factory=dict, description="Count by source type"
    )
    providers: Dict[str, int] = Field(
        default_factory=dict, description="Count by provider"
    )
    folders: Dict[str, int] = Field(default_factory=dict, description="Count by folder")
    date_ranges: Dict[str, int] = Field(
        default_factory=dict, description="Count by date range"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SearchPerformance(BaseModel):
    """Search performance metrics."""

    query_time_ms: float = Field(
        default=0.0, description="Query execution time in milliseconds"
    )
    total_time_ms: float = Field(
        default=0.0, description="Total response time in milliseconds"
    )
    search_time_ms: float = Field(default=0.0, description="Search processing time")
    match_time_ms: float = Field(default=0.0, description="Match processing time")
    fetch_time_ms: float = Field(default=0.0, description="Document fetch time")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SearchResponse(BaseModel):
    """Complete search response."""

    query: str = Field(..., description="Original search query")
    user_id: str = Field(..., description="User ID who performed the search")
    total_hits: int = Field(default=0, description="Total number of matching documents")
    documents: List[SearchResult] = Field(
        default_factory=list, description="Search results"
    )
    facets: SearchFacets = Field(
        default_factory=SearchFacets, description="Search facets"
    )
    performance: SearchPerformance = Field(
        default_factory=SearchPerformance, description="Performance metrics"
    )
    coverage: Optional[Dict[str, Any]] = Field(
        None, description="Search coverage information"
    )
    processed_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Processing timestamp",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SearchError(BaseModel):
    """Search error response."""

    query: str = Field(..., description="Original search query")
    user_id: str = Field(..., description="User ID who performed the search")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code if available")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    processed_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SearchSummary(BaseModel):
    """Summary of search results grouped by type."""

    total_results: int = Field(..., description="Total number of results")
    result_types: Dict[str, int] = Field(
        default_factory=dict, description="Count by result type"
    )
    top_results: List[SearchResult] = Field(
        default_factory=list, description="Top results by relevance"
    )
    query_analysis: Optional[Dict[str, Any]] = Field(
        None, description="Query analysis information"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
