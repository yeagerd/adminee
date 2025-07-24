from fastapi import FastAPI

from .api import (
    email_router,
    invitations_router,
    polls_router,
    public_router,
    slots_router,
)

app = FastAPI()

app.include_router(polls_router, prefix="/api/meetings/polls", tags=["polls"])
app.include_router(
    slots_router, prefix="/api/meetings/polls/{poll_id}/slots", tags=["slots"]
)
app.include_router(
    invitations_router,
    prefix="/api/meetings/polls/{poll_id}/send-invitations",
    tags=["invitations"],
)
app.include_router(public_router, prefix="/api/public/polls", tags=["public"])
app.include_router(
    email_router, prefix="/api/meetings/process-email-response", tags=["email"]
)


@app.get("/")
def root():
    return {"message": "Welcome to the Briefly Meetings Service"}


@app.get("/health")
def health():
    return {"status": "ok"}
