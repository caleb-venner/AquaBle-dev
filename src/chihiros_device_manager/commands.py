"""Module defining commands generation functions."""

import datetime


def next_message_id(
    current_msg_id: tuple[int, int] = (0, 0)
) -> tuple[int, int]:
    """Generate bluetooth message id."""
    msg_id_higher_byte, msg_id_lower_byte = current_msg_id
    if msg_id_lower_byte == 255:
        if msg_id_higher_byte == 255:
            # start counting from the beginning
            return (0, 1)
        if msg_id_higher_byte == 89:
            # higher byte should never be 90
            return (msg_id_higher_byte + 2, msg_id_lower_byte)
        return (msg_id_higher_byte + 1, 0)

    else:
        if msg_id_lower_byte == 89:
            # lower byte should never be 90
            return (0, msg_id_lower_byte + 2)
        return (0, msg_id_lower_byte + 1)


def _calculate_checksum(input_bytes: bytes) -> int:
    """Calculate message checksum."""
    assert len(input_bytes) >= 7  # commands are always at least 7 bytes long
    checksum = input_bytes[1]
    for input_byte in input_bytes[2:]:
        checksum = checksum ^ input_byte
    return checksum


def _create_command_encoding(
    cmd_id: int, cmd_mode: int, msg_id: tuple[int, int], parameters: list[int]
) -> bytearray:
    """Encode command."""
    # make sure that no parameter is 90
    sanitized_params: list[int] = list(
        map(lambda x: x if x != 90 else 89, parameters)
    )

    command = bytearray(
        [cmd_id, 1, len(parameters) + 5, msg_id[0], msg_id[1], cmd_mode]
        + sanitized_params
    )

    verification_byte = _calculate_checksum(command)
    if verification_byte == 90:
        # make sure that verification byte is not 90
        new_msg_id = (msg_id[0], msg_id[1] + 1)
        return _create_command_encoding(
            cmd_id, cmd_mode, new_msg_id, sanitized_params
        )

    return command + bytes([verification_byte])


def _encode_timestamp(ts: datetime.datetime) -> list[int]:
    """Encode timestamp."""
    # note: day is weekday e.g. 3 for wednesday
    return [
        ts.year - 2000,
        ts.month,
        ts.isoweekday(),
        ts.hour,
        ts.minute,
        ts.second,
    ]


def create_set_time_command(msg_id: tuple[int, int]) -> bytearray:
    """Create current time command."""
    return _create_command_encoding(
        90, 9, msg_id, _encode_timestamp(datetime.datetime.now())
    )


def create_manual_setting_command(
    msg_id: tuple[int, int], color: int, brightness_level: int
) -> bytearray:
    """Set brightness for a color channel.

    Args:
        msg_id: Tuple identifying the command sequence.
        color: Channel index (0=red, 1=green, 2=blue; 0=white on
            non-RGB models).
        brightness_level: Target brightness between 0 and 100.
    """
    return _create_command_encoding(90, 7, msg_id, [color, brightness_level])


def create_add_auto_setting_command(
    msg_id: tuple[int, int],
    sunrise: datetime.time,
    sunset: datetime.time,
    brightness: tuple[int, int, int],
    ramp_up_minutes: int,
    weekdays: int,
) -> bytearray:
    """Add a timed automation entry.

    Args:
        msg_id: Tuple identifying the command sequence.
        sunrise: Time when the program starts.
        sunset: Time when the program ends.
        brightness: RGB brightness tuple. Use (white, 255, 255)
            on non-RGB models.
        ramp_up_minutes: Fade-in duration in minutes.
        weekdays: Bit mask selecting active weekdays.
    """
    parameters = [
        sunrise.hour,
        sunrise.minute,
        sunset.hour,
        sunset.minute,
        ramp_up_minutes,
        weekdays,
        *brightness,
        255,
        255,
        255,
        255,
        255,
    ]

    return _create_command_encoding(165, 25, msg_id, parameters)


def create_delete_auto_setting_command(
    msg_id: tuple[int, int],
    sunrise: datetime.time,
    sunset: datetime.time,
    ramp_up_minutes: int,
    weekdays: int,
) -> bytearray:
    """Create delete auto setting command."""
    return create_add_auto_setting_command(
        msg_id, sunrise, sunset, (255, 255, 255), ramp_up_minutes, weekdays
    )


def create_reset_auto_settings_command(msg_id: tuple[int, int]) -> bytearray:
    """Create reset auto setting command."""
    return _create_command_encoding(90, 5, msg_id, [5, 255, 255])


def create_switch_to_auto_mode_command(msg_id: tuple[int, int]) -> bytearray:
    """Create switch auto setting command."""
    return _create_command_encoding(90, 5, msg_id, [18, 255, 255])


def create_status_request_command(msg_id: tuple[int, int]) -> bytearray:
    """Request a status notification from the device."""
    return _create_command_encoding(0x5A, 0x04, msg_id, [0x01])
