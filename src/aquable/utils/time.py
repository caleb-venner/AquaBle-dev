"""Time and timezone utilities for timestamps and system timezone detection.

This module handles:
1. Consistent ISO 8601 timestamp generation in the user's local timezone
2. System timezone detection and IANA validation
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def now_iso() -> str:
    """Get current timestamp in user's local timezone.

    Timestamps are stored in configuration files and should be in the user's
    local timezone for readability and debugging.

    Returns:
        ISO 8601 timestamp string with timezone offset
        (e.g., "2025-10-12T14:30:00-07:00")
    """
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def get_system_timezone() -> str:
    """Get the system timezone as an IANA timezone identifier.

    Detects the system timezone using multiple methods:
    1. TZ environment variable
    2. /etc/timezone file (Debian/Ubuntu)
    3. /etc/localtime symlink (RHEL/CentOS/most Linux)
    4. Falls back to "UTC"

    Returns:
        IANA timezone identifier (e.g., "America/New_York", "UTC")
    """
    # Method 1: Check TZ environment variable
    tz_env = os.environ.get("TZ")
    if tz_env and _is_valid_timezone(tz_env):
        return tz_env

    # Method 2: Read /etc/timezone
    try:
        tz_file = Path("/etc/timezone")
        if tz_file.exists():
            tz_str = tz_file.read_text().strip()
            if _is_valid_timezone(tz_str):
                return tz_str
    except (OSError, IOError):
        pass

    # Method 3: Check /etc/localtime symlink
    try:
        localtime_path = Path("/etc/localtime")
        if localtime_path.is_symlink():
            target = str(localtime_path.readlink())
            if "zoneinfo/" in target:
                tz_str = target.split("zoneinfo/", 1)[-1]
                if _is_valid_timezone(tz_str):
                    return tz_str
    except (OSError, IOError):
        pass

    return "UTC"


def _is_valid_timezone(tz_str: str) -> bool:
    """Validate if a string is a valid IANA timezone identifier.

    Uses zoneinfo to validate - no fallback to format-only checks.

    Args:
        tz_str: String to validate

    Returns:
        True if valid IANA timezone, False otherwise
    """
    if not tz_str or not isinstance(tz_str, str):
        return False

    try:
        ZoneInfo(tz_str)
        return True
    except Exception:
        return False
