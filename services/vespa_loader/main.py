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
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from services.common.http_errors import (
    AuthError,
    ErrorCode,
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
from services.vespa_loader.content_normalizer import ContentNormalizer
from services.vespa_loader.embeddings import EmbeddingGenerator
from services.vespa_loader.ingest_service import ingest_document_service
from services.vespa_loader.pubsub_consumer import PubSubConsumer
from services.vespa_loader.vespa_client import VespaClient
from services.vespa_loader.vespa_types import VespaDocumentType

# Setup telemetry
setup_telemetry("vespa-loader", "1.0.0")

# Get logger and tracer for this module - will be configured in lifespan
logger = get_logger(__name__)
tracer = get_tracer(__name__)

# Global service instances
vespa_client: VespaClient | None = None
content_normalizer: ContentNormalizer | None = None
embedding_generator: EmbeddingGenerator | None = None
pubsub_consumer: PubSubConsumer | None = None


# The ingest_document_service function has been moved to ingest_service.py
# to avoid circular imports


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
    global vespa_client, content_normalizer, embedding_generator, pubsub_consumer

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

    # Start Pub/Sub consumer if not disabled
    if not settings.disable_pubsub_consumer:
        try:
            pubsub_consumer = PubSubConsumer(
                settings,
                vespa_client,
                content_normalizer,
                embedding_generator,
            )
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
                "endpoint": vespa_client.vespa_endpoint,
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
    api_key: str = Depends(check_rate_limit),
) -> Dict[str, Any]:
    """Ingest a document into Vespa"""
    try:
        # Convert Dict to VespaDocumentType
        from services.vespa_loader.vespa_types import VespaDocumentType

        # Create a VespaDocumentType from the input data
        vespa_document = VespaDocumentType(
            id=document_data.get("id", ""),
            user_id=document_data.get("user_id", ""),
            type=document_data.get("type", "unknown"),
            provider=document_data.get("provider", "unknown"),
            subject=document_data.get("subject", ""),
            body=document_data.get("body", ""),
            from_address=document_data.get("from_address", ""),
            to_addresses=document_data.get("to_addresses", []),
            thread_id=document_data.get("thread_id"),
            folder=document_data.get("folder"),
            created_at=document_data.get("created_at"),
            updated_at=document_data.get("updated_at"),
            metadata=document_data.get("metadata"),
            content_chunks=document_data.get("content_chunks"),
            quoted_content=document_data.get("quoted_content"),
            thread_summary=document_data.get("thread_summary"),
            search_text=document_data.get("search_text"),
        )

        # Call the shared service function
        result = await ingest_document_service(
            vespa_document,
            vespa_client,
            content_normalizer,
            embedding_generator,
        )

        # Run post-processing synchronously since we removed background tasks
        await _post_process_document(
            document_id=document_data["id"],
            user_id=document_data["user_id"],
        )

        # Convert result to dict for API response
        return result.model_dump()

    except ValidationError:
        # Re-raise ValidationError to preserve specific error details
        raise
    except ServiceError:
        # Re-raise ServiceError to preserve specific error details
        raise
    except Exception as e:
        logger.error(f"Unexpected error ingesting document: {e}")
        raise ServiceError(
            "Document ingestion failed",
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
                "disable_consumer": pubsub_consumer.settings.disable_pubsub_consumer,
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
        # Get current consumer status
        stats = pubsub_consumer.get_stats()

        return {
            "status": "success",
            "message": "Pub/Sub consumer status retrieved",
            "consumer_stats": stats,
            "topics": list(pubsub_consumer.topics.keys()),
            "note": "This service processes messages individually, not in batches",
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
