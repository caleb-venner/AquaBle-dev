"""Validation rules for domain models."""

from collections.abc import Sequence


def ensure_unique_values(values: Sequence[str], field_name: str) -> None:
    """Validate that all values in a sequence are unique.

    Args:
        values: Sequence of strings to check for uniqueness
        field_name: Name of field being validated (for error message)

    Raises:
        ValueError: If duplicate values are found
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
