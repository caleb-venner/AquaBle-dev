"""Command encoders and related helpers for Chihiros devices."""

import datetime
from typing import Iterable, Sequence


def _calculate_checksum(input_bytes: bytes) -> int:
    """Calculate XOR-based checksum used by the light command encoder.

    This checksum starts with the second byte and XORs all subsequent
    bytes. The function name was previously `_calculate_light_checksum` but
    is generalized now since it is the canonical checksum for the encoder
    command framing.
    """
    assert len(input_bytes) >= 7  # commands are always at least 7 bytes long
    checksum = input_bytes[1]
    for input_byte in input_bytes[2:]:
        checksum = checksum ^ input_byte
    return checksum


def _encode_timestamp(ts: datetime.datetime) -> list[int]:
    """Encode a datetime into the device timestamp byte sequence."""
    # note: day is weekday e.g. 3 for wednesday
    return [
        ts.year - 2000,
        ts.month,
        ts.isoweekday(),
        ts.hour,
        ts.minute,
        ts.second,
    ]


def _encode_uart_command(
    cmd_id: int, mode: int, msg_id: tuple[int, int], params: Iterable[int]
) -> bytearray:
    """Return a UART frame compatible device protocols."""
    msg_hi, msg_lo = msg_id
    payload = list(params)
    sanitized = [(value if value != 0x5A else 0x59) for value in payload]

    command = bytearray([cmd_id, 0x01, len(sanitized) + 5, msg_hi, msg_lo, mode])
    command.extend(sanitized)

    verification_byte = _calculate_checksum(command)
    if verification_byte == 0x5A:
        # bump the message id using the canonical helper and retry
        new_msg_id = next_message_id(msg_id)
        return _encode_uart_command(cmd_id, mode, new_msg_id, params)

    command.append(verification_byte)
    return command


