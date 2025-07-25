from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.common.http_errors import register_briefly_exception_handlers
from services.meetings.api import (
    email_router,
    invitations_router,
    polls_router,
    public_router,
    slots_router,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/")
def root() -> dict:
    return {"message": "Welcome to the Briefly Meetings Service"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
