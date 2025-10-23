"""Common utilities for device storage operations.

This module provides shared functionality for device storage classes
to avoid code duplication.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence


def filter_device_json_files(storage_dir: Path) -> List[Path]:
    """Get all JSON files in storage directory.

    Args:
        storage_dir: Directory containing device JSON files

    Returns:
        List of Path objects for device configuration files
    """
    if not storage_dir.exists():
        return []

    return list(storage_dir.glob("*.json"))


def ensure_unique_values(values: Sequence[str], field_name: str) -> None:
    """Validate that all values in a sequence are unique.

    This validation is used by both doser and light storage models to ensure
    that lists like weekday names, channel keys, and time points don't contain
    duplicates.

    Args:
        values: Sequence of strings to check for uniqueness
        field_name: Name of field being validated (for error message)

    Raises:
        ValueError: If duplicate values are found, with details
        of which values are duplicated

    Example:
        >>> ensure_unique_values(["Mon", "Tue", "Mon"], "weekdays")
        ValueError: Duplicate weekdays: ['Mon']
    """
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    if duplicates:
        plural = "s" if len(duplicates) > 1 else ""
        raise ValueError(f"Duplicate {field_name}{plural}: {sorted(duplicates)}")
