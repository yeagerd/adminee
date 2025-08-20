#!/usr/bin/env python3
"""
Vespa Loader Service - Consumes email data and indexes into Vespa
"""

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.common.http_errors import (
    AuthError,
    ErrorCode,
    NotFoundError,
    RateLimitError,
    ServiceError,
    ValidationError,
    register_briefly_exception_handlers,
)
from services.common.logging_config import (
    create_request_logging_middleware,
    get_logger,
    log_service_shutdown,
    log_service_startup,
    setup_service_logging,
)
from services.common.telemetry import get_tracer, setup_telemetry

# Setup telemetry
setup_telemetry("vespa-loader", "1.0.0")

# Get logger and tracer for this module - will be configured in lifespan
logger = get_logger(__name__)
tracer = get_tracer(__name__)

# Global service instances
vespa_client: Optional[Any] = None
content_normalizer: Optional[Any] = None
embedding_generator: Optional[Any] = None
document_mapper: Optional[Any] = None
pubsub_consumer: Optional[Any] = None


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed based on rate limit"""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key] if req_time > window_start
        ]

        # Check if under limit
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True

        return False

    def get_remaining(self, key: str) -> int:
        """Get remaining requests allowed in current window"""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key] if req_time > window_start
        ]

        return max(0, self.max_requests - len(self.requests[key]))


# Initialize rate limiter (will be configured in lifespan)
rate_limiter: Optional[RateLimiter] = None


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Verify API key for inter-service authentication"""
    from services.vespa_loader.settings import Settings

    settings = Settings()

    if x_api_key != settings.api_frontend_vespa_loader_key:
        raise AuthError("Invalid API key", code=ErrorCode.AUTH_FAILED)
    return x_api_key


