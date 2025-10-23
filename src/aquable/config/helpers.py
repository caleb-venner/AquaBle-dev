"""Helper functions for device configuration management.

This module provides utilities for creating default configurations,
updating configurations based on commands, and syncing configurations
between the service and storage.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, cast
from uuid import uuid4

from ..storage import (
    AutoProfile,
    AutoProgram,
    Calibration,
    ChannelDef,
    ConfigurationRevision,
    DeviceConfiguration,
    DoserDevice,
    DoserHead,
    DoserHeadStats,
    DoserWeekday,
    LightConfiguration,
    LightDevice,
    LightProfileRevision,
    LightWeekday,
    ManualProfile,
    Recurrence,
    SingleSchedule,
)
from ..utils import now_iso as _now_iso

logger = logging.getLogger(__name__)

# ========== Doser Configuration Helpers ==========


def update_doser_schedule_config(device: DoserDevice, args: Dict[str, Any]) -> DoserDevice:
    """Update a doser device configuration based on set_schedule command args.

    Args:
        device: The DoserDevice to update
        args: Command arguments from set_schedule command

    Returns:
        Updated DoserDevice (same instance, modified in place)
    """
    head_index = args["head_index"]
    volume_tenths_ml = args["volume_tenths_ml"]
    hour = args["hour"]
    minute = args["minute"]
    weekdays = args.get("weekdays")

    # Get active configuration
    config = device.get_active_configuration()
    latest = config.latest_revision()

    # Find the head to update
    target_head = None
    for head in latest.heads:
        if head.index == head_index:
            target_head = head
            break

    if target_head is None:
        raise ValueError(f"Head {head_index} not found in device {device.id} configuration")

    # Update the head schedule
    target_head.active = True
    target_head.schedule = SingleSchedule(
        mode="single",
        dailyDoseMl=volume_tenths_ml / 10.0,
        startTime=f"{hour:02d}:{minute:02d}",
    )

    # Update weekdays if provided
    if weekdays:
        weekday_names = []
        for weekday in weekdays:
            if hasattr(weekday, "name"):
                # Convert enum names to lowercase full weekday strings
                weekday_names.append(weekday.name.lower())
            else:
                # Already a string, ensure it's lowercase
                weekday_names.append(str(weekday).lower())
        target_head.recurrence.days = weekday_names

    # Update timestamps
    timestamp = _now_iso()
    config.updatedAt = timestamp
    device.updatedAt = timestamp

    logger.info(
        f"Updated head {head_index} schedule: "
        f"{volume_tenths_ml / 10.0}ml at {hour:02d}:{minute:02d}"
    )

    return device


def create_doser_config_from_command(address: str, args: Dict[str, Any]) -> DoserDevice:
    """Create a minimal DoserDevice configuration from a set_schedule command.

    This is called when a doser device executes a command but has no saved config yet.
    Creates a minimal config containing only the head being configured.
    Other heads are NOT created upfront - users configure them as needed.

    Args:
        address: The device MAC address
        args: Command arguments from set_schedule command

    Returns:
        Minimal DoserDevice with one head configured from command
    """
    timestamp = _now_iso()
    device_name = f"Doser {address[-8:]}"

    # Extract command parameters
    head_index = args["head_index"]
    volume_tenths_ml = args["volume_tenths_ml"]
    hour = args["hour"]
    minute = args["minute"]
    weekdays = args.get("weekdays")

    # Convert weekday enum/strings to lowercase names
    weekday_names = []
    if weekdays:
        for weekday in weekdays:
            if hasattr(weekday, "name"):
                # Convert enum names to lowercase full weekday strings
                weekday_names.append(weekday.name.lower())
            else:
                # Already a string, ensure it's lowercase
                weekday_names.append(str(weekday).lower())
    else:
        # Default to all days if not specified
        weekday_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]

    # Create only the head being configured (1-based index in storage)
    head_storage_index = head_index + 1
    head = DoserHead(
        index=head_storage_index,  # type: ignore[arg-type]
        label=f"Head {head_storage_index}",
        active=True,
        schedule=SingleSchedule(
            mode="single",
            dailyDoseMl=volume_tenths_ml / 10.0,
            startTime=f"{hour:02d}:{minute:02d}",
        ),
        recurrence=Recurrence(days=cast(list[DoserWeekday], weekday_names)),
        missedDoseCompensation=False,
        calibration=Calibration(mlPerSecond=0.1, lastCalibratedAt=timestamp),
        stats=DoserHeadStats(dosesToday=0, mlDispensedToday=0.0),
    )

    # Create minimal config: just the head being configured
    revision = ConfigurationRevision(
        revision=1,
        savedAt=timestamp,
        heads=[head],
        note=f"Created from set_schedule command for head {head_storage_index}",
        savedBy="system",
    )

    # Create default configuration
    configuration = DeviceConfiguration(
        id="default",
        name="Default Configuration",
        description="Auto-generated from set_schedule command",
        createdAt=timestamp,
        updatedAt=timestamp,
        revisions=[revision],
    )

    # Create device
    device = DoserDevice(
        id=address,
        name=device_name,
        configurations=[configuration],
        activeConfigurationId="default",
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    logger.info(
        "Created minimal doser config for %s from schedule command, head %s",
        address,
        head_storage_index,
    )

    return device


# ========== Light Device Configuration Helpers ==========


def update_light_manual_profile(device: LightDevice, levels: Dict[str, int]) -> LightDevice:
    """Update or create a manual profile in the active configuration.

    Saves manual brightness levels as a new revision in the active configuration.
    This persists the current manual brightness state to the device's configuration file.

    Args:
        device: The LightDevice to update
        levels: Dictionary of channel keys to brightness values (0-100)
                Must have all device channels present

    Returns:
        Updated LightDevice with new manual profile revision
    """
    active_config = device.get_active_configuration()
    latest_revision = active_config.latest_revision()

    # Create new manual profile
    profile = ManualProfile(mode="manual", levels=levels)

    # Create new revision
    next_revision_num = latest_revision.revision + 1
    timestamp = _now_iso()

    new_revision = LightProfileRevision(
        revision=next_revision_num,
        savedAt=timestamp,
        profile=profile,
        note="Manual brightness adjustment",
        savedBy="user",
    )

    # Add to configuration
    active_config.revisions.append(new_revision)
    active_config.updatedAt = timestamp
    device.updatedAt = timestamp

    logger.info(f"Updated manual profile for {device.id} (revision {next_revision_num})")
    return device


def add_light_auto_program(
    device: LightDevice,
    program_id: str,
    label: str,
    enabled: bool,
    sunrise: str,
    sunset: str,
    levels: Dict[str, int],
    ramp_minutes: int,
    weekdays: list[str],
) -> LightDevice:
    """Add an auto program to active profile.

    Args:
        device: The LightDevice to update
        program_id: Unique program ID (typically UUID)
        label: Display label for the program
        enabled: Whether program is enabled
        sunrise: Sunrise time (HH:MM format)
        sunset: Sunset time (HH:MM format)
        levels: Dictionary of channel keys to brightness values (0-100)
        ramp_minutes: Ramp-up duration in minutes
        weekdays: List of lowercase weekday strings

    Returns:
        Updated LightDevice with new timestamps
    """
    active_config = device.get_active_configuration()
    active_profile = active_config.latest_revision()

    # Create auto program
    program = AutoProgram(
        id=program_id,
        label=label,
        enabled=enabled,
        days=cast(list[LightWeekday], weekdays),
        sunrise=sunrise,
        sunset=sunset,
        rampMinutes=ramp_minutes,
        levels=levels,
    )

    # Update profile to auto mode or add to existing auto programs
    if isinstance(active_profile.profile, AutoProfile):
        active_profile.profile.programs.append(program)
    else:
        active_profile.profile = AutoProfile(mode="auto", programs=[program])

    timestamp = _now_iso()
    active_config.updatedAt = timestamp
    device.updatedAt = timestamp

    return device


def create_light_config_from_command(
    address: str,
    command_type: str,
    args: Dict[str, Any],
    channels_info: list[Dict[str, Any]],
) -> LightDevice:
    """Create a minimal LightDevice config from a command.

    This is called when a light device executes a command but has no saved config yet.
    Creates a minimal config containing just the command data and device channels.
    User metadata is NOT created - frontend displays defaults.

    Args:
        address: The device MAC address
        command_type: Type of command ("brightness", "multi_channel_brightness", "auto_program")
        args: Command arguments
        channels_info: Device channel info from connected device (required)
                      List of {"name": "...", "index": ...} dicts

    Returns:
        Minimal LightDevice with one configuration containing the command data

    Raises:
        ValueError: If channels_info is missing or empty
    """
    if not channels_info:
        raise ValueError(f"Cannot create light config for {address}: no channel info provided")

    timestamp = _now_iso()
    device_name = f"Light {address[-8:]}"

    # Create channel defs from device info
    sorted_channels = sorted(channels_info, key=lambda ch: ch.get("index", 0))
    channel_defs = [
        ChannelDef(key=ch["name"].lower(), label=ch["name"].capitalize(), min=0, max=100, step=1)
        for ch in sorted_channels
    ]

    # Create profile based on command type
    if command_type == "brightness":
        brightness = args.get("brightness", 50)
        color = args.get("color", 0)

        # Convert single brightness + color index to list format
        # [0, 0, brightness, 0] for color=2, for example
        brightness_list = [0] * len(channel_defs)
        if color < len(channel_defs):
            brightness_list[color] = brightness

        # Normalize brightness list to channel keys
        levels = {}
        for i, ch in enumerate(channel_defs):
            if i < len(brightness_list):
                levels[ch.key] = int(brightness_list[i])
            else:
                levels[ch.key] = 0

        profile = ManualProfile(mode="manual", levels=levels)
        note = "Created from brightness command"

    elif command_type == "multi_channel_brightness":
        channels = args.get("channels", [])

        # Normalize brightness list to channel keys
        levels = {}
        for i, ch in enumerate(channel_defs):
            if i < len(channels):
                levels[ch.key] = int(channels[i])
            else:
                levels[ch.key] = 0

        profile = ManualProfile(mode="manual", levels=levels)
        note = "Created from multi-channel brightness command"

    elif command_type == "auto_program":
        sunrise = args["sunrise"]
        sunset = args["sunset"]
        brightness_arg = args.get("brightness") or args.get("channels")
        ramp_up_minutes = args.get("ramp_up_minutes", 0)
        weekdays = args.get("weekdays")
        label = args.get("label")

        # Normalize brightness to list format
        if brightness_arg is None:
            brightness_list = [0] * len(channel_defs)
        elif isinstance(brightness_arg, (list, tuple)):
            brightness_list = list(brightness_arg)
        elif isinstance(brightness_arg, dict):
            # Dict format - extract per-channel values in order
            brightness_list = [brightness_arg.get(ch.key, 100) for ch in channel_defs]
        else:
            # Single int - apply to all channels
            brightness_list = [int(brightness_arg)] * len(channel_defs)

        # Normalize brightness list to channel keys
        levels = {}
        for i, ch in enumerate(channel_defs):
            if i < len(brightness_list):
                levels[ch.key] = int(brightness_list[i])
            else:
                levels[ch.key] = 0

        # Normalize weekdays
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

        program = AutoProgram(
            id=str(uuid4()),
            label=label or f"Auto {sunrise}-{sunset}",
            enabled=True,
            days=cast(list[LightWeekday], weekdays),
            sunrise=sunrise,
            sunset=sunset,
            rampMinutes=ramp_up_minutes,
            levels=levels,
        )

        profile = AutoProfile(mode="auto", programs=[program])
        note = f"Created from auto program command ({sunrise}-{sunset})"

    else:
        raise ValueError(f"Unsupported command type: {command_type}")

    # Create minimal config: just command data + device channels
    revision = LightProfileRevision(
        revision=1,
        savedAt=timestamp,
        profile=profile,
        note=note,
        savedBy="system",
    )

    configuration = LightConfiguration(
        id="default",
        name="Default Configuration",
        description=f"Auto-generated from {command_type} command",
        revisions=[revision],
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    device = LightDevice(
        id=address,
        name=device_name,
        channels=channel_defs,
        configurations=[configuration],
        activeConfigurationId="default",
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    logger.info(f"Created minimal light config for {address} from {command_type} command")
    return device
