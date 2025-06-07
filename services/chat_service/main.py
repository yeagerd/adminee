from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .api import router

app = FastAPI(title="Chat Service", version="0.1.0")
app.include_router(router)


@app.get("/")
def health_check():
    return JSONResponse(content={"status": "ok", "service": "chat-service"})