async def check_rate_limit(api_key: str = Depends(verify_api_key)) -> str:
    """Check rate limit for API requests"""
    if rate_limiter is None:
        return api_key  # No rate limiting if not initialized

    if not rate_limiter.is_allowed(api_key):
        remaining_time = rate_limiter.window_seconds
        raise RateLimitError(
            "API rate limit exceeded",
            retry_after=remaining_time,
            details={
                "limit": rate_limiter.max_requests,
                "window_seconds": rate_limiter.window_seconds,
                "retry_after": remaining_time,
            },
        )
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage service lifecycle"""
    global vespa_client, content_normalizer, embedding_generator, document_mapper, pubsub_consumer

    # Initialize settings
    from services.vespa_loader.settings import Settings

    settings = Settings()

    # Set up centralized logging
    setup_service_logging(
        service_name="vespa-loader",
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    # Now import modules that use logging after logging is configured
    from services.vespa_loader.content_normalizer import ContentNormalizer
    from services.vespa_loader.embeddings import EmbeddingGenerator
    from services.vespa_loader.mapper import DocumentMapper
    from services.vespa_loader.pubsub_consumer import PubSubConsumer
    from services.vespa_loader.vespa_client import VespaClient

    # Log service startup
    log_service_startup("vespa-loader", version="1.0.0", environment="development")

    # Startup
    logger.info("Starting Vespa Loader Service...")

    # Initialize components
    vespa_client = VespaClient(settings.vespa_endpoint)
    content_normalizer = ContentNormalizer()
    embedding_generator = EmbeddingGenerator(settings.embedding_model)
    document_mapper = DocumentMapper()

    # Initialize rate limiter with settings
    global rate_limiter
    rate_limiter = RateLimiter(
        max_requests=settings.api_rate_limit_max_requests,
        window_seconds=settings.api_rate_limit_window_seconds,
    )

    # Test Vespa connectivity
    try:
        await vespa_client.test_connection()
        logger.info("Vespa connection test successful")
    except Exception as e:
        logger.error(f"Vespa connection test failed: {e}")
        raise

    # Start Pub/Sub consumer if enabled
    if settings.enable_pubsub_consumer:
        try:
            pubsub_consumer = PubSubConsumer(settings)
            success = await pubsub_consumer.start()
            if success:
                logger.info("Pub/Sub consumer started successfully")
            else:
                logger.warning("Failed to start Pub/Sub consumer")
        except Exception as e:
            logger.error(f"Failed to start Pub/Sub consumer: {e}")
            # Don't fail startup if Pub/Sub consumer fails
    else:
        logger.info("Pub/Sub consumer disabled")

    logger.info("Vespa Loader Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Vespa Loader Service...")
    if vespa_client:
        await vespa_client.close()
    if pubsub_consumer:
        await pubsub_consumer.stop()
    logger.info("Vespa Loader Service shutdown complete")

    # Log service shutdown
    log_service_shutdown("vespa-loader")


# Create FastAPI app
app = FastAPI(
    title="Vespa Loader Service",
    description="Consumes email data and indexes into Vespa",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.middleware("http")(create_request_logging_middleware())

# Register exception handlers
register_briefly_exception_handlers(app)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Enhanced health check endpoint with external service dependency verification"""
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "service": "vespa-loader",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {},
    }

    # Check Vespa connectivity
    try:
        if vespa_client:
            vespa_ok = await vespa_client.test_connection()
            health_status["components"]["vespa"] = {
                "status": "healthy" if vespa_ok else "unhealthy",
                "endpoint": vespa_client.endpoint,
            }
        else:
            health_status["components"]["vespa"] = {"status": "not_initialized"}
    except Exception as e:
        health_status["components"]["vespa"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"

    # Check Pub/Sub consumer status
    if pubsub_consumer:
        try:
            stats = pubsub_consumer.get_stats()
            health_status["components"]["pubsub_consumer"] = {
                "status": "healthy",
                "stats": stats,
            }
        except Exception as e:
            health_status["components"]["pubsub_consumer"] = {
                "status": "error",
                "error": str(e),
            }
            health_status["status"] = "degraded"
    else:
        health_status["components"]["pubsub_consumer"] = {"status": "not_initialized"}

    # Check core components
    core_components = {
        "content_normalizer": content_normalizer,
        "embedding_generator": embedding_generator,
        "document_mapper": document_mapper,
    }

    for name, component in core_components.items():
        health_status["components"][name] = {
            "status": "healthy" if component else "not_initialized"
        }

    # Determine overall status
    if any(
        comp.get("status") == "error" for comp in health_status["components"].values()
    ):
        health_status["status"] = "unhealthy"
    elif any(
        comp.get("status") == "degraded"
        for comp in health_status["components"].values()
    ):
        health_status["status"] = "degraded"

    return health_status


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {"message": "Vespa Loader Service", "version": "1.0.0"}


@app.post("/ingest")
async def ingest_document(
    document_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    api_key: str = Depends(check_rate_limit),
) -> Dict[str, Any]:
    """Ingest a document into Vespa"""
    if not all(
        [vespa_client, content_normalizer, embedding_generator, document_mapper]
    ):
        raise ServiceError(
            "Service not initialized", code=ErrorCode.SERVICE_UNAVAILABLE
        )

    try:
        # Validate document data
        if not document_data.get("id") or not document_data.get("user_id"):
            raise ValidationError(
                "Document ID and user_id are required",
                field="document_data",
                value=document_data,
            )

        # Map document to Vespa format
        if not document_mapper:
            raise ServiceError(
                "Document mapper not initialized", code=ErrorCode.SERVICE_ERROR
            )
        vespa_document = document_mapper.map_to_vespa(document_data)

        # Normalize content
        if vespa_document.get("content") and content_normalizer:
            vespa_document["content"] = content_normalizer.normalize(
                vespa_document["content"]
            )

        # Generate embeddings if content exists
        if vespa_document.get("content") and embedding_generator:
            try:
                embedding = await embedding_generator.generate_embedding(
                    vespa_document["content"]
                )
                vespa_document["embedding"] = embedding
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
                # Continue without embedding

        # Index document in Vespa
        if not vespa_client:
            raise ServiceError(
                "Vespa client not initialized", code=ErrorCode.SERVICE_ERROR
            )
        result = await vespa_client.index_document(vespa_document)

        # Add background task for post-processing if needed
        background_tasks.add_task(
            _post_process_document,
            document_id=document_data["id"],
            user_id=document_data["user_id"],
        )

        return {
            "status": "success",
            "document_id": document_data["id"],
            "vespa_result": result,
        }

    except Exception as e:
        logger.error(f"Error ingesting document: {e}")
        raise ServiceError(
            "Document ingestion failed",
            code=ErrorCode.SERVICE_ERROR,
            details={"error": str(e)},
        )


@app.post("/ingest/batch")
async def ingest_batch_documents(
    documents: list[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    api_key: str = Depends(check_rate_limit),
) -> Dict[str, Any]:
    """Ingest multiple documents in batch"""
    if not all(
        [vespa_client, content_normalizer, embedding_generator, document_mapper]
    ):
        raise ServiceError(
            "Service not initialized", code=ErrorCode.SERVICE_UNAVAILABLE
        )

    try:
        results = []
        errors = []

        for doc in documents:
            try:
                # Map document to Vespa format
                if not document_mapper:
                    raise ServiceError(
                        "Document mapper not initialized", code=ErrorCode.SERVICE_ERROR
                    )
                vespa_document = document_mapper.map_to_vespa(doc)

                # Normalize content
                if vespa_document.get("content") and content_normalizer:
                    vespa_document["content"] = content_normalizer.normalize(
                        vespa_document["content"]
                    )

                # Generate embeddings if content exists
                if vespa_document.get("content") and embedding_generator:
                    try:
                        embedding = await embedding_generator.generate_embedding(
                            vespa_document["content"]
                        )
                        vespa_document["embedding"] = embedding
                    except Exception as e:
                        logger.warning(
                            f"Failed to generate embedding for document {doc.get('id')}: {e}"
                        )
                        # Continue without embedding

                # Index document in Vespa
                if not vespa_client:
                    raise ServiceError(
                        "Vespa client not initialized", code=ErrorCode.SERVICE_ERROR
                    )
                result = await vespa_client.index_document(vespa_document)

                results.append(
                    {"id": doc.get("id"), "status": "success", "result": result}
                )

            except Exception as e:
                logger.error(
                    f"Error processing document {doc.get('id', 'unknown')}: {e}"
                )
                errors.append({"id": doc.get("id"), "status": "error", "error": str(e)})

        # Add background task for batch post-processing
        if results:
            background_tasks.add_task(
                _post_process_batch,
                successful_docs=len(results),
                failed_docs=len(errors),
            )

        return {
            "status": "completed",
            "total_documents": len(documents),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Error in batch ingestion: {e}")
        raise ServiceError(
            "Batch ingestion failed",
            code=ErrorCode.SERVICE_ERROR,
            details={"error": str(e)},
        )


def _flatten_office_router_document(document_data: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten Office Router nested document into loader's expected flat format.

    Office Router sends: {"document_type": "briefly_document", "fields": {...}}
    Loader expects: flat dict with keys like id, type, subject, body, sender, to, etc.
    """
    if "fields" not in document_data:
        # Assume it's already flat
        return dict(document_data)

    fields = document_data.get("fields", {}) or {}
    flat: Dict[str, Any] = {
        "user_id": fields.get("user_id"),
        "id": fields.get("doc_id"),
        "provider": fields.get("provider"),
        "type": fields.get("source_type"),
        "subject": fields.get("title"),
        "body": fields.get("content"),
        "sender": fields.get("sender"),
        "to": fields.get("recipients"),
        "thread_id": fields.get("thread_id"),
        "folder": fields.get("folder"),
        "created_at": fields.get("created_at"),
        "updated_at": fields.get("updated_at"),
        "metadata": fields.get("metadata", {}),
    }
    return flat


async def process_document(document_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single document, handling both nested and flat formats.

    Steps:
    - Flatten Office Router nested format to loader flat format
    - Map to Vespa document via DocumentMapper
    - Normalize content and compute embedding if available
    - Validate required fields (e.g., user_id)
    """
    try:
        # 1) Flatten if needed
        flat_input = _flatten_office_router_document(document_data)

        # 2) Validate minimally before mapping
        # user_id will be validated after mapping as well, but quick guard helps tests
        if flat_input.get("user_id") is None and "fields" in document_data:
            # In nested format, user_id is mandatory in fields
            # Let mapper/validation catch missing too, but we keep informative errors
            pass

        # 3) Map to Vespa document structure
        if not document_mapper:
            raise ValueError("Document mapper not initialized")
        vespa_doc = document_mapper.map_to_vespa(flat_input)

        # 4) Normalize content and search_text if present
        content = vespa_doc.get("content")
        if content and content_normalizer:
            try:
                normalized = content_normalizer.normalize(content)
                vespa_doc["content"] = normalized
                # Keep search_text aligned with content if present/expected
                vespa_doc["search_text"] = normalized
            except Exception as e:
                logger.warning(f"Content normalization failed: {e}")

        # 5) Generate embedding if we have content
        if vespa_doc.get("content") and embedding_generator:
            try:
                embedding = await embedding_generator.generate_embedding(
                    vespa_doc["content"]
                )
                vespa_doc["embedding"] = embedding
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")

        # 6) Validate required fields post-processing
        if not vespa_doc.get("user_id"):
            raise ValueError("user_id is required")

        return vespa_doc

    except Exception:
        # Bubble up for tests to assert
        raise


@app.delete("/document/{user_id}/{document_id}")
async def delete_document(user_id: str, document_id: str) -> Dict[str, Any]:
    """Delete a document from Vespa"""
    if not vespa_client:
        raise ServiceError(
            "Service not initialized", code=ErrorCode.SERVICE_UNAVAILABLE
        )

    try:
        result = await vespa_client.delete_document(document_id, user_id)
        return {"status": "success", "document_id": document_id, "deleted": result}

    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise ServiceError(
            "Document deletion failed",
            code=ErrorCode.SERVICE_ERROR,
            details={"error": str(e)},
        )


@app.get("/document/{user_id}/{document_id}")
async def get_document(user_id: str, document_id: str) -> Dict[str, Any]:
    """Get a document from Vespa"""
    if not vespa_client:
        raise ServiceError(
            "Service not initialized", code=ErrorCode.SERVICE_UNAVAILABLE
        )

    try:
        document = await vespa_client.get_document(document_id, user_id)
        if document is None:
            raise NotFoundError("Document", document_id)

        return {"status": "success", "document": document}

    except (NotFoundError, ServiceError):
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise ServiceError(
            "Document retrieval failed",
            code=ErrorCode.SERVICE_ERROR,
            details={"error": str(e)},
        )


@app.get("/search/{user_id}")
async def search_documents(
    user_id: str, query: str = "", limit: int = 10
) -> Dict[str, Any]:
    """Search documents for a user"""
    if not vespa_client:
        raise ServiceError(
            "Service not initialized", code=ErrorCode.SERVICE_UNAVAILABLE
        )

    try:
        results = await vespa_client.search_documents(query, user_id, limit)
        return {
            "status": "success",
            "query": query,
            "user_id": user_id,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise ServiceError(
            "Document search failed",
            code=ErrorCode.SERVICE_ERROR,
            details={"error": str(e)},
        )


@app.get("/stats/{user_id}")
async def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Get statistics for a user"""
    if not vespa_client:
        raise ServiceError(
            "Service not initialized", code=ErrorCode.SERVICE_UNAVAILABLE
        )

    try:
        document_count = await vespa_client.get_document_count(user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "document_count": document_count,
        }

    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise ServiceError(
            "User stats retrieval failed",
            code=ErrorCode.SERVICE_ERROR,
            details={"error": str(e)},
        )


async def _post_process_document(document_id: str, user_id: str) -> None:
    """Post-process a document after ingestion"""
    try:
        logger.info(f"Post-processing document {document_id} for user {user_id}")
        # Add any post-processing logic here
        # For example: update search indices, trigger notifications, etc.
    except Exception as e:
        logger.error(f"Error in post-processing document {document_id}: {e}")


async def _post_process_batch(successful_docs: int, failed_docs: int) -> None:
    """Post-process a batch of documents"""
    try:
        logger.info(
            f"Post-processing batch: {successful_docs} successful, {failed_docs} failed"
        )
        # Add any batch post-processing logic here
        # For example: update analytics, send notifications, etc.
    except Exception as e:
        logger.error(f"Error in batch post-processing: {e}")


@app.get("/debug/pubsub")
async def debug_pubsub_status() -> Dict[str, Any]:
    """Debug endpoint to check Pub/Sub consumer status"""
    if not pubsub_consumer:
        return {"status": "error", "message": "Pub/Sub consumer not initialized"}

    try:
        stats = pubsub_consumer.get_stats()
        return {
            "status": "success",
            "pubsub_consumer": stats,
            "settings": {
                "project_id": pubsub_consumer.settings.pubsub_project_id,
                "emulator_host": pubsub_consumer.settings.pubsub_emulator_host,
                "enable_consumer": pubsub_consumer.settings.enable_pubsub_consumer,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/debug/pubsub/trigger")
async def debug_trigger_pubsub_processing(
    api_key: str = Depends(check_rate_limit),
) -> Dict[str, Any]:
    """Debug endpoint to manually trigger Pub/Sub message processing"""
    if not pubsub_consumer:
        return {"status": "error", "message": "Pub/Sub consumer not initialized"}

    try:
        # Check if there are any pending messages in batches
        pending_messages = {}
        for topic_name, batch in pubsub_consumer.message_batches.items():
            if batch:
                pending_messages[topic_name] = len(batch)

        if not pending_messages:
            return {
                "status": "info",
                "message": "No pending messages to process",
                "pending_messages": pending_messages,
            }

        # Process all pending batches
        results = {}
        for topic_name, config in pubsub_consumer.topics.items():
            if pubsub_consumer.message_batches[topic_name]:
                try:
                    await pubsub_consumer._process_batch(topic_name, config)
                    results[topic_name] = "processed"
                except Exception as e:
                    results[topic_name] = f"error: {str(e)}"

        return {
            "status": "success",
            "message": "Manually triggered batch processing",
            "pending_messages": pending_messages,
            "processing_results": results,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/debug/vespa")
async def debug_vespa_status() -> Dict[str, Any]:
    """Debug endpoint to check Vespa connection and stats"""
    if not vespa_client:
        return {"status": "error", "message": "Vespa client not initialized"}

    try:
        # Test Vespa connection
        connection_ok = await vespa_client.test_connection()

        # Get document count for test user
        test_user_id = "trybriefly@outlook.com"
        try:
            doc_count = await vespa_client.get_document_count(test_user_id)
        except Exception as e:
            doc_count = f"error: {str(e)}"

        return {
            "status": "success",
            "vespa_connection": connection_ok,
            "vespa_endpoint": vespa_client.endpoint,
            "test_user_document_count": doc_count,
            "test_user_id": test_user_id,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
