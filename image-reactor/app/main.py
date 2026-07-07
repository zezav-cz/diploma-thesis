"""Main FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, disable_created_metrics, generate_latest

from app.internal.config import get_settings
from app.internal.logging_config import configure_logging
from app.middleware import LocalhostOnlyDocsMiddleware
from app.routers.http import health
from app.routers.http.v1 import v1_router
from app.services.database import db

# Metrics configuration
settings = get_settings()
configure_logging(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    logger.info("Starting application")

    # Initialize database
    db.settings = settings
    await db.connect()

    logger.info("Application started successfully")

    yield

    logger.info("Shutting down application")
    await db.disconnect()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(lifespan=lifespan, debug=True)

    # Localhost-only documentation middleware
    app.add_middleware(LocalhostOnlyDocsMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include health endpoints
    app.include_router(health.router)

    # Mount v1 API
    app.mount("/api/v1", v1_router)

    metrics_api_info = {}
    if settings.expose_metrics:
        disable_created_metrics()
        metrics_api_info = {"metrics": "/metrics"}

        @app.get("/metrics", tags=["Metrics"])
        async def metrics() -> Response:
            """Prometheus metrics endpoint."""
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "message": "Image Processor API",
            "api_v1": "/api/v1",
            **health.get_api_info(),
            **metrics_api_info,
        }

    # Add metrics endpoint if enabled

    return app


app = create_app()
