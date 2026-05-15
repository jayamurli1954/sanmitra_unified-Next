"""Logging configuration for the application."""

import logging
from typing import Optional


def configure_logging(level: Optional[str] = None):
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if level is None:
        level = "INFO"

    level = level.upper()
    numeric_level = getattr(logging, level, logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger()
    logger.setLevel(numeric_level)
