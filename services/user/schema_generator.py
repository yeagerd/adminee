"""
Schema generator for the user service that doesn't require full app initialization.
This allows OpenAPI schema generation without needing all environment variables.
"""

from fastapi import FastAPI
from services.user.routers import (
    integrations_router,
    internal_router,
    preferences_router,
    provider_router,
    users_router,
)

def create_schema_app() -> FastAPI:
    """
    Create a minimal FastAPI app for schema generation only.
    This bypasses the lifespan validation and database connections.
    """
    app = FastAPI(
        title="Briefly User Management Service",
        description="Manages user profiles, preferences, and OAuth integrations for the Briefly platform",
        version="0.1.0",
        contact={
            "name": "Briefly Team",
            "email": "support@briefly.ai",
        },
        license_info={
            "name": "Private",
        },
        openapi_tags=[
            {"name": "users", "description": "User profile management and operations"},
            {
                "name": "preferences",
                "description": "User preferences and settings management",
            },
            {
                "name": "integrations",
                "description": "OAuth integrations and provider management",
            },
            {
                "name": "providers",
                "description": "Authentication provider configuration",
            },
            {
                "name": "internal",
                "description": "Internal service-to-service endpoints",
            },
        ],
    )

    # Register API routers with v1 prefix
    app.include_router(users_router, prefix="/v1")
    app.include_router(preferences_router, prefix="/v1")
    app.include_router(integrations_router, prefix="/v1")
    app.include_router(provider_router, prefix="/v1")
    app.include_router(internal_router, prefix="/v1")

    return app

# Create the schema app instance
schema_app = create_schema_app()
