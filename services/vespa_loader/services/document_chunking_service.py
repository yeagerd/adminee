"""
Document chunking service for processing large documents into searchable fragments.

This module has been moved from services/common/services/ to services/vespa_loader/services/
to consolidate chunking functionality with the vespa_loader service.
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.vespa_loader.models.document_chunking import (
    ChunkingResult,
    ChunkingRule,
    ChunkingStrategy,
    ChunkType,
    DocumentChunk,
    DocumentChunkingConfig,
)

logger = logging.getLogger(__name__)


class DocumentChunkingService:
    """Service for chunking large documents into searchable fragments."""

    def __init__(self, config: Optional[DocumentChunkingConfig] = None):
        self.config = config or DocumentChunkingConfig()
        self._chunk_cache: Dict[str, List[DocumentChunk]] = {}

    def chunk_document(
        self,
        document_id: str,
        content: str,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChunkingResult:
        """Chunk a document based on its type and content."""
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            # Get chunking rules for document type
            rules = self._get_chunking_rules(document_type)

            # Choose chunking strategy
            if rules.strategy == ChunkingStrategy.HYBRID:
                chunks = self._hybrid_chunking(content, rules, metadata)
            elif rules.strategy == ChunkingStrategy.SECTION_BOUNDARIES:
                chunks = self._section_boundary_chunking(content, rules, metadata)
            elif rules.strategy == ChunkingStrategy.PAGE_LIMITS:
                chunks = self._page_limit_chunking(content, rules, metadata)
            elif rules.strategy == ChunkingStrategy.SEMANTIC_BREAKS:
                chunks = self._semantic_break_chunking(content, rules, metadata)
            elif rules.strategy == ChunkingStrategy.FIXED_SIZE:
                chunks = self._fixed_size_chunking(content, rules, metadata)
            else:
                raise ValueError(f"Unknown chunking strategy: {rules.strategy}")

            # Post-process chunks
            chunks = self._post_process_chunks(chunks, rules, metadata)

            # Create chunking result
            result = ChunkingResult(
                document_id=document_id,
                chunks=chunks,
                total_chunks=len(chunks),
                total_content_length=sum(chunk.content_length for chunk in chunks),
                average_chunk_size=(
                    sum(chunk.content_length for chunk in chunks) / len(chunks)
                    if chunks
                    else 0
                ),
                chunk_size_variance=self._calculate_variance(
                    [chunk.content_length for chunk in chunks]
                ),
                content_coverage=len(content) / len(content) if content else 0,
                chunk_quality_score=self._calculate_quality_score(chunks, rules),
                empty_chunks=len([c for c in chunks if c.content_length < 50]),
                processing_time_seconds=time.time() - start_time,
                memory_usage_mb=self._get_memory_usage() - start_memory,
                chunking_strategy=rules.strategy,
                chunking_rules=rules,
                created_at=datetime.now(timezone.utc),
            )

            # Validate result
            if not result.validate_chunk_sequence():
                logger.warning(
                    f"Chunk sequence validation failed for document {document_id}"
                )

            # Cache chunks
            self._chunk_cache[document_id] = chunks

            logger.info(
                f"Successfully chunked document {document_id} into {len(chunks)} chunks"
            )
            return result

        except Exception as e:
            logger.error(f"Error chunking document {document_id}: {e}")
            raise

    def _hybrid_chunking(
        self, content: str, rules: ChunkingRule, metadata: Optional[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Hybrid chunking that combines multiple strategies."""
        chunks = []

        # First, try section boundary chunking
        section_chunks = self._section_boundary_chunking(content, rules, metadata)

        # If sections are too large, apply size-based chunking within sections
        for section_chunk in section_chunks:
            if section_chunk.content_length <= rules.max_chunk_size:
                chunks.append(section_chunk)
            else:
                # Split large sections using fixed-size chunking
                sub_chunks = self._fixed_size_chunking(
                    section_chunk.content, rules, metadata
                )
                # Update metadata for sub-chunks
                for i, sub_chunk in enumerate(sub_chunks):
                    sub_chunk.section_path = section_chunk.section_path + [f"sub_{i+1}"]
                    sub_chunk.parent_doc_id = section_chunk.parent_doc_id
                chunks.extend(sub_chunks)

        return chunks

    def _section_boundary_chunking(
        self, content: str, rules: ChunkingRule, metadata: Optional[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Chunk based on natural section boundaries."""
        chunks = []

        # Split content into sections
        sections = self._extract_sections(content, metadata)

        for i, (section_title, section_content) in enumerate(sections):
            if len(section_content.strip()) < rules.min_chunk_size:
                # Skip very small sections
                continue

            # Create chunk for this section
            chunk = DocumentChunk(
                parent_doc_id=(
                    metadata.get("document_id", "unknown") if metadata else "unknown"
                ),
                chunk_sequence=i + 1,
                chunk_type=ChunkType.SECTION,
                content=section_content.strip(),
                content_length=len(section_content.strip()),
                word_count=len(section_content.split()),
                title=section_title,
                section_path=[section_title] if section_title else [],
                page_number=None,
                chunking_strategy=rules.strategy,
                chunk_size=rules.target_chunk_size,
                overlap_size=rules.overlap_size,
                start_offset=content.find(section_content),
                end_offset=content.find(section_content) + len(section_content),
                previous_chunk_id=None,
                next_chunk_id=None,
                search_text=self._optimize_for_search(section_content),
                keywords=self._extract_keywords(section_content),
                embedding=None,
            )

            chunks.append(chunk)

        return chunks

    def _page_limit_chunking(
        self, content: str, rules: ChunkingRule, metadata: Optional[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Chunk based on page limits (for presentations, PDFs, etc.)."""
        chunks = []

        # Extract page information from metadata or content
        pages = self._extract_pages(content, metadata)

        for i, (page_content, page_info) in enumerate(pages):
            if len(page_content.strip()) < rules.min_chunk_size:
                # Skip very small pages
                continue

            chunk = DocumentChunk(
                parent_doc_id=(
                    metadata.get("document_id", "unknown") if metadata else "unknown"
                ),
                chunk_sequence=i + 1,
                chunk_type=ChunkType.PAGE,
                content=page_content.strip(),
                content_length=len(page_content.strip()),
                word_count=len(page_content.split()),
                title=f"Page {page_info.get('page_number', i + 1)}",
                section_path=[f"page_{page_info.get('page_number', i + 1)}"],
                page_number=page_info.get("page_number", i + 1),
                chunking_strategy=rules.strategy,
                chunk_size=rules.target_chunk_size,
                overlap_size=rules.overlap_size,
                start_offset=content.find(page_content),
                end_offset=content.find(page_content) + len(page_content),
                previous_chunk_id=None,
                next_chunk_id=None,
                search_text=self._optimize_for_search(page_content),
                keywords=self._extract_keywords(page_content),
                embedding=None,
            )

            chunks.append(chunk)

        return chunks

    def _semantic_break_chunking(
        self, content: str, rules: ChunkingRule, metadata: Optional[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Chunk based on semantic breaks in content."""
        chunks = []

        # Split content into semantic units
        semantic_units = self._extract_semantic_units(content, metadata)

        for i, (unit_title, unit_content) in enumerate(semantic_units):
            if len(unit_content.strip()) < rules.min_chunk_size:
                continue

            chunk = DocumentChunk(
                parent_doc_id=(
                    metadata.get("document_id", "unknown") if metadata else "unknown"
                ),
                chunk_sequence=i + 1,
                chunk_type=ChunkType.MIXED,
                content=unit_content.strip(),
                content_length=len(unit_content.strip()),
                word_count=len(unit_content.split()),
                title=unit_title,
                section_path=[unit_title] if unit_title else [],
                page_number=None,
                chunking_strategy=rules.strategy,
                chunk_size=rules.target_chunk_size,
                overlap_size=rules.overlap_size,
                start_offset=content.find(unit_content),
                end_offset=content.find(unit_content) + len(unit_content),
                previous_chunk_id=None,
                next_chunk_id=None,
                search_text=self._optimize_for_search(unit_content),
                keywords=self._extract_keywords(unit_content),
                embedding=None,
            )

            chunks.append(chunk)

        return chunks

    def _fixed_size_chunking(
        self, content: str, rules: ChunkingRule, metadata: Optional[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Chunk content into fixed-size pieces."""
        chunks = []

        # Calculate chunk boundaries
        chunk_size = rules.target_chunk_size
        overlap = rules.overlap_size

        start = 0
        sequence = 1

        while start < len(content):
            # Find the end of this chunk
            end = min(start + chunk_size, len(content))

            # Try to break at word boundaries
            if end < len(content):
                # Look for the last space before the target end
                last_space = content.rfind(" ", start, end)
                if (
                    last_space > start + chunk_size * 0.8
                ):  # Only break at space if we're close to target
                    end = last_space

            chunk_content = content[start:end].strip()

            if len(chunk_content) >= rules.min_chunk_size:
                chunk = DocumentChunk(
                    parent_doc_id=(
                        metadata.get("document_id", "unknown")
                        if metadata
                        else "unknown"
                    ),
                    chunk_sequence=sequence,
                    chunk_type=ChunkType.MIXED,
                    content=chunk_content,
                    content_length=len(chunk_content),
                    word_count=len(chunk_content.split()),
                    title=f"Chunk {sequence}",
                    section_path=[f"chunk_{sequence}"],
                    page_number=None,
                    chunking_strategy=rules.strategy,
                    chunk_size=chunk_size,
                    overlap_size=overlap,
                    start_offset=start,
                    end_offset=end,
                    previous_chunk_id=None,
                    next_chunk_id=None,
                    search_text=self._optimize_for_search(chunk_content),
                    keywords=self._extract_keywords(chunk_content),
                    embedding=None,
                )

                chunks.append(chunk)
                sequence += 1

            # Move to next chunk with overlap
            start = max(start + 1, end - overlap)

        return chunks

    def _extract_sections(
        self, content: str, metadata: Optional[Dict[str, Any]]
    ) -> List[Tuple[str, str]]:
        """Extract sections from content based on headers and structure."""
        sections = []

        # Common header patterns
        header_patterns = [
            r"^#+\s+(.+)$",  # Markdown headers
            r"^[A-Z][A-Z\s]+\n[-=]+\n",  # Underlined headers
            r"^\d+\.\s+(.+)$",  # Numbered sections
            r"^[A-Z][^.!?]*[.!?]?\n",  # Sentence-style headers
        ]

        # Split content by headers
        lines = content.split("\n")
        current_section: List[str] = []
        current_title = "Introduction"

        for line in lines:
            # Check if line is a header
            is_header = any(re.match(pattern, line) for pattern in header_patterns)

            if is_header and current_section:
                # Save current section
                sections.append((current_title, "\n".join(current_section)))
                current_section = []
                current_title = line.strip()
            else:
                current_section.append(line)

        # Add final section
        if current_section:
            sections.append((current_title, "\n".join(current_section)))

        return sections

    def _extract_pages(
        self, content: str, metadata: Optional[Dict[str, Any]]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Extract pages from content."""
        pages = []

        # Try to find page breaks
        page_breaks = re.split(
            r"\f|\n\s*Page\s+\d+\s*\n|\n\s*---\s*Page\s+\d+\s*---\s*\n", content
        )

        for i, page_content in enumerate(page_breaks):
            if page_content.strip():
                page_info = {"page_number": i + 1, "page_type": "content"}
                pages.append((page_content, page_info))

        # If no page breaks found, treat entire content as one page
        if not pages:
            pages.append((content, {"page_number": 1, "page_type": "content"}))

        return pages

    def _extract_semantic_units(
        self, content: str, metadata: Optional[Dict[str, Any]]
    ) -> List[Tuple[str, str]]:
        """Extract semantic units from content."""
        units = []

        # Split by paragraphs
        paragraphs = content.split("\n\n")

        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                # Try to extract a title from the first sentence
                sentences = paragraph.split(".")
                title = sentences[0].strip() if sentences else f"Unit {i + 1}"

                units.append((title, paragraph))

        return units

    def _post_process_chunks(
        self,
        chunks: List[DocumentChunk],
        rules: ChunkingRule,
        metadata: Optional[Dict[str, Any]],
    ) -> List[DocumentChunk]:
        """Post-process chunks to improve quality and consistency."""
        processed_chunks = []

        for chunk in chunks:
            # Skip chunks that are too small
            if chunk.content_length < rules.min_chunk_size:
                continue

            # Skip chunks that are too low quality
            if self._calculate_chunk_quality(chunk) < rules.min_content_quality:
                continue

            # Clean up content
            chunk.content = self._clean_content(chunk.content)
            chunk.content_length = len(chunk.content)
            chunk.word_count = len(chunk.content.split())

            # Update search text
            chunk.search_text = self._optimize_for_search(chunk.content)

            # Extract keywords
            chunk.keywords = self._extract_keywords(chunk.content)

            processed_chunks.append(chunk)

        # Re-sequence chunks
        for i, chunk in enumerate(processed_chunks):
            chunk.chunk_sequence = i + 1

        return processed_chunks

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        # Remove excessive whitespace
        content = re.sub(r"\s+", " ", content)

        # Remove common artifacts
        content = re.sub(r"^\s*[-*]\s*", "", content)  # Remove list markers
        content = re.sub(r"\s*[-*]\s*$", "", content)

        # Normalize line breaks
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        return content.strip()

    def _optimize_for_search(self, content: str) -> str:
        """Optimize content for search indexing."""
        # Remove special characters that don't help with search
        search_text = re.sub(r"[^\w\s]", " ", content)

        # Normalize whitespace
        search_text = re.sub(r"\s+", " ", search_text)

        # Convert to lowercase for consistency
        search_text = search_text.lower()

        return search_text.strip()

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r"\b\w+\b", content.lower())

        # Filter out common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        keywords = [word for word in words if word not in stop_words and len(word) > 3]

        # Count frequency and return top keywords
        word_freq: Dict[str, int] = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Return top 10 keywords by frequency
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, freq in top_keywords]

    def _calculate_chunk_quality(self, chunk: DocumentChunk) -> float:
        """Calculate quality score for a chunk."""
        score = 0.0

        # Content length score (0-30 points)
        if chunk.content_length >= 500:
            score += 30
        elif chunk.content_length >= 200:
            score += 20
        elif chunk.content_length >= 100:
            score += 10

        # Word count score (0-20 points)
        if chunk.word_count >= 50:
            score += 20
        elif chunk.word_count >= 25:
            score += 15
        elif chunk.word_count >= 10:
            score += 10

        # Title presence score (0-20 points)
        if chunk.title and len(chunk.title.strip()) > 0:
            score += 20

        # Keyword score (0-30 points)
        keyword_score = min(30, len(chunk.keywords) * 3)
        score += keyword_score

        # Normalize to 0.0-1.0 range
        return min(1.0, score / 100.0)

    def _calculate_quality_score(
        self, chunks: List[DocumentChunk], rules: ChunkingRule
    ) -> float:
        """Calculate overall quality score for all chunks."""
        if not chunks:
            return 0.0

        total_quality = sum(self._calculate_chunk_quality(chunk) for chunk in chunks)
        return total_quality / len(chunks)

    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if not values:
            return 0.0

        mean = sum(values) / len(values)
        squared_diff_sum = sum((x - mean) ** 2 for x in values)
        return squared_diff_sum / len(values)

    def _get_chunking_rules(self, document_type: str) -> ChunkingRule:
        """Get chunking rules for a specific document type."""
        if document_type.lower() in ["word", "doc", "docx"]:
            return self.config.word_document_rules
        elif document_type.lower() in ["sheet", "spreadsheet", "xls", "xlsx"]:
            return self.config.sheet_document_rules
        elif document_type.lower() in ["presentation", "ppt", "pptx"]:
            return self.config.presentation_document_rules
        else:
            # Default rules
            return ChunkingRule(
                name="default",
                strategy=ChunkingStrategy.HYBRID,
                min_chunk_size=500,
                max_chunk_size=2000,
                target_chunk_size=1000,
                overlap_size=100,
            )

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

    def get_cached_chunks(self, document_id: str) -> Optional[List[DocumentChunk]]:
        """Get cached chunks for a document."""
        return self._chunk_cache.get(document_id)

    def clear_cache(self) -> None:
        """Clear the chunk cache."""
        self._chunk_cache.clear()
        logger.info("Document chunking cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_documents": len(self._chunk_cache),
            "total_chunks": sum(len(chunks) for chunks in self._chunk_cache.values()),
            "cache_size_mb": sum(
                sum(chunk.content_length for chunk in chunks)
                for chunks in self._chunk_cache.values()
            )
            / 1024
            / 1024,
        }
