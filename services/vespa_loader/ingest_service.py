#!/usr/bin/env python3
"""
Ingest Service for Vespa Loader

This module contains the core document ingestion logic that can be used
by both the HTTP API endpoints and the Pub/Sub consumer.
"""

from typing import Any, Dict, Union

from services.common.http_errors import (
    ErrorCode,
    ServiceError,
    ValidationError,
)
from services.vespa_loader.types import VespaDocumentType


async def ingest_document_service(
    document_data: Union[VespaDocumentType, Dict[str, Any]],
    vespa_client: Any,
    content_normalizer: Any,
    embedding_generator: Any,
    document_mapper: Any,
) -> Dict[str, Any]:
    """Shared service function to ingest a document into Vespa

    This function can be called directly by other parts of the service
    or through the HTTP API endpoints.

    Args:
        document_data: The document data to ingest
        vespa_client: Initialized Vespa client instance
        content_normalizer: Initialized content normalizer instance
        embedding_generator: Initialized embedding generator instance
        document_mapper: Initialized document mapper instance

    Returns:
        Dict containing the ingestion result

    Raises:
        ServiceError: If the service is not properly initialized
        ValidationError: If document data is invalid
    """
    if not all(
        [vespa_client, content_normalizer, embedding_generator, document_mapper]
    ):
        raise ServiceError(
            "Service not initialized", code=ErrorCode.SERVICE_UNAVAILABLE
        )

    try:
        # Validate document data
        if isinstance(document_data, VespaDocumentType):
            if not document_data.id or not document_data.user_id:
                raise ValidationError(
                    "Document ID and user_id are required",
                    field="document_data",
                    value=document_data,
                )
            # Convert to dict for processing
            document_dict = document_data.to_dict()
        else:
            if not document_data.get("id") or not document_data.get("user_id"):
                raise ValidationError(
                    "Document ID and user_id are required",
                    field="document_data",
                    value=document_data,
                )
            document_dict = document_data

        # Map document to Vespa format
        if not document_mapper:
            raise ServiceError(
                "Document mapper not initialized", code=ErrorCode.SERVICE_ERROR
            )
        vespa_document = document_mapper.map_to_vespa(document_dict)

        # Normalize content
        if vespa_document.get("content") and content_normalizer:
            vespa_document["content"] = content_normalizer.normalize(
                vespa_document["content"]
            )

        # Generate embeddings if content exists
        content = vespa_document.get("content")
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
        if not vespa_client:
            raise ServiceError(
                "Vespa client not initialized", code=ErrorCode.SERVICE_ERROR
            )
        result = await vespa_client.index_document(vespa_document)

        return {
            "status": "success",
            "document_id": document_dict["id"],
            "vespa_result": result,
        }

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
