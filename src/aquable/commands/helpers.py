"""Utilities for device command operations.

Provides helpers for common patterns in device command execution.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Literal

from bleak_retry_connector import BleakConnectionError, BleakNotFoundError
from fastapi import HTTPException

__all__ = ["device_operation"]


@asynccontextmanager
async def device_operation(
    service: Any,
    address: str,
    device_type: Literal["doser", "light"],
    status_wait: float = 1.5,
) -> AsyncGenerator[Any, None]:
    """Context manager for device command operations.

    Handles the common pattern of:
    1. Ensure device is connected via _ensure_device()
    2. Execute operation (within the context)
    3. Refresh device status after operation
    4. Catch BLE errors and convert to HTTPException

    Usage:
        async def turn_light_on(service, address):
            async with device_operation(service, address, "light") as device:
                await device.turn_on()
    # Status automatically refreshed after context exits
    return await service._refresh_device_status(address, persist=True)

    Args:
        service: BLE service instance
        address: Device MAC address
        device_type: Type of device ("doser" or "light")
        status_wait: Time to wait before reading status (default 1.5s)

    Yields:
        Connected device instance ready for commands

    Raises:
        HTTPException: BLE connection errors converted to 404
    """
    try:
        device = await service._ensure_device(address, device_type)
        yield device
    except (BleakNotFoundError, BleakConnectionError) as exc:
        device_type_display = device_type.capitalize()
        raise HTTPException(status_code=404, detail=f"{device_type_display} not reachable") from exc
