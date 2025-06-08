import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import history_manager
from .api import router

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
    # Startup: Ensure the database is created and connected
    await history_manager.database.connect()
    # Create tables if they don't exist
    engine = history_manager.sqlalchemy.create_engine(history_manager.DATABASE_URL)
    history_manager.metadata.create_all(engine)

    yield  # The application runs here

    # Shutdown: Clean up the connection
    await history_manager.database.disconnect()


app = FastAPI(title="Chat Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/")
async def health_check() -> JSONResponse:
    try:
        # Simple query to verify database connection
        count = await history_manager.Thread.objects.count()
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
