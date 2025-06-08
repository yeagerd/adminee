from fastapi import FastAPI

from services.office_service.api.calendar import router as calendar_router
from services.office_service.api.email import router as email_router
from services.office_service.api.files import router as files_router
from services.office_service.api.health import router as health_router
from services.office_service.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="A backend microservice responsible for all external API interactions with Google and Microsoft services",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

# Include routers
app.include_router(health_router)
app.include_router(email_router)
app.include_router(calendar_router)
app.include_router(files_router)


@app.get("/")
async def read_root():
    """Hello World root endpoint"""
    return {"message": "Hello World", "service": "Office Service"}
