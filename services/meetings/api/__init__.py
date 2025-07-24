from fastapi import APIRouter

from .email import router as email_router
from .invitations import router as invitations_router
from .polls import router as polls_router
from .public import router as public_router
from .slots import router as slots_router

router = APIRouter()

# Register routers (to be included in main.py)
