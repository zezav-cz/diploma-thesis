"""Utility for handling exceptions in API endpoints."""

from fastapi import HTTPException, status

from app.internal.config import get_settings


def handle_exception(
    exception: Exception,
    log_message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    generic_detail: str = "An error occurred while processing the request",
) -> HTTPException:
    """Handle exceptions with configurable verbosity.

    Returns an HTTPException with either:
    - Detailed error message (if VERBOSE_API_EXCEPTIONS=True)
    - Generic error message (if VERBOSE_API_EXCEPTIONS=False)

    Args:
        exception: The exception that occurred
        log_message: Message to include in detailed error
        status_code: HTTP status code to return (default: 500)
        generic_detail: Generic error message to return when verbose mode is off

    Returns:
        HTTPException with appropriate detail message
    """
    settings = get_settings()

    # Return detailed or generic message based on configuration
    detail = f"{log_message}: {str(exception)}" if settings.verbose_api_exceptions else generic_detail

    return HTTPException(
        status_code=status_code,
        detail=detail,
    )
