"""Helper functions for device configuration management.

This module provides utilities for creating default configurations,
updating configurations based on commands, and syncing configurations
between the service and storage.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, cast
from uuid import uuid4

from .commands.encoder import decode_pump_weekdays, pump_weekdays_to_names
from .doser_status import DoserStatus, HeadSnapshot
from .doser_storage import (
    Calibration,
    ConfigurationRevision,
    DeviceConfiguration,
    DoserDevice,
    DoserHead,
    DoserHeadStats,
    Recurrence,
    SingleSchedule,
    Weekday,
)
from .time_utils import now_iso as _now_iso

if TYPE_CHECKING:
    from .light_storage import LightDevice

logger = logging.getLogger(__name__)


def create_default_doser_config(address: str, name: str | None = None) -> DoserDevice:
    """Create a default configuration for a new doser device.

    Args:
        address: The device MAC address
        name: Optional friendly name for the device

    Returns:
        A DoserDevice with default configuration for 4 heads
    """
    device_name = name or f"Doser {address[-8:]}"
    timestamp = _now_iso()

    # Create default heads (all inactive by default)
    default_heads = []
    for idx in range(1, 5):
        head = DoserHead(
            index=idx,  # type: ignore[arg-type]
            label=f"Head {idx}",
            active=False,
            schedule=SingleSchedule(mode="single", dailyDoseMl=10.0, startTime="09:00"),
            recurrence=Recurrence(
                days=[
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
            ),
            missedDoseCompensation=False,
            calibration=Calibration(mlPerSecond=0.1, lastCalibratedAt=timestamp),
            stats=DoserHeadStats(dosesToday=0, mlDispensedToday=0.0),
        )
        default_heads.append(head)

    # Create initial revision
    revision = ConfigurationRevision(
        revision=1,
        savedAt=timestamp,
        heads=default_heads,
        note="Initial configuration",
        savedBy="system",
    )

    # Create default configuration
    configuration = DeviceConfiguration(
        id="default",
        name="Default Configuration",
        description="Auto-generated default configuration",
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

    return device


def create_doser_config_from_status(
    address: str,
    status: DoserStatus,
    existing: Optional[DoserDevice] = None,
    name: str | None = None,
) -> DoserDevice:
    """Create or update a DoserDevice configuration from device status.

    Args:
        address: The device MAC address
        status: Current device status from BLE
        existing: Existing device configuration to update (if any)
        name: Optional friendly name for the device

    Returns:
        Updated or new DoserDevice with configuration from status
    """
    timestamp = _now_iso()

    # Extract heads from status
    heads = []
    for head_snap in status.heads:
        # Determine if head is active based on mode
        is_active = head_snap.mode != 0x04  # 0x04 is disabled mode

        # Try to decode weekday information from device status
        # TODO: Parse per-head weekday information from HeadSnapshot.extra bytes
        # Currently, device status may contain weekday info at device level
        recurrence_days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]  # Default to all days
        if status.weekday is not None:
            try:
                pump_weekdays = decode_pump_weekdays(status.weekday)
                recurrence_days = pump_weekdays_to_names(pump_weekdays)
                if not recurrence_days:  # Empty list means no days selected
                    recurrence_days = [
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ]
            except Exception:
                # Fall back to all days if decoding fails
                pass

        head = DoserHead(
            index=(head_snap.mode + 1 if head_snap.mode < 4 else 1),  # type: ignore[arg-type]
            active=is_active,
            schedule=SingleSchedule(
                mode="single",
                dailyDoseMl=head_snap.dosed_ml() or 10.0,
                startTime=f"{head_snap.hour:02d}:{head_snap.minute:02d}",
            ),
            recurrence=Recurrence(days=cast(list[Weekday], recurrence_days)),
            missedDoseCompensation=False,
            calibration=Calibration(mlPerSecond=0.1, lastCalibratedAt=timestamp),
            stats=DoserHeadStats(dosesToday=0, mlDispensedToday=head_snap.dosed_ml()),
        )
        heads.append(head)

    if existing:
        # Update existing device with new revision
        logger.info(f"Updating existing config for doser {address}")
        device = existing
        config = device.get_active_configuration()

        # Add new revision
        next_revision = config.latest_revision().revision + 1
        new_revision = ConfigurationRevision(
            revision=next_revision,
            savedAt=timestamp,
            heads=heads,
            note="Updated from device status",
            savedBy="system",
        )
        config.revisions.append(new_revision)
        config.updatedAt = timestamp
        device.updatedAt = timestamp
    else:
        # Create new device
        logger.info(f"Creating new config for doser {address}")
        device_name = name or f"Doser {address[-8:]}"

        revision = ConfigurationRevision(
            revision=1,
            savedAt=timestamp,
            heads=heads,
            note="Created from device status",
            savedBy="system",
        )

        configuration = DeviceConfiguration(
            id="default",
            name="Default Configuration",
            description="Auto-generated from device status",
            createdAt=timestamp,
            updatedAt=timestamp,
            revisions=[revision],
        )

        device = DoserDevice(
            id=address,
            name=device_name,
            configurations=[configuration],
            activeConfigurationId="default",
            createdAt=timestamp,
            updatedAt=timestamp,
        )

    return device


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


def update_doser_head_stats(
    device: DoserDevice, head_index: int, status: HeadSnapshot
) -> DoserDevice:
    """Update statistics for a specific doser head.

    Args:
        device: The DoserDevice to update
        head_index: Index of the head (1-4)
        status: Head status snapshot from device

    Returns:
        Updated DoserDevice
    """
    config = device.get_active_configuration()
    latest = config.latest_revision()

    for head in latest.heads:
        if head.index == head_index:
            if head.stats is None:
                head.stats = DoserHeadStats(dosesToday=0, mlDispensedToday=0.0)
            head.stats.mlDispensedToday = status.dosed_ml()
            logger.debug(f"Updated head {head_index} stats: {status.dosed_ml()}ml dispensed")
            break

    device.updatedAt = _now_iso()
    return device


# ========== Light Device Configuration Helpers ==========


def create_default_light_profile(
    address: str,
    name: str | None = None,
    channels: list[Dict[str, Any]] | None = None,
) -> LightDevice:
    """Create a default profile for a new light device.

    Args:
        address: The device MAC address
        name: Optional friendly name for the device
        channels: Optional list of channel definitions from device

    Returns:
        A LightDevice with default manual profile
    """
    from .light_storage import (
        ChannelDef,
        LightConfiguration,
        LightDevice,
        LightProfileRevision,
        ManualProfile,
    )

    device_name = name or f"Light {address[-8:]}"
    timestamp = _now_iso()

    # Create default channel definitions if not provided
    if not channels:
        channel_defs = [
            ChannelDef(key="white", label="White", min=0, max=100, step=1),
            ChannelDef(key="red", label="Red", min=0, max=100, step=1),
            ChannelDef(key="green", label="Green", min=0, max=100, step=1),
            ChannelDef(key="blue", label="Blue", min=0, max=100, step=1),
        ]
    else:
        channel_defs = [
            ChannelDef(
                key=ch.get("name", f"channel{ch.get('index', 0)}").lower(),
                label=ch.get("name", f"Channel {ch.get('index', 0)}"),
                min=0,
                max=100,
                step=1,
            )
            for ch in channels
        ]

    # Create default manual profile (all channels at 50%)
    default_levels = {ch.key: 50 for ch in channel_defs}

    # Create a profile revision with the manual profile
    revision = LightProfileRevision(
        revision=1,
        savedAt=timestamp,
        profile=ManualProfile(mode="manual", levels=default_levels),
        note="Auto-generated default configuration",
    )

    # Create a configuration containing the revision
    default_config = LightConfiguration(
        id="default",
        name="Default Configuration",
        description="Auto-generated default configuration",
        revisions=[revision],
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    # Create device
    device = LightDevice(
        id=address,
        name=device_name,
        channels=channel_defs,
        configurations=[default_config],
        activeConfigurationId="default",
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    return device


def update_light_manual_profile(device: LightDevice, levels: Dict[str, int]) -> LightDevice:
    """Update light device's active manual profile with new levels.

    Args:
        device: The LightDevice to update
        levels: Dictionary of channel keys to brightness values

    Returns:
        Updated LightDevice
    """
    from .light_storage import ManualProfile

    # Get active profile
    active_config = device.get_active_configuration()
    active_profile = active_config.latest_revision()

    # Update or create manual profile
    if isinstance(active_profile.profile, ManualProfile):
        # Update existing manual profile
        active_profile.profile.levels.update(levels)
    else:
        # Convert to manual profile
        active_profile.profile = ManualProfile(mode="manual", levels=levels)

    timestamp = _now_iso()
    active_config.updatedAt = timestamp
    device.updatedAt = timestamp

    logger.info(f"Updated light {device.id} manual profile: {levels}")

    return device


def update_light_brightness(device: LightDevice, brightness: int, color: int = 0) -> LightDevice:
    """Update light brightness for a specific color channel.

    Args:
        device: The LightDevice to update
        brightness: Brightness level (0-100)
        color: Color channel index (default: 0 for all/white)

    Returns:
        Updated LightDevice
    """
    from .light_storage import ManualProfile

    # Get active profile
    active_config = device.get_active_configuration()
    active_profile = active_config.latest_revision()

    # Determine which channel to update
    if color < len(device.channels):
        channel_key = device.channels[color].key
    else:
        # Default to first channel
        channel_key = device.channels[0].key if device.channels else "white"

    # Update levels
    levels = {}
    if isinstance(active_profile.profile, ManualProfile):
        levels = dict(active_profile.profile.levels)

    levels[channel_key] = brightness

    # Update profile
    active_profile.profile = ManualProfile(mode="manual", levels=levels)

    timestamp = _now_iso()
    active_config.updatedAt = timestamp
    device.updatedAt = timestamp

    logger.info(f"Updated light {device.id} brightness: {channel_key}={brightness}")

    return device


def update_light_multi_channel_brightness(
    device: LightDevice, brightness_values: list[int]
) -> LightDevice:
    """Update light multi-channel brightness for all channels.

    Args:
        device: The LightDevice to update
        brightness_values: List of brightness values for channels
        in order [red, green, blue, white]

    Returns:
        Updated LightDevice
    """
    from .light_storage import ManualProfile

    # Get active profile
    active_config = device.get_active_configuration()
    active_profile = active_config.latest_revision()

    # Map brightness values to channel keys
    channel_keys = ["red", "green", "blue", "white"]
    levels: dict[str, int] = {}
    for i, brightness in enumerate(brightness_values):
        if i < len(channel_keys):
            levels[channel_keys[i]] = int(brightness)  # Explicit cast to int

    # Update profile
    active_profile.profile = ManualProfile(mode="manual", levels=levels)

    timestamp = _now_iso()
    active_config.updatedAt = timestamp
    device.updatedAt = timestamp

    logger.info(f"Updated light {device.id} multi-channel brightness: {levels}")

    return device


def add_light_auto_program(
    device: LightDevice,
    sunrise: str,
    sunset: str,
    brightness: int | dict[str, int],
    ramp_up_minutes: int = 0,
    weekdays: list[str] | None = None,
    label: str | None = None,
) -> LightDevice:
    """Add an auto program to light device's active profile.

    Args:
        device: The LightDevice to update
        sunrise: Sunrise time (HH:MM format)
        sunset: Sunset time (HH:MM format)
        brightness: Target brightness level (int) or per-channel levels (dict)
        ramp_up_minutes: Ramp-up duration in minutes
        weekdays: List of weekdays (default: all days)
        label: Optional custom label for the schedule (default: Auto {sunrise}-{sunset})

    Returns:
        Updated LightDevice
    """
    from .light_storage import AutoProfile, AutoProgram, LightProfileRevision

    # Create default levels for all channels
    active_config = device.get_active_configuration()
    active_profile = active_config.latest_revision()

    # Create default levels for all channels
    if isinstance(brightness, dict):
        levels = {ch.key: brightness.get(ch.key, 100) for ch in device.channels}
    else:
        # Use single brightness value for all channels
        levels = {ch.key: brightness for ch in device.channels}

    # Create new auto program - use full lowercase weekday name
    if weekdays is None:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    program = AutoProgram(
        id=str(uuid4()),
        label=label or f"Auto {sunrise}-{sunset}",
        enabled=True,
        days=cast(list["Weekday"], weekdays),
        sunrise=sunrise,
        sunset=sunset,
        rampMinutes=ramp_up_minutes,
        levels=levels,
    )

    # Update profile to auto mode or add to existing auto programs
    if isinstance(active_profile.profile, AutoProfile):
        active_profile.profile.programs.append(program)
    else:
        # Convert to auto profile
        active_profile.profile = AutoProfile(mode="auto", programs=[program])

    timestamp = _now_iso()
    active_config.updatedAt = timestamp
    device.updatedAt = timestamp

    logger.info(f"Added auto program to light {device.id}: {sunrise}-{sunset}")

    return device


def create_doser_config_from_command(address: str, args: Dict[str, Any]) -> DoserDevice:
    """Create a new DoserDevice configuration from a set_schedule command.

    Args:
        address: The device MAC address
        args: Command arguments from set_schedule command

    Returns:
        New DoserDevice with configuration from command
    """
    timestamp = _now_iso()
    device_name = f"Doser {address[-8:]}"

    # Extract command parameters
    head_index = args["head_index"]
    volume_tenths_ml = args["volume_tenths_ml"]
    hour = args["hour"]
    minute = args["minute"]
    weekdays = args.get("weekdays")

    # Create default heads (all inactive except the one being configured)
    heads = []
    for idx in range(1, 5):
        if idx == head_index + 1:  # head_index is 0-based in command, 1-based in storage
            # This is the head being configured
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

            head = DoserHead(
                index=idx,  # type: ignore[arg-type]
                label=f"Head {idx}",
                active=True,
                schedule=SingleSchedule(
                    mode="single",
                    dailyDoseMl=volume_tenths_ml / 10.0,
                    startTime=f"{hour:02d}:{minute:02d}",
                ),
                recurrence=Recurrence(days=cast(list[Weekday], weekday_names)),
                missedDoseCompensation=False,
                calibration=Calibration(mlPerSecond=0.1, lastCalibratedAt=timestamp),
                stats=DoserHeadStats(dosesToday=0, mlDispensedToday=0.0),
            )
        else:
            # Inactive head with default settings
            head = DoserHead(
                index=idx,  # type: ignore[arg-type]
                label=f"Head {idx}",
                active=False,
                schedule=SingleSchedule(mode="single", dailyDoseMl=10.0, startTime="09:00"),
                recurrence=Recurrence(
                    days=[
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ]
                ),
                missedDoseCompensation=False,
                calibration=Calibration(mlPerSecond=0.1, lastCalibratedAt=timestamp),
                stats=DoserHeadStats(dosesToday=0, mlDispensedToday=0.0),
            )
        heads.append(head)

    # Create initial revision
    revision = ConfigurationRevision(
        revision=1,
        savedAt=timestamp,
        heads=heads,
        note=f"Created from set_schedule command for head {head_index + 1}",
        savedBy="system",
    )

    # Create default configuration
    configuration = DeviceConfiguration(
        id="default",
        name="Default Configuration",
        description=f"Auto-generated from set_schedule command",
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
        f"Created new doser config for {address} from schedule command, head {head_index + 1}"
    )

    return device


def create_light_config_from_command(
    address: str, command_type: str, args: Dict[str, Any]
) -> LightDevice:
    """Create a new LightDevice configuration from a command.

    Args:
        address: The device MAC address
        command_type: Type of command ("brightness", "multi_channel_brightness", "auto_program")
        args: Command arguments

    Returns:
        New LightDevice with configuration from command
    """
    from .light_storage import (
        AutoProfile,
        AutoProgram,
        ChannelDef,
        LightConfiguration,
        LightDevice,
        LightProfileRevision,
        ManualProfile,
    )

    timestamp = _now_iso()
    device_name = f"Light {address[-8:]}"

    # Create default channel definitions
    # Use standard RGBW channel layout
    channel_defs = [
        ChannelDef(key="red", label="Red", min=0, max=100, step=1),
        ChannelDef(key="green", label="Green", min=0, max=100, step=1),
        ChannelDef(key="blue", label="Blue", min=0, max=100, step=1),
        ChannelDef(key="white", label="White", min=0, max=100, step=1),
    ]

    # Create profile based on command type
    if command_type == "brightness":
        # Single channel brightness command
        brightness = args.get("brightness", 50)
        color = args.get("color", 0)

        # Determine which channel to set
        if color < len(channel_defs):
            channel_key = channel_defs[color].key
        else:
            channel_key = "white"

        # Create manual profile with the brightness set for the specified channel
        levels = {ch.key: (brightness if ch.key == channel_key else 0) for ch in channel_defs}

        profile = ManualProfile(mode="manual", levels=levels)
        note = f"Created from brightness command ({channel_key}={brightness})"

    elif command_type == "multi_channel_brightness":
        # Multi-channel brightness command
        channels = args.get("channels", [])
        if not channels:
            channels = [0, 0, 0, 0]

        # Map channels to RGBW keys
        channel_keys = ["red", "green", "blue", "white"]
        levels = {}
        for i, brightness in enumerate(channels):
            if i < len(channel_keys):
                levels[channel_keys[i]] = int(brightness)

        # Fill in any missing channels with 0
        for ch in channel_defs:
            if ch.key not in levels:
                levels[ch.key] = 0

        profile = ManualProfile(mode="manual", levels=levels)
        note = f"Created from multi-channel brightness command"

    elif command_type == "auto_program":
        # Auto program command
        sunrise = args["sunrise"]
        sunset = args["sunset"]
        brightness_arg = args.get("brightness") or args.get("channels")
        ramp_up_minutes = args.get("ramp_up_minutes", 0)
        weekdays = args.get("weekdays")
        label = args.get("label")

        # Create levels for all channels
        if isinstance(brightness_arg, dict):
            levels = {ch.key: brightness_arg.get(ch.key, 100) for ch in channel_defs}
        elif isinstance(brightness_arg, (list, tuple)):
            # Multi-channel brightness values
            channel_keys = ["red", "green", "blue", "white"]
            levels = {}
            for i, brightness in enumerate(brightness_arg):
                if i < len(channel_keys):
                    levels[channel_keys[i]] = int(brightness)
            # Fill in missing channels
            for ch in channel_defs:
                if ch.key not in levels:
                    levels[ch.key] = 0
        else:
            # Single brightness value for all channels
            brightness_val = int(brightness_arg) if brightness_arg is not None else 100
            levels = {ch.key: brightness_val for ch in channel_defs}

        # Create auto program
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
            # Convert weekday enums to strings if needed
            weekdays = [
                (day.value.lower() if hasattr(day, "value") else str(day).lower())
                for day in weekdays
            ]

        program = AutoProgram(
            id=str(uuid4()),
            label=label or f"Auto {sunrise}-{sunset}",
            enabled=True,
            days=cast(list["Weekday"], weekdays),
            sunrise=sunrise,
            sunset=sunset,
            rampMinutes=ramp_up_minutes,
            levels=levels,
        )

        profile = AutoProfile(mode="auto", programs=[program])
        note = f"Created from auto program command ({sunrise}-{sunset})"

    else:
        raise ValueError(f"Unsupported command type: {command_type}")

    # Create profile revision
    revision = LightProfileRevision(
        revision=1,
        savedAt=timestamp,
        profile=profile,
        note=note,
        savedBy="system",
    )

    # Create configuration
    configuration = LightConfiguration(
        id="default",
        name="Default Configuration",
        description=f"Auto-generated from {command_type} command",
        revisions=[revision],
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    # Create device
    device = LightDevice(
        id=address,
        name=device_name,
        channels=channel_defs,
        configurations=[configuration],
        activeConfigurationId="default",
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    logger.info(f"Created new light config for {address} from {command_type} command")

    return device
