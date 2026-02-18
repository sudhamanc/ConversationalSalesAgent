"""
Logging configuration for the Payment Agent.
"""

import logging
import os
from typing import Optional

# Default log level from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ from calling module)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or __name__)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    return logger
