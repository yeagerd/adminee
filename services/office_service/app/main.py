from fastapi import FastAPI
from services.office_service.core.config import settings
from services.office_service.api.health import router as health_router

app = FastAPI(
    title=settings.APP_NAME,
    description="A backend microservice responsible for all external API interactions with Google and Microsoft services",
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# Include routers
app.include_router(health_router)

@app.get("/")
async def read_root():
    """Hello World root endpoint"""
    return {"message": "Hello World", "service": "Office Service"} 