from fastapi import APIRouter

from services.meetings.api.booking_endpoints import (  # noqa: F401
    router as bookings_router,
)
from services.meetings.api.email import router as email_router  # noqa: F401
from services.meetings.api.invitations import router as invitations_router  # noqa: F401
from services.meetings.api.polls import router as polls_router  # noqa: F401
from services.meetings.api.public import router as public_router  # noqa: F401
from services.meetings.api.slots import router as slots_router  # noqa: F401

router = APIRouter()

# Register routers (to be included in main.py)