def next_message_id(current_msg_id: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    """Return the next message id pair, avoiding reserved values.

    The encoder uses two-byte message ids that skip 0x5A/90 in both
    positions. This helper encapsulates that wrap/skip behaviour with
    proper bounds checking and session reset capability.

    Args:
        current_msg_id: Current message ID as (higher_byte, lower_byte) tuple

    Returns:
        Next message ID as (higher_byte, lower_byte) tuple

    Raises:
        ValueError: If current_msg_id contains invalid values
    """
    msg_id_higher_byte, msg_id_lower_byte = current_msg_id

    # Validate input
    if not (0 <= msg_id_higher_byte <= 255) or not (0 <= msg_id_lower_byte <= 255):
        raise ValueError(f"Message ID bytes must be in range 0-255, got {current_msg_id}")

    if msg_id_higher_byte == 90 or msg_id_lower_byte == 90:
        raise ValueError(
            f"Message ID cannot contain reserved value 90 (0x5A), got {current_msg_id}"
        )

    # Handle lower byte increment
    if msg_id_lower_byte == 255:
        # Need to increment higher byte
        if msg_id_higher_byte == 255:
            # Wrap around to beginning, skip (0, 0) as it's the default start
            return (0, 1)
        elif msg_id_higher_byte == 89:
            # Skip 90 in higher byte position
            return (91, 0)
        else:
            return (msg_id_higher_byte + 1, 0)
    else:
        # Increment lower byte
        if msg_id_lower_byte == 89:
            # Skip 90 in lower byte position
            return (msg_id_higher_byte, 91)
        else:
            return (msg_id_higher_byte, msg_id_lower_byte + 1)


def reset_message_id() -> tuple[int, int]:
    """Reset message ID to the beginning of a new session.

    Returns:
        Initial message ID for a new session
    """
    return (0, 1)


def is_message_id_exhausted(current_msg_id: tuple[int, int]) -> bool:
    """Check if message ID is approaching exhaustion.

    Message IDs wrap around, but this can help detect if we're
    in a long-running session that might benefit from a reset.

    Args:
        current_msg_id: Current message ID

    Returns:
        True if message ID is in the last 10% of available values
    """
    higher, lower = current_msg_id
    # Total possible values: 256 * 256 = 65536, minus skipped values
    # For simplicity, consider it exhausted if higher byte >= 230 (~90% through)
    return higher >= 230


def create_handshake_command(msg_id: tuple[int, int]) -> bytearray:
    """Build a handshake/status request command (0x5A / mode 0x04).

    Used by both light and doser devices to request device status.
    For doser devices, this is also the initial synchronization command
    sent before configuration workflows.
    """
    return _encode_uart_command(0x5A, 0x04, msg_id, [0x01])


# Weekday bit mapping (same for light and doser devices)
_WEEKDAY_BITS = {
    "monday": 1 << 6,  # bit 6, value 64
    "tuesday": 1 << 5,  # bit 5, value 32
    "wednesday": 1 << 4,  # bit 4, value 16
    "thursday": 1 << 3,  # bit 3, value 8
    "friday": 1 << 2,  # bit 2, value 4
    "saturday": 1 << 1,  # bit 1, value 2
    "sunday": 1 << 0,  # bit 0, value 1
}


def encode_weekdays(weekdays: Sequence[str] | None) -> int:
    """Encode weekday selections into a 7-bit mask for device commands.

    Both light and doser devices use identical bit mapping for weekday scheduling.

    Args:
        weekdays: List of lowercase weekday names (e.g., ["monday", "tuesday"])
                  or None for everyday (all days)

    Returns:
        7-bit integer mask where each bit represents a weekday

    Examples:
        encode_weekdays(["monday", "wednesday"]) -> 84 (64 | 16)
        encode_weekdays(None) -> 127 (everyday)
    """
    if weekdays is None or not weekdays:
        return 127  # Default to everyday (all days)

    encoding = 0
    for day in weekdays:
        if day not in _WEEKDAY_BITS:
            raise ValueError(f"Invalid weekday: {day}")
        encoding |= _WEEKDAY_BITS[day]

    return encoding


def create_set_time_command(msg_id: tuple[int, int]) -> bytearray:
    """Build a set-time UART command for the device."""
    return _encode_uart_command(90, 9, msg_id, _encode_timestamp(datetime.datetime.now()))


# ============================================================================
# Light Commands
# ============================================================================


def create_manual_setting_command(
    msg_id: tuple[int, int], color: int, brightness_level: int
) -> bytearray:
    """Create a manual color/brightness setting command."""
    return _encode_uart_command(90, 7, msg_id, [color, brightness_level])


def create_add_auto_setting_command(
    msg_id: tuple[int, int],
    sunrise: datetime.time,
    sunset: datetime.time,
    brightness: tuple[int, ...],
    ramp_up_minutes: int,
    weekdays: int,
) -> bytearray:
    """Create a command to add an auto program to a light device.

    Supports variable numbers of brightness channels (RGB, RGBW, etc.).
    The brightness tuple length determines how many channels are configured.
    """
    # Validate brightness values
    if not brightness or len(brightness) > 4:
        raise ValueError(f"Brightness must contain 1-4 values, got {len(brightness)}")

    for i, val in enumerate(brightness):
        if not (0 <= val <= 100):
            raise ValueError(f"Brightness value {i} must be 0-100, got {val}")

    parameters = [
        sunrise.hour,
        sunrise.minute,
        sunset.hour,
        sunset.minute,
        ramp_up_minutes,
        weekdays,
        *brightness,
    ]

    # Pad with 255s to ensure consistent command length (7 brightness slots total)
    padding_needed = 7 - len(brightness)
    parameters.extend([255] * padding_needed)

    return _encode_uart_command(165, 25, msg_id, parameters)


def create_delete_auto_setting_command(
    msg_id: tuple[int, int],
    sunrise: datetime.time,
    sunset: datetime.time,
    ramp_up_minutes: int,
    weekdays: int,
) -> bytearray:
    """Create a delete-auto-setting command (encoded via add with 255s)."""
    return create_add_auto_setting_command(
        msg_id, sunrise, sunset, (255, 255, 255), ramp_up_minutes, weekdays
    )


def create_reset_auto_settings_command(msg_id: tuple[int, int]) -> bytearray:
    """Return a command to reset auto settings on the device."""
    return _encode_uart_command(90, 5, msg_id, [5, 255, 255])


def create_switch_to_auto_mode_command(msg_id: tuple[int, int]) -> bytearray:
    """Return a command switching the light to auto mode."""
    return _encode_uart_command(90, 5, msg_id, [18, 255, 255])


# ============================================================================
# Doser Commands
# ============================================================================


def create_prepare_command(msg_id: tuple[int, int], stage: int) -> bytearray:
    """Return the 0xA5 / mode 0x04 command used before configuration writes."""
    if stage not in (0x04, 0x05):
        raise ValueError("stage must be 0x04 or 0x05")
    return _encode_uart_command(0xA5, 0x04, msg_id, [stage])


def create_head_select_command(
    msg_id: tuple[int, int],
    head_index: int,
    *,
    flag1: int = 0x00,  # So this might be set catchup dosing
    flag2: int = 0x01,
) -> bytearray:
    """Select the dosing head that will be modified next (mode 0x20)."""
    if not 0 <= head_index <= 0x03:
        raise ValueError("head_index must be between 0 and 3")
    return _encode_uart_command(0xA5, 0x20, msg_id, [head_index, flag1, flag2])


def create_head_dose_command(
    msg_id: tuple[int, int],
    head_index: int,
    volume_tenths_ml: int,
    *,
    weekday_mask: int,
    schedule_mode: int = 0x01,
    repeat_flag: int = 0x01,
    reserved: int = 0x00,
) -> bytearray:
    """Create the mode 0x1B command that sets weekday mask and daily dose.

    Now supports volumes up to 6553.5mL (65535 tenths) using 2-byte encoding.
    Values <= 255 use legacy 1-byte format for backward compatibility.
    Values > 255 use new 2-byte format.
    """
    if not 0 <= volume_tenths_ml <= 0xFFFF:
        raise ValueError("volume_tenths_ml must fit in two bytes (0-65535)")
    if not 0 <= weekday_mask <= 0x7F:
        raise ValueError("weekday_mask must be a 7-bit value")

    # Use 2-byte encoding for volumes > 255, otherwise keep legacy 1-byte format
    if volume_tenths_ml <= 0xFF:
        # Legacy 1-byte format for backward compatibility
        return _encode_uart_command(
            0xA5,
            0x1B,
            msg_id,
            [
                head_index,
                weekday_mask,
                schedule_mode,
                repeat_flag,
                reserved,
                volume_tenths_ml,
            ],
        )
    else:
        # New 2-byte format for larger volumes
        # Split volume into high and low bytes (big-endian)
        volume_high = (volume_tenths_ml >> 8) & 0xFF
        volume_low = volume_tenths_ml & 0xFF
        return _encode_uart_command(
            0xA5,
            0x1C,  # New mode for 2-byte volume encoding
            msg_id,
            [
                head_index,
                weekday_mask,
                schedule_mode,
                repeat_flag,
                reserved,
                volume_high,
                volume_low,
            ],
        )


def create_head_schedule_command(
    msg_id: tuple[int, int],
    head_index: int,
    hour: int,
    minute: int,
    *,
    reserve1: int = 0x00,  # So this might be set catchup dosing
    reserve2: int = 0x00,
) -> bytearray:
    """Create the mode 0x15 command that sets the daily schedule time."""
    if not 0 <= hour <= 23:
        raise ValueError("hour must be 0-23")
    if not 0 <= minute <= 59:
        raise ValueError("minute must be 0-59")
    return _encode_uart_command(
        0xA5,
        0x15,
        msg_id,
        [head_index, reserve1, hour, minute, reserve2, 0x00],
    )
