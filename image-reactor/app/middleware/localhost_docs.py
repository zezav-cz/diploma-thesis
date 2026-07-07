"""Middleware to restrict documentation endpoints to localhost only."""

from fastapi import Request, Response, status
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class LocalhostOnlyDocsMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict documentation endpoints to localhost only."""

    async def dispatch(self, request: Request, call_next):
        """Check if request to docs endpoints is from localhost."""
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            client_host = request.client.host if request.client else None
            if client_host not in ["127.0.0.1", "localhost", "::1"]:
                logger.bind(path=request.url.path, client=client_host).warning("Blocked non-localhost access to documentation")
                return Response(
                    content="Access to documentation is restricted to localhost only",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            logger.bind(path=request.url.path, client=client_host).debug("Allowing localhost access to documentation")
        return await call_next(request)
