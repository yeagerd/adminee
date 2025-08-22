"""
Document chunking data models for managing large documents and fragments.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ChunkingStrategy(str, Enum):
    """Strategies for chunking documents."""

    SECTION_BOUNDARIES = "section_boundaries"
    PAGE_LIMITS = "page_limits"
    SEMANTIC_BREAKS = "semantic_breaks"
    FIXED_SIZE = "fixed_size"
    HYBRID = "hybrid"


class ChunkType(str, Enum):
    """Types of document chunks."""

    HEADER = "header"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    PAGE = "page"
    TABLE = "table"
    LIST = "list"
    IMAGE = "image"
    FOOTNOTE = "footnote"
    COMMENT = "comment"
    MIXED = "mixed"


class DocumentChunk(BaseModel):
    """Represents a chunk of a larger document."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique chunk ID")
    parent_doc_id: str = Field(..., description="ID of the parent document")
    chunk_sequence: int = Field(..., description="Order of this chunk in the document")
    chunk_type: ChunkType = Field(..., description="Type of content in this chunk")

    # Content
    content: str = Field(..., description="Text content of the chunk")
    content_length: int = Field(..., description="Length of content in characters")
    word_count: int = Field(..., description="Number of words in the chunk")

    # Metadata
    title: Optional[str] = Field(None, description="Title or heading of this chunk")
    section_path: List[str] = Field(
        default_factory=list, description="Hierarchical path to this chunk"
    )
    page_number: Optional[int] = Field(None, description="Page number if applicable")

    # Chunking info
    chunking_strategy: ChunkingStrategy = Field(
        ..., description="Strategy used to create this chunk"
    )
    chunk_size: int = Field(..., description="Target size of the chunk")
    overlap_size: int = Field(default=0, description="Overlap with adjacent chunks")

    # Boundaries
    start_offset: int = Field(
        ..., description="Character offset from start of parent document"
    )
    end_offset: int = Field(
        ..., description="Character offset to end of chunk in parent document"
    )

    # Relationships
    previous_chunk_id: Optional[str] = Field(None, description="ID of previous chunk")
    next_chunk_id: Optional[str] = Field(None, description="ID of next chunk")
    child_chunk_ids: List[str] = Field(
        default_factory=list, description="IDs of sub-chunks if this is a container"
    )

    # Search and indexing
    search_text: str = Field(..., description="Text optimized for search")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    embedding: Optional[List[float]] = Field(
        None, description="Vector embedding for semantic search"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this chunk was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this chunk was last updated"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_vespa_document(self, user_id: str, provider: str) -> Dict[str, Any]:
        """Convert to Vespa document format."""
        return {
            "doc_id": f"chunk_{self.id}",
            "user_id": user_id,
            "content_type": "document_fragment",
            "title": self.title or f"Chunk {self.chunk_sequence}",
            "content": self.content,
            "search_text": self.search_text,
            "created_at": int(self.created_at.timestamp()),
            "updated_at": int(self.updated_at.timestamp()),
            "last_updated": int(self.updated_at.timestamp()),
            "sync_timestamp": int(self.updated_at.timestamp()),
            "operation": "create",
            "batch_id": None,
            "tags": [
                f"chunk_type:{self.chunk_type}",
                f"strategy:{self.chunking_strategy}",
            ],
            "metadata": {
                "parent_doc_id": self.parent_doc_id,
                "chunk_sequence": self.chunk_sequence,
                "chunk_type": self.chunk_type,
                "content_length": self.content_length,
                "word_count": self.word_count,
                "section_path": self.section_path,
                "page_number": self.page_number,
                "chunking_strategy": self.chunking_strategy,
                "chunk_size": self.chunk_size,
                "overlap_size": self.overlap_size,
                "start_offset": self.start_offset,
                "end_offset": self.end_offset,
                "previous_chunk_id": self.previous_chunk_id,
                "next_chunk_id": self.next_chunk_id,
                "child_chunk_ids": self.child_chunk_ids,
                "keywords": self.keywords,
                "provider": provider,
            },
            "parent_doc_id": self.parent_doc_id,
            "fragment_sequence": self.chunk_sequence,
        }


class ChunkingRule(BaseModel):
    """Rule for chunking documents."""

    name: str = Field(..., description="Name of the chunking rule")
    strategy: ChunkingStrategy = Field(..., description="Chunking strategy to use")

    # Size constraints
    min_chunk_size: int = Field(..., description="Minimum chunk size in characters")
    max_chunk_size: int = Field(..., description="Maximum chunk size in characters")
    target_chunk_size: int = Field(..., description="Target chunk size in characters")
    overlap_size: int = Field(
        default=0, description="Overlap between chunks in characters"
    )

    # Content rules
    preserve_sections: bool = Field(
        default=True, description="Try to keep sections intact"
    )
    preserve_paragraphs: bool = Field(
        default=True, description="Try to keep paragraphs intact"
    )
    preserve_sentences: bool = Field(
        default=False, description="Try to keep sentences intact"
    )

    # Special handling
    handle_tables: bool = Field(
        default=True, description="Special handling for table content"
    )
    handle_lists: bool = Field(
        default=True, description="Special handling for list content"
    )
    handle_images: bool = Field(
        default=True, description="Special handling for image content"
    )

    # Quality thresholds
    min_content_quality: float = Field(
        default=0.7, description="Minimum content quality score (0.0-1.0)"
    )
    max_empty_chunks: int = Field(
        default=0, description="Maximum number of empty chunks allowed"
    )

    # Performance settings
    max_processing_time: int = Field(
        default=30, description="Maximum processing time in seconds"
    )
    batch_size: int = Field(
        default=100, description="Number of chunks to process in a batch"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ChunkingResult(BaseModel):
    """Result of a document chunking operation."""

    document_id: str = Field(..., description="ID of the document that was chunked")
    chunks: List[DocumentChunk] = Field(..., description="Generated chunks")

    # Statistics
    total_chunks: int = Field(..., description="Total number of chunks created")
    total_content_length: int = Field(
        ..., description="Total content length across all chunks"
    )
    average_chunk_size: float = Field(..., description="Average chunk size")
    chunk_size_variance: float = Field(..., description="Variance in chunk sizes")

    # Quality metrics
    content_coverage: float = Field(
        ..., description="Percentage of original content covered"
    )
    chunk_quality_score: float = Field(
        ..., description="Overall quality score for chunks"
    )
    empty_chunks: int = Field(..., description="Number of empty or low-quality chunks")

    # Performance metrics
    processing_time_seconds: float = Field(
        ..., description="Time taken to process document"
    )
    memory_usage_mb: float = Field(..., description="Memory used during processing")

    # Metadata
    chunking_strategy: ChunkingStrategy = Field(
        ..., description="Strategy used for chunking"
    )
    chunking_rules: ChunkingRule = Field(
        ..., description="Rules applied during chunking"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When chunking was completed"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def get_chunk_by_sequence(self, sequence: int) -> Optional[DocumentChunk]:
        """Get a chunk by its sequence number."""
        for chunk in self.chunks:
            if chunk.chunk_sequence == sequence:
                return chunk
        return None

    def get_chunks_by_type(self, chunk_type: ChunkType) -> List[DocumentChunk]:
        """Get all chunks of a specific type."""
        return [chunk for chunk in self.chunks if chunk.chunk_type == chunk_type]

    def get_chunk_at_offset(self, offset: int) -> Optional[DocumentChunk]:
        """Get the chunk that contains a specific character offset."""
        for chunk in self.chunks:
            if chunk.start_offset <= offset <= chunk.end_offset:
                return chunk
        return None

    def validate_chunk_sequence(self) -> bool:
        """Validate that chunks are properly sequenced."""
        if not self.chunks:
            return False

        # Check sequence numbers
        sequences = [chunk.chunk_sequence for chunk in self.chunks]
        if sequences != sorted(sequences):
            return False

        # Check for gaps
        for i in range(len(sequences) - 1):
            if sequences[i + 1] - sequences[i] != 1:
                return False

        # Check parent-child relationships
        for i, chunk in enumerate(self.chunks):
            if i > 0:
                chunk.previous_chunk_id = self.chunks[i - 1].id
            if i < len(self.chunks) - 1:
                chunk.next_chunk_id = self.chunks[i + 1].id

        return True


class DocumentChunkingConfig(BaseModel):
    """Configuration for document chunking service."""

    # Default rules for different document types
    word_document_rules: ChunkingRule = Field(
        default_factory=lambda: ChunkingRule(
            name="word_document_default",
            strategy=ChunkingStrategy.HYBRID,
            min_chunk_size=500,
            max_chunk_size=2000,
            target_chunk_size=1000,
            overlap_size=100,
            preserve_sections=True,
            preserve_paragraphs=True,
            preserve_sentences=False,
            handle_tables=True,
            handle_lists=True,
            handle_images=True,
            min_content_quality=0.8,
            max_empty_chunks=0,
            max_processing_time=60,
            batch_size=50,
        )
    )

    sheet_document_rules: ChunkingRule = Field(
        default_factory=lambda: ChunkingRule(
            name="sheet_document_default",
            strategy=ChunkingStrategy.SECTION_BOUNDARIES,
            min_chunk_size=300,
            max_chunk_size=1500,
            target_chunk_size=800,
            overlap_size=50,
            preserve_sections=True,
            preserve_paragraphs=False,
            preserve_sentences=False,
            handle_tables=True,
            handle_lists=False,
            handle_images=False,
            min_content_quality=0.7,
            max_empty_chunks=1,
            max_processing_time=45,
            batch_size=100,
        )
    )

    presentation_document_rules: ChunkingRule = Field(
        default_factory=lambda: ChunkingRule(
            name="presentation_document_default",
            strategy=ChunkingStrategy.PAGE_LIMITS,
            min_chunk_size=400,
            max_chunk_size=1800,
            target_chunk_size=900,
            overlap_size=75,
            preserve_sections=True,
            preserve_paragraphs=True,
            preserve_sentences=False,
            handle_tables=True,
            handle_lists=True,
            handle_images=True,
            min_content_quality=0.75,
            max_empty_chunks=0,
            max_processing_time=30,
            batch_size=75,
        )
    )

    # Global settings
    enable_parallel_processing: bool = Field(
        default=True, description="Enable parallel chunking"
    )
    max_workers: int = Field(
        default=4, description="Maximum number of worker processes"
    )
    chunk_cache_size: int = Field(
        default=1000, description="Number of chunks to cache in memory"
    )

    # Quality thresholds
    min_chunk_quality: float = Field(
        default=0.6, description="Minimum quality for chunks to be indexed"
    )
    max_chunk_retries: int = Field(
        default=3, description="Maximum retries for failed chunking"
    )

    # Storage settings
    enable_chunk_compression: bool = Field(
        default=True, description="Compress chunk content for storage"
    )
    chunk_retention_days: int = Field(
        default=365, description="Days to retain chunk data"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
