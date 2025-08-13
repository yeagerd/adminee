from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.common.http_errors import register_briefly_exception_handlers
from services.common.logging_config import (
    create_request_logging_middleware,
    get_logger,
    log_service_shutdown,
    log_service_startup,
    setup_service_logging,
)
from services.meetings.api import (
    bookings_router,
    email_router,
    invitations_router,
    polls_router,
    public_router,
    slots_router,
)
from services.meetings.settings import get_settings

# Set up centralized logging - will be initialized in lifespan
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup event logic
    settings = get_settings()

    # Set up centralized logging
    setup_service_logging(
        service_name="meetings",
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    log_service_startup(
        "meetings",
        version="0.1.0",
        environment="development",
    )
    yield
    # Shutdown event logic
    log_service_shutdown("meetings")


app = FastAPI(
    title="Briefly Meetings Service",
    version="0.1.0",
    description="Meeting scheduling and polling microservice for Briefly.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.middleware("http")(create_request_logging_middleware())

# Register standardized exception handlers
register_briefly_exception_handlers(app)

app.include_router(polls_router, prefix="/api/v1/meetings/polls", tags=["polls"])
app.include_router(
    slots_router, prefix="/api/v1/meetings/polls/{poll_id}/slots", tags=["slots"]
)
app.include_router(
    invitations_router,
    prefix="/api/v1/meetings/polls/{poll_id}/send-invitations",
    tags=["invitations"],
)
app.include_router(public_router, prefix="/api/v1/public/polls", tags=["public"])
app.include_router(
    email_router, prefix="/api/v1/meetings/process-email-response", tags=["email"]
)
app.include_router(bookings_router, prefix="/api/v1/bookings", tags=["bookings"])


@app.get("/")
def root() -> dict:
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Briefly Meetings Service"}


@app.get("/health")
def health() -> dict:
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}
