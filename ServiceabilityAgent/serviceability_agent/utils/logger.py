"""
Structured logging for the Serviceability Agent.

Provides consistent logging across all components.
"""

import logging
import sys
import os
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        # Set level from environment variable
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        
        # Format: timestamp - logger_name - level - message
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
    
    return logger


def log_tool_call(logger: logging.Logger, tool_name: str, args: dict):
    """
    Log a tool invocation in a structured format.
    
    Args:
        logger: Logger instance
        tool_name: Name of the tool being called
        args: Tool arguments
    """
    logger.info(f"Tool call: {tool_name} | Args: {args}")


def log_tool_result(logger: logging.Logger, tool_name: str, success: bool, result: dict = None):
    """
    Log a tool result in a structured format.
    
    Args:
        logger: Logger instance
        tool_name: Name of the tool
        success: Whether the tool call succeeded
        result: Tool result (optional, for debugging)
    """
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"Tool result: {tool_name} | Status: {status}")
    
    if not success and result:
        logger.error(f"Tool error details: {result}")
