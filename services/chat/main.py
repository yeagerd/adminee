import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import select

from services.chat import history_manager
from services.chat.api import router
from services.chat.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Silence verbose logs from specific modules
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("Logging is configured")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: Ensure the database is created and tables exist
    logger.info("Starting Chat Service with Multi-Agent Workflow")

    # Validate API keys for outgoing service calls (optional - will warn if missing)
    if not get_settings().api_chat_user_key:
        logger.warning(
            "API_CHAT_USER_KEY not configured - user management calls will fail"
        )
    if not get_settings().api_chat_office_key:
        logger.warning(
            "API_CHAT_OFFICE_KEY not configured - office service calls will fail"
        )

    await history_manager.init_db()

    yield  # The application runs here

    # Shutdown: Clean up connections
    logger.info("Shutting down Chat Service")
    engine = history_manager.get_engine()
    await engine.dispose()


app = FastAPI(title="Chat Service", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all incoming requests and responses.

    This provides detailed logging for debugging failed requests,
    especially useful for 404 errors and endpoint mismatches.
    """
    import time
    import uuid

    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Log incoming request
    logger.info(
        f"[{request_id}] Incoming request: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params) if request.query_params else None,
            "client_ip": (
                getattr(request.client, "host", "unknown")
                if request.client
                else "unknown"
            ),
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
        },
    )

    # Read and log request body for POST/PUT requests (but don't consume the body)
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # Get the request body without consuming the stream
            body = await request.body()
            if body:
                # Only log first 500 chars to avoid massive logs
                body_preview = body.decode("utf-8")[:500]
                if len(body) > 500:
                    body_preview += "... (truncated)"
                logger.info(
                    f"[{request_id}] Request body preview: {body_preview}",
                    extra={"request_id": request_id, "body_size": len(body)},
                )
        except Exception as e:
            logger.warning(f"[{request_id}] Could not read request body: {e}")

    # Process the request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Log response
    log_level = logging.ERROR if response.status_code >= 400 else logging.INFO
    status_emoji = "❌" if response.status_code >= 400 else "✅"

    logger.log(
        log_level,
        f"[{request_id}] {status_emoji} Response: {response.status_code} ({process_time:.3f}s)",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": process_time,
            "method": request.method,
            "path": request.url.path,
        },
    )

    # Special logging for 404 errors to help with debugging
    if response.status_code == 404:
        available_routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                for method in route.methods:
                    if method != "HEAD":  # Skip HEAD methods for clarity
                        available_routes.append(f"{method} {route.path}")

        logger.error(
            f"[{request_id}] 🔍 404 DEBUG - Requested: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "requested_endpoint": f"{request.method} {request.url.path}",
                "available_endpoints": available_routes,
                "suggestion": "Check if the endpoint path and HTTP method are correct",
            },
        )

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.

    Logs the error with full traceback and returns a generic error response
    to avoid exposing internal details in production.
    """
    import uuid
    from datetime import datetime, timezone

    request_id = str(uuid.uuid4())

    logger.error(
        "Unhandled exception occurred",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "request_id": request_id,
        },
        exc_info=True,  # This includes the full traceback
    )

    return JSONResponse(
        status_code=500,
        content={
            "type": "internal_error",
            "message": "An unexpected error occurred. Please try again later.",
            "details": {
                "error_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
                "code": "INTERNAL_SERVER_ERROR",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
        },
    )


@app.get("/ready")
async def ready_check() -> JSONResponse:
    return JSONResponse(
        content={
            "status": "ok",
            "service": "chat-service",
        }
    )


app.include_router(router)


@app.get("/")
@app.get("/health")
async def health_check() -> JSONResponse:
    try:
        # Simple query to verify database connection
        async with history_manager.get_async_session_factory()() as session:
            result = await session.execute(select(history_manager.Thread))
            threads = result.scalars().all()
            count = len(threads)

        # Check service configuration
        config_status = {
            "api_chat_user_key": (
                "configured" if get_settings().api_chat_user_key else "missing"
            ),
            "api_chat_office_key": (
                "configured" if get_settings().api_chat_office_key else "missing"
            ),
            "user_management_service_url": get_settings().user_management_service_url,
            "office_service_url": get_settings().office_service_url,
        }

        return JSONResponse(
            content={
                "status": "ok",
                "service": "chat-service",
                "agent_mode": "multi-agent-workflow",
                "database": "connected",
                "threads_count": count,
                "configuration": config_status,
            }
        )
    except Exception as e:
        logger.error(
            "Health check failed with exception",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,  # This includes the full traceback
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": f"Database connection error: {str(e)}",
            },
        )
