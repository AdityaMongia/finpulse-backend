"""
app/utils/logger.py
====================
Logger factory helper.

Provides a simple `get_logger(name)` convenience function so all modules
can get a consistently named logger with a single import instead of
repeating `logging.getLogger(__name__)` everywhere.

Usage:
    from app.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Processing ticker %s", ticker)

Note:
    The actual logging CONFIGURATION (level, format, handlers) is done
    once at startup in `app.core.logging.configure_logging()`.
    This module only provides a factory for getting named loggers —
    it does NOT configure the root logger.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Parameters
    ----------
    name : str
        Logger name. Best practice is to pass `__name__` so the logger
        hierarchy reflects the Python module path.
        e.g., "app.services.stock_service"

    Returns
    -------
    logging.Logger
        A standard Python Logger instance.

    Example:
        # In any module:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("This is logged as: app.your.module | This is logged")
    """
    return logging.getLogger(name)
