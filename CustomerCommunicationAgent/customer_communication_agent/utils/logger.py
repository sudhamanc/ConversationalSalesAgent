"""
Logging utilities for the Customer Communication Agent.
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Configure and return a logger instance.
    
    Args:
        name: Logger name (typically __name__ of calling module)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only add handler if not already present
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


# Create default logger instance for module-level use
logger = get_logger("customer_communication_agent.utils.logger")
