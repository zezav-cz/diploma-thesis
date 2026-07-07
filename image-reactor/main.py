"""Entry point for running the FastAPI application."""

import uvicorn

from app.internal.config import get_settings


def main() -> None:
    """Run the FastAPI application with uvicorn."""
    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=str(settings.host),
        port=settings.port,
    )


if __name__ == "__main__":
    main()
