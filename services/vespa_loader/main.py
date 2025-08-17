#!/usr/bin/env python3
"""
Vespa Loader Service - Consumes email data and indexes into Vespa
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from services.vespa_loader.vespa_client import VespaClient
from services.vespa_loader.content_normalizer import ContentNormalizer
from services.vespa_loader.embeddings import EmbeddingGenerator
from services.vespa_loader.mapper import DocumentMapper
from services.vespa_loader.pubsub_consumer import PubSubConsumer
from services.vespa_loader.settings import Settings
from services.common.logging_config import setup_service_logging, get_logger, create_request_logging_middleware
from services.common.http_errors import register_briefly_exception_handlers
from services.common.telemetry import setup_telemetry, get_tracer

# Setup service logging
setup_service_logging(
    service_name="vespa-loader",
    log_level="INFO",
    log_format="json"
)

# Setup telemetry
setup_telemetry("vespa-loader", "1.0.0")

# Get logger and tracer for this module
logger = get_logger(__name__)
tracer = get_tracer(__name__)

# Global service instances
vespa_client: VespaClient | None = None
content_normalizer: ContentNormalizer | None = None
embedding_generator: EmbeddingGenerator | None = None
document_mapper: DocumentMapper | None = None
pubsub_consumer: PubSubConsumer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global vespa_client, content_normalizer, embedding_generator, document_mapper, pubsub_consumer
    
    # Startup
    logger.info("Starting Vespa Loader Service...")
    
    # Initialize settings
    settings = Settings()
    
    # Initialize components
    vespa_client = VespaClient(settings.vespa_endpoint)
    content_normalizer = ContentNormalizer()
    embedding_generator = EmbeddingGenerator(settings.embedding_model)
    document_mapper = DocumentMapper()
    
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

# Create FastAPI app
app = FastAPI(
    title="Vespa Loader Service",
    description="Service for loading and indexing documents into Vespa",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_briefly_exception_handlers(app)

# Add request logging middleware
app.middleware("http")(create_request_logging_middleware())

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = "healthy"
    
    # Check Vespa connectivity
    vespa_healthy = vespa_client is not None
    if not vespa_healthy:
        health_status = "degraded"
    
    # Check Pub/Sub consumer status
    pubsub_healthy = pubsub_consumer is not None and pubsub_consumer.running if pubsub_consumer else False
    
    return {
        "status": health_status,
        "service": "vespa-loader",
        "version": "1.0.0",
        "components": {
            "vespa": {
                "status": "healthy" if vespa_healthy else "unavailable",
                "endpoint": vespa_client.vespa_endpoint if vespa_client else None
            },
            "pubsub_consumer": {
                "status": "healthy" if pubsub_healthy else "unavailable",
                "enabled": pubsub_consumer is not None,
                "running": pubsub_consumer.running if pubsub_consumer else False
            }
        }
    }

@app.post("/ingest")
async def ingest_document(document_data: dict):
    """Ingest a document into Vespa"""
    with tracer.start_as_current_span("api.ingest_document") as span:
        span.set_attribute("api.document.type", document_data.get("source_type", "unknown"))
        span.set_attribute("api.document.user_id", document_data.get("user_id", "unknown"))
        
        if not all([vespa_client, content_normalizer, embedding_generator, document_mapper]):
            span.set_attribute("api.error", "Service not ready")
            raise HTTPException(status_code=503, detail="Service not ready")
        
        try:
            # Process the document
            processed_doc = await process_document(document_data)
            
            # Index into Vespa
            result = await vespa_client.index_document(processed_doc)
            
            span.set_attribute("api.ingest.success", True)
            span.set_attribute("api.document.id", result.get("id"))
            
            return {
                "status": "success",
                "document_id": result.get("id"),
                "message": "Document indexed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest document: {e}")
            span.set_attribute("api.ingest.success", False)
            span.set_attribute("api.error.message", str(e))
            span.record_exception(e)
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/batch")
async def ingest_batch_documents(documents: list[dict]):
    """Ingest multiple documents in batch"""
    if not all([vespa_client, content_normalizer, embedding_generator, document_mapper]):
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        results = []
        
        # Process documents in parallel
        import asyncio
        tasks = [process_document(doc) for doc in documents]
        processed_docs = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Index documents in batch
        for i, processed_doc in enumerate(processed_docs):
            if isinstance(processed_doc, Exception):
                results.append({
                    "index": i,
                    "status": "error",
                    "error": str(processed_doc)
                })
            else:
                try:
                    result = await vespa_client.index_document(processed_doc)
                    results.append({
                        "index": i,
                        "status": "success",
                        "document_id": result.get("id")
                    })
                except Exception as e:
                    results.append({
                        "index": i,
                        "status": "error",
                        "error": str(e)
                    })
        
        return {
            "status": "completed",
            "total_documents": len(documents),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest batch documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{user_id}/{doc_id}")
async def delete_document(user_id: str, doc_id: str):
    """Delete a document from Vespa"""
    if not vespa_client:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        result = await vespa_client.delete_document(user_id, doc_id)
        return {
            "status": "success",
            "message": "Document deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{user_id}/{doc_id}")
async def get_document(user_id: str, doc_id: str):
    """Retrieve a document from Vespa"""
    if not vespa_client:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        document = await vespa_client.get_document(user_id, doc_id)
        return document
        
    except Exception as e:
        logger.error(f"Failed to retrieve document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    stats = {
        "service": "vespa-loader",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vespa": {
            "endpoint": vespa_client.vespa_endpoint if vespa_client else None,
            "connected": vespa_client is not None
        }
    }
    
    if pubsub_consumer:
        stats["pubsub_consumer"] = pubsub_consumer.get_stats()
    
    return stats

async def process_document(document_data: dict) -> dict:
    """Process a document for Vespa indexing"""
    try:
        # Map office service format to Vespa format
        vespa_doc = document_mapper.map_to_vespa(document_data)
        
        # Normalize content (HTML to Markdown, etc.)
        if "content" in vespa_doc:
            vespa_doc["content"] = content_normalizer.normalize(vespa_doc["content"])
        
        if "search_text" in vespa_doc:
            vespa_doc["search_text"] = content_normalizer.normalize(vespa_doc["search_text"])
        
        # Generate embeddings for semantic search
        if "search_text" in vespa_doc and vespa_doc["search_text"]:
            embedding = await embedding_generator.generate_embedding(vespa_doc["search_text"])
            vespa_doc["embedding"] = embedding
        
        return vespa_doc
        
    except Exception as e:
        logger.error(f"Failed to process document: {e}")
        raise

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
