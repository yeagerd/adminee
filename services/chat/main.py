import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
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
logger = logging.getLogger(__name__)
logger.info("Logging is configured")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: Ensure the database is created and tables exist
    logger.info("Starting Chat Service")

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
        async with history_manager.async_session() as session:
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
                "database": "connected",
                "threads_count": count,
                "configuration": config_status,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": f"Database connection error: {str(e)}",
            },
        )
