from fastapi import FastAPI
from services.office_service.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="A backend microservice responsible for all external API interactions with Google and Microsoft services",
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

@app.get("/")
async def read_root():
    """Hello World root endpoint"""
    return {"message": "Hello World", "service": "Office Service"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "office-service"} 