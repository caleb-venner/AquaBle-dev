"""Device command helpers split out from ble_service for readability.

These are thin adapters that accept a running BLEService-like object
and perform device-level commands, delegating to the service's
connection and status helpers.
"""

from __future__ import annotations

from datetime import time as _time
from typing import TYPE_CHECKING, Any, Sequence

from bleak_retry_connector import BleakConnectionError, BleakNotFoundError
from fastapi import HTTPException

if TYPE_CHECKING:
    # Avoid runtime import cycles; used for type annotations only
    from ..ble_service import CachedStatus


async def set_doser_schedule(
    service: Any,
    address: str,
    *,
    head_index: int,
    volume_tenths_ml: int,
    hour: int,
    minute: int,
    weekdays: Sequence[str] | None = None,
    confirm: bool = False,
    wait_seconds: float = 1.5,
) -> "CachedStatus":
    """Set a daily dose schedule on a connected doser device."""
    device = await service._ensure_device(address, "doser")
    try:
        await device.set_daily_dose(
            head_index,
            volume_tenths_ml,
            hour,
            minute,
            weekdays=weekdays,
            confirm=confirm,
            wait_seconds=wait_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (BleakNotFoundError, BleakConnectionError) as exc:
        raise HTTPException(status_code=404, detail="Dosing pump not reachable") from exc
    return await service._refresh_device_status("doser", persist=True)


async def set_light_brightness(
    service: Any, address: str, *, brightness: int, color: int
) -> "CachedStatus":
    """Set the light brightness on a device for a specific channel.

    Args:
        service: BLE service instance
        address: Device MAC address
        brightness: Brightness value (0-100)
        color: Channel index (0-based integer, e.g., 0 for first channel, 1 for second, etc.)
    """
    device = await service._ensure_device(address, "light")
    try:
        # Validate channel index
        num_channels = len(set(device._colors.values()))
        if not (0 <= color < num_channels):
            raise ValueError(
                f"Invalid channel index {color}. "
                f"Device has {num_channels} channels (0-{num_channels-1})"
            )

        # Create brightness tuple with brightness for target channel, 0 for others
        brightness_tuple = tuple(brightness if i == color else 0 for i in range(num_channels))
        await device.set_brightness(brightness_tuple)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (BleakNotFoundError, BleakConnectionError) as exc:
        raise HTTPException(status_code=404, detail="Light not reachable") from exc
    return await service._refresh_device_status("light", persist=True)


async def turn_light_on(service: Any, address: str) -> "CachedStatus":
    """Turn the specified light device on."""
    device = await service._ensure_device(address, "light")
    try:
        await device.turn_on()
    except (BleakNotFoundError, BleakConnectionError) as exc:
        raise HTTPException(status_code=404, detail="Light not reachable") from exc
    return await service._refresh_device_status("light", persist=True)


async def turn_light_off(service: Any, address: str) -> "CachedStatus":
    """Turn the specified light device off."""
    device = await service._ensure_device(address, "light")
    try:
        await device.turn_off()
    except (BleakNotFoundError, BleakConnectionError) as exc:
        raise HTTPException(status_code=404, detail="Light not reachable") from exc
    return await service._refresh_device_status("light", persist=True)


async def enable_auto_mode(service: Any, address: str) -> "CachedStatus":
    """Enable auto mode on the light device."""
    device = await service._ensure_device(address, "light")
    try:
        await device.enable_auto_mode()
    except (BleakNotFoundError, BleakConnectionError) as exc:
        raise HTTPException(status_code=404, detail="Light not reachable") from exc
    return await service._refresh_device_status("light", persist=True)


async def set_manual_mode(service: Any, address: str) -> "CachedStatus":
    """Switch the light device to manual control mode."""
    device = await service._ensure_device(address, "light")
    try:
        await device.set_manual_mode()
    except (BleakNotFoundError, BleakConnectionError) as exc:
        raise HTTPException(status_code=404, detail="Light not reachable") from exc
    return await service._refresh_device_status("light", persist=True)


async def reset_auto_settings(service: Any, address: str) -> "CachedStatus":
    """Reset stored auto settings on the light device."""
    device = await service._ensure_device(address, "light")
    try:
        await device.reset_settings()
    except (BleakNotFoundError, BleakConnectionError) as exc:
        raise HTTPException(status_code=404, detail="Light not reachable") from exc
    return await service._refresh_device_status("light", persist=True)


async def add_light_auto_setting(
    service: Any,
    address: str,
    *,
    sunrise: _time,
    sunset: _time,
    brightness: int | tuple[int, ...] | dict[str, int] | None = None,
    ramp_up_minutes: int = 0,
    weekdays: Sequence[str] | None = None,
) -> "CachedStatus":
    """Add an auto program setting to the specified light device.

    Supports flexible brightness specification:
    - int: Apply same brightness to all channels
    - tuple/list: Apply brightness values in device channel order (by index)
    - dict: Map channel indices (as integers 0-N) to brightness values (e.g., {0: 80, 1: 100})
    - None: Default to 100 for all channels

    Args:
        sunrise: Sunrise time (datetime.time)
        sunset: Sunset time (datetime.time)
        brightness: Brightness configuration. See above for formats.
        ramp_up_minutes: Ramp up time in minutes
        weekdays: List of weekdays, defaults to everyday
    """
    device = await service._ensure_device(address, "light")
    try:
        # Validate and normalize brightness
        if brightness is None:
            normalized_brightness = None
        elif isinstance(brightness, int):
            normalized_brightness = brightness
        elif isinstance(brightness, (list, tuple)):
            normalized_brightness = tuple(int(x) for x in brightness)
        elif isinstance(brightness, dict):
            # Convert string keys to integers and validate channel indices
            # JSON sends dict keys as strings, so we need to handle both
            num_channels = len(set(device._colors.values()))
            converted_brightness = {}
            for key, value in brightness.items():
                try:
                    channel_idx = int(key) if isinstance(key, str) else key
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid channel index '{key}'. Must be a valid integer.")

                if not (0 <= channel_idx < num_channels):
                    raise ValueError(
                        f"Invalid channel index {channel_idx}. "
                        f"Device has {num_channels} channels (0-{num_channels-1})"
                    )
                converted_brightness[channel_idx] = int(value)
            normalized_brightness = converted_brightness
        else:
            raise ValueError(
                "brightness must be int, tuple/list of ints, dict of channel indices, or None"
            )

        # Use the unified add_auto_setting method
        await device.add_auto_setting(
            sunrise,
            sunset,
            brightness=normalized_brightness,
            ramp_up_in_minutes=ramp_up_minutes,
            weekdays=weekdays or ["everyday"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (BleakNotFoundError, BleakConnectionError) as exc:
        raise HTTPException(status_code=404, detail="Light not reachable") from exc

    return await service._refresh_device_status("light", persist=True)
