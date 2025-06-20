import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import select

from services.chat import history_manager
from services.chat.api import router
from services.chat.settings import get_settings
from services.common.logging_config import (
    create_request_logging_middleware,
    log_service_shutdown,
    log_service_startup,
    setup_service_logging,
)

# Set up centralized logging
setup_service_logging(service_name="chat-service", log_level="INFO", log_format="json")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: Ensure the database is created and tables exist
    log_service_startup(
        "chat-service",
        api_frontend_chat_key=(
            "configured" if get_settings().api_frontend_chat_key else "missing"
        ),
        api_chat_user_key=(
            "configured" if get_settings().api_chat_user_key else "missing"
        ),
        api_chat_office_key=(
            "configured" if get_settings().api_chat_office_key else "missing"
        ),
        user_management_service_url=get_settings().user_management_service_url,
        office_service_url=get_settings().office_service_url,
    )

    # Validate API keys for incoming and outgoing service calls
    if not get_settings().api_frontend_chat_key:
        logger.warning(
            "API_FRONTEND_CHAT_KEY not configured - frontend authentication will fail"
        )
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
    log_service_shutdown("chat-service")
    engine = history_manager.get_engine()
    await engine.dispose()


app = FastAPI(title="Chat Service", version="0.1.0", lifespan=lifespan)

# Add centralized request logging middleware
app.middleware("http")(create_request_logging_middleware())


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
            "api_frontend_chat_key": (
                "configured" if get_settings().api_frontend_chat_key else "missing"
            ),
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
