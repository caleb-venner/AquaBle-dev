"""Time and timestamp utilities for consistent timestamp generation.

This module provides centralized timestamp generation for configuration metadata.
All timestamps use local system time (not UTC) since this service manages physical
devices in the user's local environment.
"""

from datetime import datetime


def now_iso() -> str:
    """Get current timestamp in user's local timezone.

    Timestamps are stored in configuration files and should be in the user's
    local timezone for readability and debugging.

    Returns:
        ISO 8601 timestamp string with timezone offset
        (e.g., "2025-10-12T14:30:00-07:00")
    """
    return datetime.now().astimezone().replace(microsecond=0).isoformat()
