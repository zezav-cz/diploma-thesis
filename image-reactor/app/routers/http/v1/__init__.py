"""HTTP v1 routers."""

from fastapi import FastAPI

from . import failed_downloads_attempts, images

# API Metadata Constants
API_TITLE = "Image Processor API v1"
API_SUMMARY = "Image metadata processor with FastAPI and asyncpg"
API_VERSION = "1.0.0"
API_DESCRIPTION = """Image metadata processor API.

## Features
- Store and retrieve image metadata
- Track failed download attempts
- Health check endpoints
"""
API_CONTACT_NAME = "Jan Trojak"
API_CONTACT_EMAIL = "jan.trojak@recombee.com"

v1_router = FastAPI(
    title=API_TITLE,
    summary=API_SUMMARY,
    version=API_VERSION,
    description=API_DESCRIPTION,
    contact={
        "name": API_CONTACT_NAME,
        "email": API_CONTACT_EMAIL,
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@v1_router.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint for API v1."""
    return {
        "message": "Image Processor API v1",
        "version": API_VERSION,
        "docs": "/api/v1/docs",
        "redoc": "/api/v1/redoc",
        "openapi": "/api/v1/openapi.json",
        "health": "/api/v1/health",
    }


# Include v1 routers
v1_router.include_router(images.router)
v1_router.include_router(failed_downloads_attempts.router)
