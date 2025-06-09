"""
User Management Service - FastAPI Application

This is the main entry point for the User Management Service.
"""

from fastapi import FastAPI

app = FastAPI(
    title="User Management Service",
    description="Manages user profiles, preferences, and OAuth integrations",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "user-management"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
