"""
Structured logging utility for the Product Agent.

Provides consistent logging across all agent components.
"""

import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        level: Optional log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Defaults to INFO if not specified
    
    Returns:
        Configured logger instance
    """
    import os
    
    # Get log level from environment or use provided level or default to INFO
    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger
