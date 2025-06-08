from fastapi import FastAPI
from contextlib import asynccontextmanager

from core.config import Settings
from core.cache_manager import init_redis_pool, close_redis_pool
from core.dependencies import get_token_manager, get_api_client_factory, close_global_token_manager
from api import health as health_router
from api import email as email_router
from api import calendar as calendar_router
from api import files as files_router

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis_pool()
    tm = await get_token_manager()
    await get_api_client_factory(tm) # Initialize factory with the token manager
    yield
    await close_global_token_manager() # Close token manager's client
    await close_redis_pool()

app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    lifespan=lifespan
)

app.include_router(health_router.router)
app.include_router(email_router.router)
app.include_router(calendar_router.router)
app.include_router(files_router.router)

@app.get("/")
async def read_root():
    return {"Hello": "World"}
