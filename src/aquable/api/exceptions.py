"""Exception handling utilities for API routes.

Provides decorators and utilities for consistent error handling across endpoints.
"""

import functools
import logging
from typing import Any, Callable, TypeVar, cast

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# TypeVar for wrapping async functions
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# HTTP Error Factory Functions
# ============================================================================


def device_not_found(address: str) -> HTTPException:
    """Create a standardized 404 error for device not found.

    Args:
        address: Device MAC address that was not found

    Returns:
        HTTPException with 404 status and formatted message
    """
    return HTTPException(status_code=404, detail=f"Device not found: {address}")


def command_not_found(command_id: str) -> HTTPException:
    """Create a standardized 404 error for command not found.

    Args:
        command_id: Command ID that was not found

    Returns:
        HTTPException with 404 status and formatted message
    """
    return HTTPException(status_code=404, detail=f"Command not found: {command_id}")


def device_not_reachable(device_type: str) -> HTTPException:
    """Create a standardized 404 error for unreachable device.

    Args:
        device_type: Type of device (e.g., 'light', 'doser')

    Returns:
        HTTPException with 404 status and formatted message
    """
    device_label = device_type.capitalize() if device_type else "Device"
    return HTTPException(status_code=404, detail=f"{device_label} not reachable")


def invalid_device_data(message: str) -> HTTPException:
    """Create a standardized 422 error for invalid device data.

    Args:
        message: Detailed validation error message

    Returns:
        HTTPException with 422 status and formatted message
    """
    return HTTPException(status_code=422, detail=f"Invalid request: {message}")


def storage_error(message: str) -> HTTPException:
    """Create a standardized 500 error for storage/file system errors.

    Args:
        message: Error message describing the storage issue

    Returns:
        HTTPException with 500 status and formatted message
    """
    return HTTPException(status_code=500, detail=f"Storage error: {message}")


def connection_timeout() -> HTTPException:
    """Create a standardized 504 error for connection timeout.

    Returns:
        HTTPException with 504 status for timeout
    """
    return HTTPException(status_code=504, detail="Connection timeout")


def unsupported_device_type() -> HTTPException:
    """Create a standardized 400 error for unsupported device type.

    Returns:
        HTTPException with 400 status
    """
    return HTTPException(status_code=400, detail="Unsupported device type")


def model_code_mismatch(imported: str, current: str) -> HTTPException:
    """Create a standardized 409 error for model code mismatch.

    Args:
        imported: Model code from imported configuration
        current: Model code of current device

    Returns:
        HTTPException with 409 status
    """
    return HTTPException(
        status_code=409,
        detail=f"Model code mismatch: imported config is for {imported} but device is {current}",
    )


def bluetooth_unavailable() -> HTTPException:
    """Create a standardized 503 error for unavailable Bluetooth.

    Returns:
        HTTPException with 503 status
    """
    return HTTPException(
        status_code=503,
        detail="Bluetooth not available: D-Bus socket not found. "
        "Ensure Bluetooth hardware and drivers are properly configured.",
    )


def bluetooth_permission_denied() -> HTTPException:
    """Create a standardized 403 error for Bluetooth permission denial.

    Returns:
        HTTPException with 403 status
    """
    return HTTPException(
        status_code=403,
        detail="Bluetooth permission denied. Check add-on permissions.",
    )


def bluetooth_disabled() -> HTTPException:
    """Create a standardized 503 error for disabled Bluetooth.

    Returns:
        HTTPException with 503 status
    """
    return HTTPException(
        status_code=503,
        detail="Bluetooth is disabled or not available on this device. "
        "Enable Bluetooth to scan for devices.",
    )


def bluetooth_adapter_not_found() -> HTTPException:
    """Create a standardized 503 error for missing Bluetooth adapter.

    Returns:
        HTTPException with 503 status
    """
    return HTTPException(
        status_code=503,
        detail="Bluetooth adapter not found. Ensure Bluetooth hardware is present and enabled.",
    )


def bluetooth_scan_failed(reason: str = "") -> HTTPException:
    """Create a standardized 503 error for Bluetooth scan failure.

    Args:
        reason: Optional reason for scan failure

    Returns:
        HTTPException with 503 status
    """
    detail = "Bluetooth scan failed"
    if reason:
        detail += f": {reason}"
    return HTTPException(status_code=503, detail=detail)


# ============================================================================
# Error Handling Decorators
# ============================================================================


def handle_storage_errors(func: F) -> F:
    """Decorator for consistent error handling across API endpoints.

    Handles common storage and validation exceptions:
    - HTTPException: Pass through (already formatted for response)
    - ValueError: User input validation errors (422 status)
    - OSError/IOError: File system errors (500 status)

    Usage:
        @router.get("/devices/{address}/configurations")
        @handle_storage_errors
        async def get_device_configurations(request: Request, address: str):
            # Implementation without try-except needed
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Already formatted error response, pass through
            raise
        except ValueError as e:
            # User input validation errors -> 422 Unprocessable Entity
            logger.error(f"Validation error in {func.__name__}: {e}", exc_info=True)
            raise invalid_device_data(str(e)) from e
        except (OSError, IOError) as e:
            # File system errors -> 500 Internal Server Error
            logger.error(f"Storage error in {func.__name__}: {e}", exc_info=True)
            raise storage_error(str(e)) from e

    return cast(F, wrapper)
