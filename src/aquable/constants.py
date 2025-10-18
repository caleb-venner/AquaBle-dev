"""Timeout constants used across the application.

Centralized timeout definitions to ensure consistency across frontend,
backend, and device layers.
"""

from __future__ import annotations

# Command execution timeouts (seconds)
COMMAND_TIMEOUT_DEFAULT = 10.0  # Default timeout for most commands
COMMAND_TIMEOUT_AUTO_SETTINGS = 15.0  # Timeout for auto setting operations (add/delete/reset)

# BLE operation timeouts (seconds)
BLE_STATUS_CAPTURE_WAIT = 1.5  # Wait time after sending commands before reading status
BLE_DOSER_SCHEDULE_WAIT = 2.0  # Wait time for doser schedule confirmation

# Frontend API timeouts (seconds) - should match backend defaults
FRONTEND_COMMAND_TIMEOUT_DEFAULT = 10
FRONTEND_COMMAND_TIMEOUT_AUTO_SETTINGS = 15
