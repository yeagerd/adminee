from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Chat Service", version="0.1.0")

@app.get("/")
def health_check():
    return JSONResponse(content={"status": "ok", "service": "chat-service"})
