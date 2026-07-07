"""Middleware package."""

from app.middleware.localhost_docs import LocalhostOnlyDocsMiddleware

__all__ = ["LocalhostOnlyDocsMiddleware"]
