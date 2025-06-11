import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import history_manager
from api import router
from fastapi import FastAPI
from fastapi.responses import JSONResponse
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
    await history_manager.init_db()

    yield  # The application runs here

    # Shutdown: Clean up connections
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
async def health_check() -> JSONResponse:
    try:
        # Simple query to verify database connection
        async with history_manager.async_session() as session:
            result = await session.execute(select(history_manager.Thread))
            threads = result.scalars().all()
            count = len(threads)

        return JSONResponse(
            content={
                "status": "ok",
                "service": "chat-service",
                "database": "connected",
                "threads_count": count,
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
