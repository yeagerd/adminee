#!/usr/bin/env python3
"""
Vespa Loader Service - Consumes email data and indexes into Vespa
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Any, Dict, Union, AsyncGenerator

from services.common.logging_config import setup_service_logging, get_logger, create_request_logging_middleware, log_service_startup, log_service_shutdown
from services.common.http_errors import register_briefly_exception_handlers
from services.common.telemetry import setup_telemetry, get_tracer

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
        log_format=settings.log_format
    )
    
    # Now import modules that use logging after logging is configured
    from services.vespa_loader.vespa_client import VespaClient
    from services.vespa_loader.content_normalizer import ContentNormalizer
    from services.vespa_loader.embeddings import EmbeddingGenerator
    from services.vespa_loader.mapper import DocumentMapper
    from services.vespa_loader.pubsub_consumer import PubSubConsumer
    
    # Log service startup
    log_service_startup(
        "vespa-loader",
        version="1.0.0",
        environment="development"
    )
    
    # Startup
    logger.info("Starting Vespa Loader Service...")
    
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
    
    # Log service shutdown
    log_service_shutdown("vespa-loader")

# Create FastAPI app
app = FastAPI(
    title="Vespa Loader Service",
    description="Consumes email data and indexes into Vespa",
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

# Add request logging middleware
app.add_middleware(create_request_logging_middleware())

# Register exception handlers
register_briefly_exception_handlers(app)

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "vespa-loader"}

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {"message": "Vespa Loader Service", "version": "1.0.0"}

@app.post("/ingest")
async def ingest_document(
    document_data: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Ingest a document into Vespa"""
    if not all([vespa_client, content_normalizer, embedding_generator, document_mapper]):
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        # Validate document data
        if not document_data.get("id") or not document_data.get("user_id"):
            raise HTTPException(status_code=400, detail="Document ID and user_id are required")
        
        # Map document to Vespa format
        if not document_mapper:
            raise HTTPException(status_code=500, detail="Document mapper not initialized")
        vespa_document = document_mapper.map_to_vespa(document_data)
        
        # Normalize content
        if vespa_document.get("content") and content_normalizer:
            vespa_document["content"] = content_normalizer.normalize(vespa_document["content"])
        
        # Generate embeddings if content exists
        if vespa_document.get("content") and embedding_generator:
            try:
                embedding = await embedding_generator.generate_embedding(vespa_document["content"])
                vespa_document["embedding"] = embedding
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
                # Continue without embedding
        
        # Index document in Vespa
        if not vespa_client:
            raise HTTPException(status_code=500, detail="Vespa client not initialized")
        result = await vespa_client.index_document(vespa_document)
        
        # Add background task for post-processing if needed
        background_tasks.add_task(
            _post_process_document,
            document_id=document_data["id"],
            user_id=document_data["user_id"]
        )
        
        return {
            "status": "success",
            "document_id": document_data["id"],
            "vespa_result": result
        }
        
    except Exception as e:
        logger.error(f"Error ingesting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/batch")
async def ingest_batch_documents(
    documents: list[Dict[str, Any]],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Ingest multiple documents in batch"""
    if not all([vespa_client, content_normalizer, embedding_generator, document_mapper]):
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        results = []
        errors = []
        
        for doc in documents:
            try:
                # Map document to Vespa format
                if not document_mapper:
                    raise HTTPException(status_code=500, detail="Document mapper not initialized")
                vespa_document = document_mapper.map_to_vespa(doc)
                
                # Normalize content
                if vespa_document.get("content") and content_normalizer:
                    vespa_document["content"] = content_normalizer.normalize(vespa_document["content"])
                
                # Generate embeddings if content exists
                if vespa_document.get("content") and embedding_generator:
                    try:
                        embedding = await embedding_generator.generate_embedding(vespa_document["content"])
                        vespa_document["embedding"] = embedding
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for document {doc.get('id')}: {e}")
                        # Continue without embedding
                
                # Index document in Vespa
                if not vespa_client:
                    raise HTTPException(status_code=500, detail="Vespa client not initialized")
                result = await vespa_client.index_document(vespa_document)
                
                results.append({
                    "id": doc.get("id"),
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Error processing document {doc.get('id', 'unknown')}: {e}")
                errors.append({
                    "id": doc.get("id"),
                    "status": "error",
                    "error": str(e)
                })
        
        # Add background task for batch post-processing
        if results:
            background_tasks.add_task(
                _post_process_batch,
                successful_docs=len(results),
                failed_docs=len(errors)
            )
        
        return {
            "status": "completed",
            "total_documents": len(documents),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error in batch ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/document/{user_id}/{document_id}")
async def delete_document(user_id: str, document_id: str) -> Dict[str, Any]:
    """Delete a document from Vespa"""
    if not vespa_client:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        result = await vespa_client.delete_document(document_id, user_id)
        return {
            "status": "success",
            "document_id": document_id,
            "deleted": result
        }
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/document/{user_id}/{document_id}")
async def get_document(user_id: str, document_id: str) -> Dict[str, Any]:
    """Get a document from Vespa"""
    if not vespa_client:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        document = await vespa_client.get_document(document_id, user_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "status": "success",
            "document": document
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/{user_id}")
async def search_documents(
    user_id: str,
    query: str = "",
    limit: int = 10
) -> Dict[str, Any]:
    """Search documents for a user"""
    if not vespa_client:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        results = await vespa_client.search_documents(query, user_id, limit)
        return {
            "status": "success",
            "query": query,
            "user_id": user_id,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/{user_id}")
async def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Get statistics for a user"""
    if not vespa_client:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        document_count = await vespa_client.get_document_count(user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "document_count": document_count
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        logger.info(f"Post-processing batch: {successful_docs} successful, {failed_docs} failed")
        # Add any batch post-processing logic here
        # For example: update analytics, send notifications, etc.
    except Exception as e:
        logger.error(f"Error in batch post-processing: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
