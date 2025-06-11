import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import history_manager
from api import router
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from settings import settings
from sqlmodel import select

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

    # Validate required configuration
    if not settings.api_key_chat:
        logger.error("API_KEY_CHAT is required but not configured")
        raise RuntimeError("API_KEY_CHAT is required")

    await history_manager.init_db()

    yield  # The application runs here

    # Shutdown: Clean up connections
    logger.info("Shutting down Chat Service")
    await history_manager.engine.dispose()


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
            "api_key_chat": "configured" if settings.api_key_chat else "missing",
            "api_key_user_management": (
                "configured" if settings.api_key_user_management else "missing"
            ),
            "api_key_office": "configured" if settings.api_key_office else "missing",
            "user_management_service_url": settings.user_management_service_url,
            "office_service_url": settings.office_service_url,
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
