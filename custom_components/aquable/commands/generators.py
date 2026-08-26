"""Pure functional payload generators for device workflows.

These functions encapsulate the domain knowledge of *what* bytes to send
to achieve a specific outcome, without knowing *how* to send them via BLE.
They accept the necessary parameters and the current message ID, and return
the incremented message ID along with a sequential list of bytearrays to transmit.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from . import encoder


def generate_doser_set_daily_dose_sequence(
    start_msg_id: tuple[int, int],
    head_index: int,
    volume_tenths_ml: int,
    hour: int,
    minute: int,
    weekdays: Sequence[str] | None = None,
) -> tuple[tuple[int, int], list[bytearray]]:
    """Generate the exact sequence of commands to set a daily dose on a doser.

    Uses the 8-command sequence proven from the iPhone app packet capture:
    1. Handshake
    2. Time Sync 1
    3. Time Sync 2
    4. Prepare (0x04)
    5. Prepare (0x05)
    6. Select Head
    7. Set Dose and Weekdays
    8. Set Schedule Time

    Args:
        start_msg_id: The current message ID session state
        head_index: 1-based head index (1-4)
        volume_tenths_ml: volume to dose
        hour: hour of day
        minute: minute of hour
        weekdays: days of the week to run

    Returns:
        A tuple of (final_msg_id, list_of_command_payloads)
    """
    ble_head_index = head_index - 1
    weekday_mask = encoder.encode_weekdays(weekdays)

    msg_id = start_msg_id
    commands = []

    # 1. Handshake
    msg_id = encoder.next_message_id(msg_id)
    commands.append(encoder.create_handshake_command(msg_id))

    # 2. First time sync
    msg_id = encoder.next_message_id(msg_id)
    commands.append(encoder.create_set_time_command(msg_id))

    # 3. Second time sync (confirmation)
    msg_id = encoder.next_message_id(msg_id)
    commands.append(encoder.create_set_time_command(msg_id))

    # 4. Prepare stage 0x04
    msg_id = encoder.next_message_id(msg_id)
    # create_prepare_command signature: (msg_id, stage)
    # Using raw encode_uart_command if prepare helper missing in encoder,
    # assuming encoder has `create_prepare_command` based on prior file reads
    commands.append(encoder.create_prepare_command(msg_id, 0x04))

    # 5. Prepare stage 0x05
    msg_id = encoder.next_message_id(msg_id)
    commands.append(encoder.create_prepare_command(msg_id, 0x05))

    # 6. Head select
    msg_id = encoder.next_message_id(msg_id)
    commands.append(encoder.create_head_select_command(msg_id, ble_head_index))

    # 7. Head dose (volume & days)
    msg_id = encoder.next_message_id(msg_id)
    commands.append(
        encoder.create_head_dose_command(
            msg_id, ble_head_index, volume_tenths_ml, weekday_mask=weekday_mask
        )
    )

    # 8. Head schedule (time)
    msg_id = encoder.next_message_id(msg_id)
    commands.append(encoder.create_head_schedule_command(msg_id, ble_head_index, hour, minute))

    return msg_id, commands


def generate_doser_manual_dose_sequence(
    start_msg_id: tuple[int, int],
    head_index: int,
    volume_tenths_ml: int,
) -> tuple[tuple[int, int], list[bytearray]]:
    """Generate command to trigger an immediate manual dose."""
    msg_id = encoder.next_message_id(start_msg_id)
    # head_index logic follows 0-based for ble commands (head 1 -> 0)
    ble_head_index = head_index - 1
    return msg_id, [encoder.create_manual_dose_command(msg_id, ble_head_index, volume_tenths_ml)]


def generate_light_set_brightness_sequence(
    start_msg_id: tuple[int, int],
    colors: dict[int, int],
) -> tuple[tuple[int, int], list[bytearray]]:
    """Generate commands to set manual brightness on a light.

    Args:
        start_msg_id: Current message ID state
        colors: A dictionary mapping channel index to brightness value (0-100)
    """
    msg_id = start_msg_id
    commands = []

    for channel_id in sorted(colors.keys()):
        brightness_value = colors[channel_id]
        msg_id = encoder.next_message_id(msg_id)
        commands.append(encoder.create_manual_setting_command(msg_id, channel_id, brightness_value))

    return msg_id, commands


def generate_light_add_auto_setting_sequence(
    start_msg_id: tuple[int, int],
    sunrise: datetime.time,
    sunset: datetime.time,
    brightness: tuple[int, ...],
    ramp_up_minutes: int = 0,
    weekdays: Sequence[str] | None = None,
) -> tuple[tuple[int, int], list[bytearray]]:
    """Generate command to add an auto program setting."""
    msg_id = encoder.next_message_id(start_msg_id)
    weekday_mask = encoder.encode_weekdays(weekdays or ["everyday"])

    cmd = encoder.create_add_auto_setting_command(
        msg_id,
        sunrise,
        sunset,
        brightness,
        ramp_up_minutes,
        weekday_mask,
    )
    return msg_id, [cmd]


def generate_light_enable_auto_mode_sequence(
    start_msg_id: tuple[int, int],
) -> tuple[tuple[int, int], list[bytearray]]:
    """Generate sequence to switch light to auto mode and sync time."""
    msg_id = start_msg_id
    commands = []

    msg_id = encoder.next_message_id(msg_id)
    commands.append(encoder.create_switch_to_auto_mode_command(msg_id))

    msg_id = encoder.next_message_id(msg_id)
    commands.append(encoder.create_set_time_command(msg_id))

    return msg_id, commands


def generate_handshake_sequence(
    start_msg_id: tuple[int, int],
) -> tuple[tuple[int, int], list[bytearray]]:
    """Generate a single handshake request (used for status retrieval)."""
    msg_id = encoder.next_message_id(start_msg_id)
    return msg_id, [encoder.create_handshake_command(msg_id)]


def generate_light_clear_schedules_sequence(
    start_msg_id: tuple[int, int],
) -> tuple[tuple[int, int], list[bytearray]]:
    """Generate sequence to clear all auto schedules."""
    msg_id = encoder.next_message_id(start_msg_id)
    return msg_id, [encoder.create_reset_auto_settings_command(msg_id)]
