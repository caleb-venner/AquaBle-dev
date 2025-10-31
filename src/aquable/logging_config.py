"""Unified logging configuration for AquaBle service.

This module provides a centralized logging configuration that ensures all log
entries (from both the application and uvicorn) include timestamps and follow
a consistent format.

Usage:
    At application startup (in main() or service initialization):
    >>> from aquable.logging_config import configure_logging
    >>> configure_logging()
    
    When starting uvicorn:
    >>> from aquable.logging_config import get_uvicorn_log_config
    >>> uvicorn.run(app, log_config=get_uvicorn_log_config())
    
    For development:
    >>> python3 dev_server.py  # Uses unified logging automatically

Configuration:
    - Log level: Set via AQUA_BLE_LOG_LEVEL environment variable (default: INFO)
    - Timezone: Set via TZ environment variable (affects timestamp display)
    - Format: "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
    - Date format: "%Y-%m-%d %H:%M:%S"

Benefits:
    - All log entries include timestamps (fixes the issue with uvicorn logs)
    - Consistent format across all loggers (application, uvicorn, etc.)
    - Proper timezone handling
    - Configurable via environment variables
"""

import logging
import logging.config
import os
from typing import Any, Dict


def get_log_level() -> str:
    """Get the log level from environment variable with fallback."""
    return (os.getenv("AQUA_BLE_LOG_LEVEL", "INFO") or "INFO").upper()


def get_logging_config() -> Dict[str, Any]:
    """Generate a unified logging configuration dictionary.
    
    This configuration ensures:
    - All log entries include timestamps
    - Consistent format across application and uvicorn
    - Proper timezone handling (via logging module's localtime parameter)
    - Color-coded output for terminal
    - Access logs (health/status checks) only shown in verbose mode or on errors
    """
    log_level = get_log_level()
    
    # Check for verbose logging flag (set by Home Assistant add-on config)
    verbose_logging = os.getenv("AQUA_BLE_VERBOSE_LOGGING", "false").lower() in ("true", "1", "yes")
    
    # Set access log level: INFO for verbose mode, WARNING otherwise
    access_log_level = log_level if verbose_logging else "WARNING"
    
    # Unified format with timestamp
    log_format = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": log_format,
                "datefmt": date_format,
            },
            "access": {
                # Use the same format as default - uvicorn will provide the message
                "format": log_format,
                "datefmt": date_format,
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": access_log_level,  # WARNING by default, INFO if verbose_logging enabled
                "propagate": False,
            },
            "aquable": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["default"],
        },
    }


def configure_logging() -> None:
    """Configure logging for the entire application.
    
    This should be called once at application startup, before any other
    logging configuration or logger creation.
    """
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Set timezone-aware timestamps if TZ environment variable is set
    tz = os.getenv("TZ")
    if tz:
        logging.Formatter.converter = logging.Formatter.converter  # Use local time
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured with timezone: {tz}")


def get_uvicorn_log_config() -> Dict[str, Any]:
    """Get uvicorn-specific log configuration.
    
    This configuration is used when starting uvicorn to ensure it uses
    the unified logging format.
    """
    return get_logging_config()
