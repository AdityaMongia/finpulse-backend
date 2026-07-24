"""
app/core/logging.py
===================
Centralised logging configuration for FinPulse.

Sets up Python's standard `logging` module with:
  - A consistent log format (JSON in production, human-readable in development)
  - Configurable log level from settings
  - A JSON formatter via `python-json-logger` for structured log aggregation

Usage:
    # Called once at application startup (inside lifespan in main.py):
    from app.core.logging import configure_logging
    configure_logging(level="INFO", fmt="json")

    # Anywhere else in the codebase:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Something happened", extra={"ticker": "RELIANCE.NS"})
"""

import logging
import sys
from typing import Literal

from pythonjsonlogger import jsonlogger


# Map string level names to logging constants
_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Noisy third-party loggers to suppress unless DEBUG is active
_QUIET_LOGGERS: list[str] = [
    "uvicorn.access",
    "sqlalchemy.engine",
    "apscheduler",
    "httpx",
]


class _JsonFormatter(jsonlogger.JsonFormatter):
    """
    Extended JSON formatter that adds standard fields to every log record.

    Each log line will include:
        - timestamp  (ISO 8601)
        - level      (INFO, ERROR, …)
        - name       (logger name / module path)
        - message    (the log message)
        - any extra  kwargs passed via logger.info("…", extra={})
    """

    def add_fields(
        self,
        log_record: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["name"] = record.name


class _TextFormatter(logging.Formatter):
    """
    Human-readable formatter for development consoles.
    Example: 2024-01-15 10:23:45,123 | INFO     | app.main | Application started
    """

    _FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    _DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATE_FMT)


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    fmt: Literal["json", "text"] = "json",
) -> None:
    """
    Configure the root logger and all application loggers.

    Parameters
    ----------
    level:
        Minimum severity level to emit (e.g. "INFO").
    fmt:
        "json"  → structured JSON logs (for production / log aggregation)
        "text"  → coloured human-readable logs (for development console)

    This function is idempotent — safe to call multiple times.
    """
    numeric_level = _LEVEL_MAP.get(level.upper(), logging.INFO)

    # Choose formatter
    formatter: logging.Formatter
    if fmt == "json":
        formatter = _JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        formatter = _TextFormatter()

    # Root handler (stdout)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()   # Remove any handlers added before configure_logging
    root_logger.addHandler(handler)

    # Quieten noisy third-party libraries unless DEBUG is active
    if numeric_level > logging.DEBUG:
        for name in _QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger(__name__).debug(
        "Logging configured: level=%s format=%s", level, fmt
    )
