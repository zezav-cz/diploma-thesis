"""Logging configuration using Loguru for application logs and standard logging for uvicorn."""

import logging
import sys

from loguru import logger

from app.internal.config import Settings


def format_record(record: dict[str, any]) -> str:
    """
    Custom format function to style 'extra' fields nicely.
    Output: TIMESTAMP | LEVEL | LOC - MESSAGE | key=value key2=value2
    """
    # Base format for time, level, location, and message
    format_columns = [
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green>",
        "<level>{level: <8}</level>",
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>",
        "<level>{message}</level>",
    ]

    # If there are extra fields (bound via logger.bind()), add them
    if record["extra"]:
        extra_str = ", ".join(
            [f"{key}={value}" for key, value in record["extra"].items()]
        )
        extra_str = extra_str.replace("\n", "\\n")
        format_columns.append(f"<yellow>{extra_str}</yellow>")

    # Add newline and exception handling
    format_string = " | ".join(format_columns)

    return format_string + "\n{exception}"


def configure_logging(settings: Settings) -> None:
    """
    Configure Loguru for application logs and standard logging for uvicorn.

    Sets up logging based on log level and format (JSON or TXT).
    """
    log_level = settings.log_level.upper()
    log_format = settings.log_format.upper()

    # Remove default loguru handler
    logger.remove()

    # Configure format based on settings
    if log_format == "JSON":
        # JSON format for structured logging
        logger.add(
            sys.stdout,
            format="{message}",
            level=log_level,
            serialize=True,  # This enables JSON serialization
            enqueue=True,  # Non-blocking logging via background thread
        )
    else:
        # TXT format (default) - colorized and human-readable with extra fields
        logger.add(
            sys.stdout,
            format=format_record,
            level=log_level,
            colorize=True,
            enqueue=True,  # Non-blocking logging via background thread
        )

    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)

    loggers = ()

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = []
        logging_logger.propagate = True

    # Set asyncpg to DEBUG level when app log level is TRACE to show queries
    if log_level == "TRACE":
        asyncpg_logger = logging.getLogger("asyncpg")
        asyncpg_logger.setLevel(logging.DEBUG)

    logger.bind(level=log_level, format=log_format).info("Logging configured")

    logger.info("Standard logging cleared")


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Use the record's module information directly instead of trying to find the caller
        # This preserves the original logger name (e.g., uvicorn, uvicorn.access)
        logger.patch(
            lambda r: r.update(
                name=record.name, function=record.funcName, line=record.lineno
            )
        ).log(level, record.getMessage())
