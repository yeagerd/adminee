#!/usr/bin/env python3
"""
Vespa Query Service - Query interface for hybrid search capabilities
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from services.vespa_query.search_engine import SearchEngine
from services.vespa_query.query_builder import QueryBuilder
from services.vespa_query.result_processor import ResultProcessor
from services.vespa_query.settings import Settings
from services.common.logging_config import setup_service_logging, get_logger, create_request_logging_middleware
from services.common.http_errors import register_briefly_exception_handlers
from services.common.telemetry import setup_telemetry, get_tracer

# Setup service logging
setup_service_logging(
    service_name="vespa-query",
    log_level="INFO",
    log_format="json"
)

# Setup telemetry
setup_telemetry("vespa-query", "1.0.0")

# Get logger and tracer for this module
logger = get_logger(__name__)
tracer = get_tracer(__name__)

# Global service instances
search_engine: SearchEngine | None = None
query_builder: QueryBuilder | None = None
result_processor: ResultProcessor | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global search_engine, query_builder, result_processor
    
    # Startup
    logger.info("Starting Vespa Query Service...")
    
    # Initialize settings
    settings = Settings()
    
    # Initialize components
    search_engine = SearchEngine(settings.vespa_endpoint)
    query_builder = QueryBuilder()
    result_processor = ResultProcessor()
    
    # Test Vespa connectivity
    try:
        await search_engine.test_connection()
        logger.info("Vespa connection test successful")
    except Exception as e:
        logger.error(f"Vespa connection test failed: {e}")
        raise
    
    logger.info("Vespa Query Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Vespa Query Service...")
    if search_engine:
        await search_engine.close()
    logger.info("Vespa Query Service shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Vespa Query Service",
    description="Query interface for hybrid search capabilities",
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
    return {
        "status": "healthy",
        "service": "vespa-query",
        "version": "1.0.0"
    }

@app.get("/search")
async def search_documents(
    query: str = Query(..., description="Search query"),
    user_id: str = Query(..., description="User ID for data isolation"),
    ranking_profile: str = Query("hybrid", description="Ranking profile (hybrid, bm25, semantic)"),
    max_hits: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    source_types: Optional[str] = Query(None, description="Comma-separated source types to filter"),
    providers: Optional[str] = Query(None, description="Comma-separated providers to filter"),
    date_from: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date filter (ISO format)"),
    folders: Optional[str] = Query(None, description="Comma-separated folders to filter"),
    include_facets: bool = Query(True, description="Whether to include faceted results")
):
    """Search documents using hybrid search"""
    with tracer.start_as_current_span("api.search_documents") as span:
        span.set_attribute("api.query", query)
        span.set_attribute("api.user_id", user_id)
        span.set_attribute("api.ranking_profile", ranking_profile)
        span.set_attribute("api.max_hits", max_hits)
        span.set_attribute("api.offset", offset)
        
        if not all([search_engine, query_builder, result_processor]):
            span.set_attribute("api.error", "Service not ready")
            raise HTTPException(status_code=503, detail="Service not ready")
        
        try:
            # Parse filter parameters
            source_type_list = source_types.split(",") if source_types else None
            provider_list = providers.split(",") if providers else None
            folder_list = folders.split(",") if folders else None
            
            span.set_attribute("api.source_types", str(source_type_list) if source_type_list else "none")
            span.set_attribute("api.providers", str(provider_list) if provider_list else "none")
            span.set_attribute("api.folders", str(folder_list) if folder_list else "none")
            
            # Build search query
            search_query = query_builder.build_search_query(
                query=query,
                user_id=user_id,
                ranking_profile=ranking_profile,
                max_hits=max_hits,
                offset=offset,
                source_types=source_type_list,
                providers=provider_list,
                date_from=date_from,
                date_to=date_to,
                folders=folder_list,
                include_facets=include_facets
            )
            
            # Execute search
            search_results = await search_engine.search(search_query)
            
            # Process and format results
            processed_results = result_processor.process_search_results(
                search_results,
                query=query,
                user_id=user_id,
                include_facets=include_facets
            )
            
            span.set_attribute("api.search.success", True)
            span.set_attribute("api.results.total_hits", processed_results.get("total_hits", 0))
            return processed_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            span.set_attribute("api.search.success", False)
            span.set_attribute("api.error.message", str(e))
            span.record_exception(e)
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/autocomplete")
async def autocomplete_search(
    query: str = Query(..., description="Partial search query"),
    user_id: str = Query(..., description="User ID for data isolation"),
    max_suggestions: int = Query(5, ge=1, le=20, description="Maximum number of suggestions")
):
    """Get autocomplete suggestions for search queries"""
    if not all([search_engine, query_builder, result_processor]):
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Build autocomplete query
        autocomplete_query = query_builder.build_autocomplete_query(
            query=query,
            user_id=user_id,
            max_suggestions=max_suggestions
        )
        
        # Execute autocomplete search
        autocomplete_results = await search_engine.autocomplete(autocomplete_query)
        
        # Process results
        suggestions = result_processor.process_autocomplete_results(autocomplete_results)
        
        return {
            "query": query,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Autocomplete search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/similar")
async def find_similar_documents(
    document_id: str = Query(..., description="Document ID to find similar documents for"),
    user_id: str = Query(..., description="User ID for data isolation"),
    max_hits: int = Query(10, ge=1, le=50, description="Maximum number of similar documents"),
    similarity_threshold: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")
):
    """Find documents similar to a given document"""
    if not all([search_engine, query_builder, result_processor]):
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Build similarity query
        similarity_query = query_builder.build_similarity_query(
            document_id=document_id,
            user_id=user_id,
            max_hits=max_hits,
            similarity_threshold=similarity_threshold
        )
        
        # Execute similarity search
        similarity_results = await search_engine.find_similar(similarity_query)
        
        # Process results
        processed_results = result_processor.process_similarity_results(
            similarity_results,
            document_id=document_id,
            user_id=user_id
        )
        
        return processed_results
        
    except Exception as e:
        logger.error(f"Similarity search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/facets")
async def get_search_facets(
    user_id: str = Query(..., description="User ID for data isolation"),
    source_types: Optional[str] = Query(None, description="Comma-separated source types to filter"),
    providers: Optional[str] = Query(None, description="Comma-separated providers to filter"),
    date_from: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date filter (ISO format)")
):
    """Get faceted search results for browsing"""
    if not all([search_engine, query_builder, result_processor]):
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Parse filter parameters
        source_type_list = source_types.split(",") if source_types else None
        provider_list = providers.split(",") if providers else None
        
        # Build facets query
        facets_query = query_builder.build_facets_query(
            user_id=user_id,
            source_types=source_type_list,
            providers=provider_list,
            date_from=date_from,
            date_to=date_to
        )
        
        # Execute facets search
        facets_results = await search_engine.get_facets(facets_query)
        
        # Process results
        processed_facets = result_processor.process_facets_results(facets_results)
        
        return processed_facets
        
    except Exception as e:
        logger.error(f"Facets search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/trending")
async def get_trending_topics(
    user_id: str = Query(..., description="User ID for data isolation"),
    time_window: str = Query("7d", description="Time window (1d, 7d, 30d, 90d)"),
    max_topics: int = Query(10, ge=1, le=50, description="Maximum number of trending topics")
):
    """Get trending topics based on recent document activity"""
    if not all([search_engine, query_builder, result_processor]):
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Build trending query
        trending_query = query_builder.build_trending_query(
            user_id=user_id,
            time_window=time_window,
            max_topics=max_topics
        )
        
        # Execute trending search
        trending_results = await search_engine.get_trending(trending_query)
        
        # Process results
        processed_trending = result_processor.process_trending_results(trending_results)
        
        return processed_trending
        
    except Exception as e:
        logger.error(f"Trending search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/analytics")
async def get_search_analytics(
    user_id: str = Query(..., description="User ID for data isolation"),
    date_from: str = Query(..., description="Start date (ISO format)"),
    date_to: str = Query(..., description="End date (ISO format)")
):
    """Get search analytics and insights"""
    if not all([search_engine, query_builder, result_processor]):
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Build analytics query
        analytics_query = query_builder.build_analytics_query(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to
        )
        
        # Execute analytics search
        analytics_results = await search_engine.get_analytics(analytics_query)
        
        # Process results
        processed_analytics = result_processor.process_analytics_results(analytics_results)
        
        return processed_analytics
        
    except Exception as e:
        logger.error(f"Analytics search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
        log_level="info"
    )
