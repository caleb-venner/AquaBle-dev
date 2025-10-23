"""Command execution service for device commands."""

from __future__ import annotations

import asyncio
import logging
from datetime import time
from typing import Any, Dict, Optional
from uuid import uuid4

from bleak_retry_connector import BleakConnectionError, BleakNotFoundError
from fastapi import HTTPException
from pydantic import ValidationError

from ..ble_service import BLEService
from ..commands_model import COMMAND_ARG_SCHEMAS, CommandRecord, CommandRequest
from ..constants import BLE_DOSER_SCHEDULE_WAIT, COMMAND_TIMEOUT_DEFAULT
from ..errors import CommandValidationError, ErrorCode
from ..utils import cached_status_to_dict

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes commands on devices through BLE service."""

    def __init__(self, ble_service: BLEService):
        """Execute commands on devices through BLE service."""
        self.ble_service = ble_service
        self._device_locks: Dict[str, asyncio.Lock] = {}

    def _get_device_channels(self, address: str) -> Optional[list[Dict[str, Any]]]:
        """Get channel info for a device from cached status.

        Used for auto_setting to create channel levels dict.
        """
        snapshot = self.ble_service.get_status_snapshot()
        cached_status = snapshot.get(address)
        if cached_status and hasattr(cached_status, "parsed"):
            parsed = cached_status.parsed
            if parsed and isinstance(parsed, dict) and "channels" in parsed:
                channels = parsed.get("channels")
                if isinstance(channels, list):
                    return channels
        return None

    def _get_device_lock(self, address: str) -> asyncio.Lock:
        """Get or create a lock for device operations."""
        if address not in self._device_locks:
            self._device_locks[address] = asyncio.Lock()
        return self._device_locks[address]

    def validate_command_args(
        self, action: str, args: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Validate command arguments against schema and return normalized args.

        Returns the normalized args dict with enums and other types properly converted,
        or None if no args are needed.
        """
        schema_class = COMMAND_ARG_SCHEMAS.get(action)
        if schema_class is None:
            # Action requires no arguments
            if args is not None and args:
                raise CommandValidationError(f"Action '{action}' does not accept arguments")
            return None

        if args is None:
            raise CommandValidationError(f"Action '{action}' requires arguments")

        try:
            validated_model = schema_class(**args)
            # Return the validated model as a dict to ensure enums are properly converted
            return validated_model.model_dump()
        except ValidationError as exc:
            raise CommandValidationError(f"Invalid arguments for '{action}': {exc}") from exc

    async def execute_command(self, address: str, request: CommandRequest) -> CommandRecord:
        """Execute a command synchronously and return the record."""
        # Validate command arguments and get normalized args
        normalized_args = request.args
        try:
            normalized_args = self.validate_command_args(request.action, request.args)
        except CommandValidationError as exc:
            record = CommandRecord(
                address=address,
                action=request.action,
                args=request.args,
                timeout=request.timeout or COMMAND_TIMEOUT_DEFAULT,
            )
            if request.id is not None:
                record.id = request.id
            record.mark_failed(str(exc), ErrorCode.VALIDATION_ERROR)
            return record

        # Create command record with normalized args
        record = CommandRecord(
            address=address,
            action=request.action,
            args=normalized_args,
            timeout=request.timeout or COMMAND_TIMEOUT_DEFAULT,
        )
        if request.id is not None:
            record.id = request.id

        # Acquire device lock to prevent concurrent operations
        lock = self._get_device_lock(address)

        try:
            async with lock:
                record.mark_started()

                # Execute with timeout
                try:
                    result = await asyncio.wait_for(
                        self._execute_action(address, request.action, normalized_args or {}),
                        timeout=record.timeout,
                    )
                    record.mark_success(result)

                except asyncio.TimeoutError:
                    record.mark_timeout()
                    logger.warning(
                        "Command %s timed out for device %s after %s seconds",
                        request.action,
                        address,
                        record.timeout,
                    )

                except HTTPException:
                    # HTTPExceptions should propagate up to the API layer
                    # Don't catch them here as they contain important status info
                    raise

                except (BleakNotFoundError, BleakConnectionError) as exc:
                    error_msg = f"Device communication failed: {exc}"
                    record.mark_failed(error_msg, ErrorCode.BLE_CONNECTION_ERROR)
                    logger.error(
                        "Command %s failed for device %s: %s",
                        request.action,
                        address,
                        error_msg,
                    )

                except ValueError as exc:
                    # ValueError typically indicates invalid parameters or device state
                    error_msg = f"Invalid operation: {exc}"
                    record.mark_failed(error_msg, ErrorCode.INVALID_ARGUMENTS)
                    logger.error(
                        "Command %s failed for device %s: %s",
                        request.action,
                        address,
                        error_msg,
                    )

                except Exception as exc:
                    # Catch-all for unexpected errors
                    error_msg = f"Unexpected error during command execution: {exc}"
                    record.mark_failed(error_msg, ErrorCode.INTERNAL_ERROR)
                    logger.error(
                        "Command %s failed for device %s: %s",
                        request.action,
                        address,
                        exc,
                        exc_info=True,
                    )

        except Exception as exc:
            # Lock acquisition failed or unexpected error
            record.mark_failed(f"Lock acquisition failed: {exc}", ErrorCode.INTERNAL_ERROR)
            logger.error("Failed to acquire lock for device %s: %s", address, exc)

        return record

    async def _execute_action(
        self, address: str, action: str, args: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Execute the specific action on the device."""
        # Map actions to BLE service methods
        if action == "turn_on":
            status = await self.ble_service.turn_light_on(address)
            return cached_status_to_dict(self.ble_service, status)

        elif action == "turn_off":
            status = await self.ble_service.turn_light_off(address)
            return cached_status_to_dict(self.ble_service, status)

        elif action == "set_brightness":
            status = await self.ble_service.set_light_brightness(
                address,
                brightness=args["brightness"],
                color=args.get("color", 0),
            )

            # Save manual brightness to persistent config
            await self._save_light_brightness_config(address, args)

            return cached_status_to_dict(self.ble_service, status)

        elif action == "enable_auto_mode":
            status = await self.ble_service.enable_auto_mode(address)
            return cached_status_to_dict(self.ble_service, status)

        elif action == "set_manual_mode":
            status = await self.ble_service.set_manual_mode(address)
            return cached_status_to_dict(self.ble_service, status)

        elif action == "reset_auto_settings":
            status = await self.ble_service.reset_auto_settings(address)
            return cached_status_to_dict(self.ble_service, status)

        elif action == "add_auto_setting":
            # Convert string times to datetime.time objects
            sunrise_str = args["sunrise"]
            sunset_str = args["sunset"]

            def parse_time(time_str: str) -> time:
                """Convert HH:MM string to datetime.time object."""
                hours, minutes = time_str.split(":")
                return time(int(hours), int(minutes))

            # Handle either single brightness or per-channel brightness
            brightness_arg = args.get("brightness") or args.get("channels")
            if brightness_arg is None:
                raise ValueError("Either 'brightness' or 'channels' must be provided")

            # Weekdays are already converted to LightWeekday enums by the validator
            weekdays_arg = args.get("weekdays")

            status = await self.ble_service.add_light_auto_setting(
                address,
                sunrise=parse_time(sunrise_str),
                sunset=parse_time(sunset_str),
                brightness=brightness_arg,
                ramp_up_minutes=args.get("ramp_up_minutes", 0),
                weekdays=weekdays_arg,
            )

            # Update and persist light configuration
            await self._save_light_auto_setting_config(address, args)

            return cached_status_to_dict(self.ble_service, status)

        elif action == "set_schedule":
            # Weekdays are already converted to PumpWeekday enums by the validator
            status = await self.ble_service.set_doser_schedule(
                address,
                head_index=args["head_index"],
                volume_tenths_ml=args["volume_tenths_ml"],
                hour=args["hour"],
                minute=args["minute"],
                weekdays=args.get("weekdays"),  # List[PumpWeekday] from validator
                confirm=args.get("confirm", True),
                wait_seconds=args.get("wait_seconds", BLE_DOSER_SCHEDULE_WAIT),
            )

            # Update and persist doser configuration
            await self._save_doser_schedule_config(address, args)

            return cached_status_to_dict(self.ble_service, status)

        else:
            raise ValueError(f"Unsupported action: {action}")

    async def _save_doser_schedule_config(self, address: str, args: Dict[str, Any]) -> None:
        """Save doser schedule configuration after successful command.

        Args:
            address: Device MAC address
            args: Command arguments from set_schedule
        """
        if not self.ble_service._auto_save_config:
            logger.debug("Auto-save config disabled, skipping")
            return

        try:
            from .helpers import update_doser_schedule_config

            device = self.ble_service._doser_storage.get_device(address)
            if device:
                # Update the existing configuration
                device = update_doser_schedule_config(device, args)
                self.ble_service._doser_storage.upsert_device(device)
                logger.info(
                    f"Saved doser configuration for {address}, " f"head {args['head_index']}"
                )
            else:
                # Create new configuration from the actual command being sent
                from .helpers import create_doser_config_from_command

                logger.info(
                    f"Creating new configuration for doser {address} " f"from schedule command"
                )
                device = create_doser_config_from_command(address, args)
                self.ble_service._doser_storage.upsert_device(device)
                logger.info(
                    f"Created and saved new doser configuration for {address}, "
                    f"head {args['head_index']}"
                )
        except Exception as exc:
            # Don't fail the command if config save fails
            logger.error(
                f"Failed to save doser configuration for {address}: {exc}",
                exc_info=True,
            )

    async def _save_light_auto_setting_config(self, address: str, args: Dict[str, Any]) -> None:
        """Save light auto setting configuration after successful command.

        Args:
            address: Device MAC address
            args: Command arguments from add_auto_setting
        """
        if not self.ble_service._auto_save_config:
            logger.debug("Auto-save config disabled, skipping")
            return

        try:
            from .helpers import add_light_auto_program, create_light_config_from_command

            brightness_arg = args.get("brightness")
            if brightness_arg is None:
                raise ValueError("'brightness' must be provided")

            device = self.ble_service._light_storage.get_device(address)

            if not device:
                # Create new configuration
                channels_info = self._get_device_channels(address)
                if not channels_info:
                    logger.warning(
                        f"Cannot create config for {address}: device channels not cached. "
                        f"Command executed but no config saved."
                    )
                    return

                device = create_light_config_from_command(
                    address, "auto_program", args, channels_info
                )
                self.ble_service._light_storage.upsert_device(device)
                logger.info(
                    f"Created and saved new light profile for {address} "
                    f"from auto program command {args['sunrise']}-{args['sunset']}"
                )
                return

            # Convert brightness to levels dict for all channels
            channels_info = self._get_device_channels(address)
            if not channels_info:
                logger.warning(
                    f"Could not save auto program for {address}: device channels not cached"
                )
                return

            # Build channel dict with brightness value for all channels
            sorted_channels = sorted(channels_info, key=lambda ch: ch.get("index", 0))
            channel_keys = [ch["name"].lower() for ch in sorted_channels]
            brightness_val = int(brightness_arg) if isinstance(brightness_arg, int) else 50
            levels = {key: brightness_val for key in channel_keys}

            # Normalize weekdays
            weekdays = args.get("weekdays")
            if weekdays is None:
                weekdays = [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
            else:
                weekdays = [
                    (day.value.lower() if hasattr(day, "value") else str(day).lower())
                    for day in weekdays
                ]

            # Update the existing configuration
            device = add_light_auto_program(
                device,
                program_id=str(uuid4()),
                label=args.get("label") or f"Auto {args['sunrise']}-{args['sunset']}",
                enabled=True,
                sunrise=args["sunrise"],
                sunset=args["sunset"],
                levels=levels,
                ramp_minutes=args.get("ramp_up_minutes", 0),
                weekdays=weekdays,
            )
            self.ble_service._light_storage.upsert_device(device)
            logger.info(
                f"Saved light auto program for {address}, " f"{args['sunrise']}-{args['sunset']}"
            )
        except Exception as exc:
            logger.error(
                f"Failed to save light auto program for {address}: {exc}",
                exc_info=True,
            )

    async def _save_light_brightness_config(self, address: str, args: Dict[str, Any]) -> None:
        """Save manual brightness configuration after successful set_brightness command.

        Args:
            address: Device MAC address
            args: Command arguments from set_brightness (brightness, color)
        """
        if not self.ble_service._auto_save_config:
            logger.debug("Auto-save config disabled, skipping")
            return

        try:
            from .helpers import (
                create_light_config_from_command,
                update_light_manual_profile,
            )

            brightness = args.get("brightness", 0)
            color_index = args.get("color", 0)

            device = self.ble_service._light_storage.get_device(address)

            if not device:
                # Create new configuration with manual profile from this command
                channels_info = self._get_device_channels(address)
                if not channels_info:
                    logger.warning(
                        f"Cannot create config for {address}: device channels not cached. "
                        f"Command executed but no config saved."
                    )
                    return

                device = create_light_config_from_command(
                    address, "brightness", args, channels_info
                )
                self.ble_service._light_storage.upsert_device(device)
                logger.info(
                    f"Created and saved new light config for {address} from brightness command"
                )
                return

            # Build levels dict from single brightness + color index
            channels_info = self._get_device_channels(address)
            if not channels_info:
                logger.warning(
                    f"Could not save brightness for {address}: device channels not cached"
                )
                return

            sorted_channels = sorted(channels_info, key=lambda ch: ch.get("index", 0))
            channel_keys = [ch["name"].lower() for ch in sorted_channels]

            # Set brightness for specified color, 0 for others
            levels = {}
            for i, key in enumerate(channel_keys):
                if i == color_index:
                    levels[key] = int(brightness)
                else:
                    levels[key] = 0

            # Update the existing configuration
            device = update_light_manual_profile(device, levels)
            self.ble_service._light_storage.upsert_device(device)
            logger.info(
                f"Saved manual brightness for {address}: " f"channel {color_index} = {brightness}%"
            )
        except Exception as exc:
            logger.error(
                f"Failed to save brightness config for {address}: {exc}",
                exc_info=True,
            )
