"""Base class for Chihiros lighting devices with status support."""

from __future__ import annotations

from typing import Any, ClassVar, Sequence

from ..commands import encoder as commands
from ..storage.models import LightStatus, parse_light_payload
from ..utils.schedule import get_schedules_with_status
from .base_device import BaseDevice


class LightDevice(BaseDevice):
    """Base class for Chihiros lights that can request status updates."""

    device_kind: ClassVar[str] = "light"
    status_serializer: ClassVar[str | None] = "serialize_light_status"

    async def request_status(self) -> None:
        """Trigger a status report from the light via the UART handshake."""
        cmd = commands.create_handshake_command(self.get_next_msg_id())
        await self._send_command(cmd, 3)

    def _parse_status(self, data: bytearray) -> Any:
        """Parse an incoming UART notification from the light."""
        if not data:
            return None

        if data[0] == 0x5B and len(data) >= 6:
            mode = data[5]
            if mode == 0xFE:
                try:
                    status = parse_light_payload(data)
                    # If in auto mode, augment programs with live status
                    if (
                        status
                        and hasattr(status, "profile")
                        and status.profile
                        and status.profile.mode == "auto"
                        and status.profile.programs
                    ):
                        # Pydantic models are immutable, so we need to create a new profile
                        programs_with_status = get_schedules_with_status(
                            [p.dict() for p in status.profile.programs]
                        )
                        # Re-create program objects to match Pydantic model
                        # This is a bit inefficient but necessary if we don't modify the model
                        # For now, we assume the frontend can handle the dicts
                        status.profile.programs = programs_with_status

                    return status
                except Exception:
                    self._logger.exception("Failed to parse light status payload")
                    # Return a minimal object so raw payload is available
                    return LightStatus(
                        message_id=None,
                        response_mode=None,
                        weekday=None,
                        hour=None,
                        minute=None,
                        keyframes=[],
                        time_markers=[],
                        tail=b"",
                        raw_payload=bytes(data),
                    )
            if mode == 0x0A:
                self._logger.debug("%s: Handshake ack: %s", self.name, data.hex())
                return None  # Not a status update

        self._logger.debug("%s: Non-status notification: %s", self.name, data.hex())
        return None

    async def set_brightness(self, brightness: int | tuple[int, ...]) -> None:
        """Set light brightness.

        Args:
            brightness: Single brightness value (0-100) for single channel,
                       or tuple of brightness values for multiple channels (RGB, RGBW, etc.)
        """
        # Normalize to tuple of (channel_id, brightness) pairs
        if isinstance(brightness, int):
            # Single brightness value: apply to all channels
            commands_to_send = [
                (channel_id, brightness) for channel_id in sorted(set(self._colors.values()))
            ]
        else:
            # Tuple of brightness values: map to channel IDs in sorted order
            channel_ids = sorted(set(self._colors.values()))
            commands_to_send = list(zip(channel_ids, brightness))

        # Send each brightness command
        for channel_id, brightness_value in commands_to_send:
            cmd = commands.create_manual_setting_command(
                self.get_next_msg_id(), channel_id, brightness_value
            )
            await self._send_command(cmd, 3)

    async def turn_on(self) -> None:
        """Turn on light."""
        await self.set_brightness(100)

    async def turn_off(self) -> None:
        """Turn off light."""
        await self.set_brightness(0)

    async def add_auto_setting(
        self,
        sunrise,
        sunset,
        brightness: int | tuple[int, ...] | dict[int, int] | None = None,
        ramp_up_in_minutes: int = 0,
        weekdays: Sequence[str] | None = None,
    ) -> None:
        """Add an automation setting to the light.

        Supports flexible brightness specification:
        - Single int: Apply same brightness to all channels
        - Tuple of ints: Apply brightness values in device channel order (by index)
        - Dict[int, int]: Map channel indices (0-N) to brightness values (0-100)
        - None: Default to 100 for all channels

        Args:
            sunrise: Sunrise time
            sunset: Sunset time
            brightness: Brightness configuration (int, tuple, dict, or None). Defaults to 100.
            ramp_up_in_minutes: Ramp up time in minutes
            weekdays: List of weekdays, defaults to everyday
        """
        # Normalize brightness to tuple in device channel order
        if brightness is None:
            brightness = 100

        if isinstance(brightness, int):
            # Single brightness value: apply to all channels
            num_channels = len(set(self._colors.values()))
            brightness_tuple = tuple(brightness for _ in range(num_channels))

        elif isinstance(brightness, dict):
            # Dict mapping channel indices to brightness values
            num_channels = len(set(self._colors.values()))
            brightness_values = []
            for i in range(num_channels):
                brightness_values.append(brightness.get(i, 100))
            brightness_tuple = tuple(brightness_values)

        else:
            # Assume tuple of brightness values in device channel order
            brightness_tuple = brightness

        cmd = commands.create_add_auto_setting_command(
            self.get_next_msg_id(),
            sunrise,
            sunset,
            brightness_tuple,
            ramp_up_in_minutes,
            commands.encode_weekdays(weekdays or ["everyday"]),
        )
        await self._send_command(cmd, 3)

    async def remove_setting(
        self,
        sunrise,
        sunset,
        ramp_up_in_minutes: int = 0,
        weekdays: Sequence[str] | None = None,
    ) -> None:
        """Remove an automation setting from the light."""
        cmd = commands.create_delete_auto_setting_command(
            self.get_next_msg_id(),
            sunrise.time(),
            sunset.time(),
            ramp_up_in_minutes,
            commands.encode_weekdays(weekdays or ["everyday"]),
        )
        await self._send_command(cmd, 3)

    async def reset_settings(self) -> None:
        """Remove all automation settings from the light."""
        cmd = commands.create_reset_auto_settings_command(self.get_next_msg_id())
        await self._send_command(cmd, 3)

    async def enable_auto_mode(self) -> None:
        """Enable auto mode of the light."""
        switch_cmd = commands.create_switch_to_auto_mode_command(self.get_next_msg_id())
        time_cmd = commands.create_set_time_command(self.get_next_msg_id())
        await self._send_command(switch_cmd, 3)
        await self._send_command(time_cmd, 3)

    async def set_manual_mode(self) -> None:
        """Switch to manual mode by sending a manual mode command."""
        await self.set_brightness(0)
