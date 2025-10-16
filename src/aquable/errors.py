"""Error types and constants for consistent error handling across the application."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Standardized error codes for consistent error handling."""

    # Device-related errors
    DEVICE_NOT_FOUND = "device_not_found"
    DEVICE_DISCONNECTED = "device_disconnected"
    DEVICE_BUSY = "device_busy"
    DEVICE_TIMEOUT = "device_timeout"

    # Command-related errors
    COMMAND_INVALID = "command_invalid"
    COMMAND_TIMEOUT = "command_timeout"
    COMMAND_FAILED = "command_failed"
    COMMAND_CANCELLED = "command_cancelled"

    # Validation errors
    VALIDATION_ERROR = "validation_error"
    INVALID_ARGUMENTS = "invalid_arguments"

    # BLE-specific errors
    BLE_CONNECTION_ERROR = "ble_connection_error"
    BLE_CHARACTERISTIC_MISSING = "ble_characteristic_missing"

    # Configuration errors
    CONFIG_SAVE_ERROR = "config_save_error"

    # Generic errors
    INTERNAL_ERROR = "internal_error"
    UNKNOWN_ERROR = "unknown_error"


class AquariumError(Exception):
    """Base exception class for AquaBle errors."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize the aquarium error.

        Args:
            code: Error code identifier
            message: Human-readable error message
            details: Additional error context and data
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


# Specific error classes
class DeviceNotFoundError(AquariumError):
    """Raised when a device is not found."""

    def __init__(self, address: str, details: Optional[Dict[str, Any]] = None):
        """Initialize device not found error.

        Args:
            address: Device MAC address that was not found
            details: Additional error context
        """
        super().__init__(
            ErrorCode.DEVICE_NOT_FOUND,
            f"Device {address} not found",
            details={"address": address, **(details or {})},
        )


class DeviceDisconnectedError(AquariumError):
    """Raised when a device is disconnected."""

    def __init__(self, address: str, details: Optional[Dict[str, Any]] = None):
        """Initialize device disconnected error.

        Args:
            address: Device MAC address that is disconnected
            details: Additional error context
        """
        super().__init__(
            ErrorCode.DEVICE_DISCONNECTED,
            f"Device {address} is disconnected",
            details={"address": address, **(details or {})},
        )


class CommandValidationError(AquariumError):
    """Raised when command arguments are invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize command validation error.

        Args:
            message: Validation error message
            details: Additional validation context
        """
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            message,
            details,
        )


class CommandTimeoutError(AquariumError):
    """Raised when a command times out."""

    def __init__(
        self,
        action: str,
        timeout: float,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize command timeout error.

        Args:
            action: Command action that timed out
            timeout: Timeout duration in seconds
            details: Additional error context
        """
        super().__init__(
            ErrorCode.COMMAND_TIMEOUT,
            f"Command '{action}' timed out after {timeout} seconds",
            details={"action": action, "timeout": timeout, **(details or {})},
        )


class BLEConnectionError(AquariumError):
    """Raised when BLE connection fails."""

    def __init__(
        self,
        address: str,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize BLE connection error.

        Args:
            address: Device MAC address that failed to connect
            cause: Original exception that caused the connection failure
            details: Additional error context
        """
        message = f"BLE connection failed for device {address}"
        if cause:
            message += f": {cause}"
        super().__init__(
            ErrorCode.BLE_CONNECTION_ERROR,
            message,
            details={"address": address, **(details or {})},
            cause=cause,
        )


class CharacteristicMissingError(AquariumError):
    """Raised when a required BLE characteristic is missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize characteristic missing error.

        Args:
            message: Error message describing the missing characteristic
            details: Additional error context
        """
        super().__init__(
            ErrorCode.BLE_CHARACTERISTIC_MISSING,
            message,
            details,
        )
