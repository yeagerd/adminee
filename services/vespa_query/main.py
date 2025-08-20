#!/usr/bin/env python3
"""
Vespa Query Service - Query interface for hybrid search capabilities
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware

from services.common.http_errors import register_briefly_exception_handlers
from services.common.logging_config import (
    create_request_logging_middleware,
    get_logger,
    log_service_shutdown,
    log_service_startup,
    setup_service_logging,
)
from services.common.telemetry import get_tracer, setup_telemetry

# Setup telemetry
setup_telemetry("vespa-query", "1.0.0")

# Get logger and tracer for this module - will be configured in lifespan
logger = get_logger(__name__)
tracer = get_tracer(__name__)

# Global service instances
search_engine: Optional[Any] = None
query_builder: Optional[Any] = None
result_processor: Optional[Any] = None


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Verify API key for inter-service communication"""
    from services.vespa_query.settings import Settings
    settings = Settings()
    
    if x_api_key != settings.api_frontend_vespa_query_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage service lifecycle"""
    global search_engine, query_builder, result_processor

    # Initialize settings
    from services.vespa_query.settings import Settings

    settings = Settings()

    # Set up centralized logging
    setup_service_logging(
        service_name="vespa-query",
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    # Now import modules that use logging after logging is configured
    from services.vespa_query.query_builder import QueryBuilder
    from services.vespa_query.result_processor import ResultProcessor
    from services.vespa_query.search_engine import SearchEngine

    # Log service startup
    log_service_startup("vespa-query", version="1.0.0", environment="development")

    # Startup
    logger.info("Starting Vespa Query Service...")

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

    # Log service shutdown
    log_service_shutdown("vespa-query")


# Create FastAPI app
app = FastAPI(
    title="Vespa Query Service",
    description="Query interface for hybrid search capabilities",
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
app.add_middleware(create_request_logging_middleware())

# Register exception handlers
register_briefly_exception_handlers(app)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "vespa-query"}


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {"message": "Vespa Query Service", "version": "1.0.0"}


@app.post("/search")
async def search(
    query: str = Query(..., description="Search query"),
    user_id: str = Query(..., description="User ID"),
    max_hits: int = Query(10, description="Maximum number of results"),
    offset: int = Query(0, description="Result offset"),
    source_types: Optional[List[str]] = Query(
        None, description="Filter by source types"
    ),
    providers: Optional[List[str]] = Query(None, description="Filter by providers"),
    date_from: Optional[str] = Query(None, description="Start date for filtering"),
    date_to: Optional[str] = Query(None, description="End date for filtering"),
    folders: Optional[List[str]] = Query(None, description="Filter by folders"),
    include_facets: bool = Query(True, description="Include facets in results"),
    api_key: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Execute a search query"""
    if not query_builder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # Build search query
        search_query = query_builder.build_search_query(
            query=query,
            user_id=user_id,
            max_hits=max_hits,
            offset=offset,
            source_types=source_types,
            providers=providers,
            date_from=date_from,
            date_to=date_to,
            folders=folders,
            include_facets=include_facets,
        )

        # Execute search
        if not search_engine:
            raise HTTPException(status_code=500, detail="Search engine not initialized")

        vespa_results = await search_engine.search(search_query)

        # Process results
        if not result_processor:
            raise HTTPException(
                status_code=500, detail="Result processor not initialized"
            )

        processed_results = result_processor.process_search_results(
            vespa_results=vespa_results,
            query=query,
            user_id=user_id,
            include_highlights=True,
            include_facets=include_facets,
        )

        return processed_results

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/autocomplete")
async def autocomplete(
    query: str = Query(..., description="Autocomplete query"),
    user_id: str = Query(..., description="User ID"),
    max_suggestions: int = Query(5, description="Maximum number of suggestions"),
    api_key: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Get autocomplete suggestions"""
    if not query_builder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # Build autocomplete query
        autocomplete_query = query_builder.build_autocomplete_query(
            query=query, user_id=user_id, max_hits=max_suggestions
        )

        # Execute autocomplete
        if not search_engine:
            raise HTTPException(status_code=500, detail="Search engine not initialized")

        vespa_results = await search_engine.autocomplete(autocomplete_query)

        # Process results
        if not result_processor:
            raise HTTPException(
                status_code=500, detail="Result processor not initialized"
            )

        processed_results = result_processor.process_autocomplete_results(
            vespa_results=vespa_results, query=query, user_id=user_id
        )

        return processed_results

    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/similar")
async def find_similar(
    document_id: str = Query(
        ..., description="Document ID to find similar documents for"
    ),
    user_id: str = Query(..., description="User ID"),
    max_hits: int = Query(10, description="Maximum number of similar documents"),
    api_key: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Find similar documents"""
    if not query_builder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # Build similarity query
        similarity_query = query_builder.build_similarity_query(
            document_id=document_id, user_id=user_id, max_hits=max_hits
        )

        # Execute similarity search
        if not search_engine:
            raise HTTPException(status_code=500, detail="Search engine not initialized")

        vespa_results = await search_engine.find_similar(similarity_query)

        # Process results
        if not result_processor:
            raise HTTPException(
                status_code=500, detail="Result processor not initialized"
            )

        processed_results = result_processor.process_similarity_results(
            vespa_results=vespa_results, query=document_id, user_id=user_id
        )

        return processed_results

    except Exception as e:
        logger.error(f"Similarity search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/facets")
async def get_facets(
    user_id: str = Query(..., description="User ID"),
    source_types: Optional[List[str]] = Query(
        None, description="Filter by source types"
    ),
    providers: Optional[List[str]] = Query(None, description="Filter by providers"),
    date_from: Optional[str] = Query(None, description="Start date for filtering"),
    date_to: Optional[str] = Query(None, description="End date for filtering"),
    api_key: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Get facet information"""
    if not query_builder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # Build facets query
        facets_query = query_builder.build_facets_query(
            user_id=user_id,
            source_types=source_types,
            providers=providers,
            date_from=date_from,
            date_to=date_to,
        )

        # Execute facets query
        if not search_engine:
            raise HTTPException(status_code=500, detail="Search engine not initialized")

        vespa_results = await search_engine.get_facets(facets_query)

        # Process results
        if not result_processor:
            raise HTTPException(
                status_code=500, detail="Result processor not initialized"
            )

        processed_results = result_processor.process_facets_results(
            vespa_results=vespa_results, query="facets", user_id=user_id
        )

        return processed_results

    except Exception as e:
        logger.error(f"Facets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trending")
async def get_trending(
    user_id: str = Query(..., description="User ID"),
    time_range: str = Query("7d", description="Time range for trending"),
    max_hits: int = Query(10, description="Maximum number of trending documents"),
    api_key: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Get trending documents"""
    if not query_builder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # Build trending query
        trending_query = query_builder.build_trending_query(
            user_id=user_id, time_range=time_range, max_hits=max_hits
        )

        # Execute trending query
        if not search_engine:
            raise HTTPException(status_code=500, detail="Search engine not initialized")

        vespa_results = await search_engine.get_trending(trending_query)

        # Process results
        if not result_processor:
            raise HTTPException(
                status_code=500, detail="Result processor not initialized"
            )

        processed_results = result_processor.process_trending_results(
            vespa_results=vespa_results, query="trending", user_id=user_id
        )

        return processed_results

    except Exception as e:
        logger.error(f"Trending error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analytics")
async def get_analytics(
    user_id: str = Query(..., description="User ID"),
    time_range: str = Query("30d", description="Time range for analytics"),
    api_key: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Get analytics data"""
    if not query_builder:
        raise HTTPException(status_code=500, detail="Service not initialized")

    try:
        # Build analytics query
        analytics_query = query_builder.build_analytics_query(
            user_id=user_id, time_range=time_range
        )

        # Execute analytics query
        if not search_engine:
            raise HTTPException(status_code=500, detail="Search engine not initialized")

        vespa_results = await search_engine.get_analytics(analytics_query)

        # Process results
        if not result_processor:
            raise HTTPException(
                status_code=500, detail="Result processor not initialized"
            )

        processed_results = result_processor.process_analytics_results(
            vespa_results=vespa_results, query="analytics", user_id=user_id
        )

        return processed_results

    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006)
