#!/usr/bin/env python3
"""
Ingest Service for Vespa Loader

This module contains the core document ingestion logic that can be used
by both the HTTP API endpoints and the Pub/Sub consumer.
"""

from typing import Any, Dict

from services.common.http_errors import (
    ErrorCode,
    ServiceError,
    ValidationError,
)
from services.vespa_loader.types import VespaDocumentType, DocumentIngestionResult
from vespa_loader.content_normalizer import ContentNormalizer
from vespa_loader.embeddings import EmbeddingGenerator
from vespa_loader.vespa_client import VespaClient


async def ingest_document_service(
    document_data: VespaDocumentType,
    vespa_client: VespaClient,
    content_normalizer: ContentNormalizer,
    embedding_generator: EmbeddingGenerator,
) -> DocumentIngestionResult:
    """Shared service function to ingest a document into Vespa

    This function can be called directly by other parts of the service
    or through the HTTP API endpoints.

    Args:
        document_data: The document data to ingest (must be VespaDocumentType)
        vespa_client: Initialized Vespa client instance
        content_normalizer: Initialized content normalizer instance
        embedding_generator: Initialized embedding generator instance

    Returns:
        DocumentIngestionResult containing the ingestion result details

    Raises:
        ServiceError: If the service is not properly initialized
        ValidationError: If document data is invalid
    """

    try:
        # Validate document data
        if not document_data.id or not document_data.user_id:
            raise ValidationError(
                "Document ID and user_id are required",
                field="document_data",
                value=document_data,
            )
        
        # Document is already in Vespa format, use it directly
        vespa_document = document_data.to_dict()

        # Normalize content
        if vespa_document.get("body") and content_normalizer:
            vespa_document["body"] = content_normalizer.normalize(
                vespa_document["body"]
            )

        # Generate embeddings if content exists
        content = vespa_document.get("body")
        if content and embedding_generator:
            try:
                embedding = await embedding_generator.generate_embedding(content)
                vespa_document["embedding"] = embedding
            except Exception as e:
                # Log warning but continue without embedding
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to generate embedding: {e}")

        # Index document in Vespa
        result = await vespa_client.index_document(vespa_document)

        return DocumentIngestionResult(
            status="success",
            document_id=document_data.id,
            vespa_result=result,
        )

    except ValidationError:
        # Re-raise ValidationError to preserve the specific error details
        raise
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error ingesting document: {e}")
        raise ServiceError(
            "Document ingestion failed",
            code=ErrorCode.SERVICE_ERROR,
            details={"error": str(e)},
        )
