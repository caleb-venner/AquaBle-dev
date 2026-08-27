"""Payload parsers for BLE device notifications.

Decodes raw byte payloads into strongly typed domain models.
"""

from ..domain.doser.status import DoserStatus, HeadSnapshot
from ..domain.light.status import LightKeyframe, LightSchedule, LightStatus

# ─── DOSER ────────────────────────────────────────────────────────────────────


def _parse_status_payload(payload: bytes) -> DoserStatus | None:
    """Parse response mode 0xFE: Head data with schedule info and daily dosed amounts."""
    if not payload or len(payload) < 9 or payload[0] != 0x5B:
        return None

    message_id = (payload[3], payload[4])
    response_mode = payload[5]
    weekday = payload[6]
    hour = payload[7]
    minute = payload[8]

    body = payload[9:]
    heads: list[HeadSnapshot] = []
    tail_targets: list[int] = []
    tail_flag: int | None = None
    tail_raw = b""

    # Extract tail from last 5 bytes
    if len(body) >= 5:
        tail_raw = body[-5:]
        head_bytes = body[:-5]
    else:
        head_bytes = body

    # Parse head blocks (9 bytes each, up to 4 heads)
    for idx in range(0, min(len(head_bytes), 9 * 4), 9):
        end_index = idx + 9
        chunk = head_bytes[idx:end_index]
        if len(chunk) < 9:
            break
        heads.append(
            HeadSnapshot(
                mode=chunk[0],
                hour=chunk[1],
                minute=chunk[2],
                extra=chunk[3:7],
                dosed_tenths_ml=(chunk[7] << 8) | chunk[8],
            )
        )

    if tail_raw:
        tail_targets = list(tail_raw[:4])
        if len(tail_raw) > 4:
            tail_flag = tail_raw[4]

    return DoserStatus(
        message_id=message_id,
        response_mode=response_mode,
        weekday=weekday,
        hour=hour,
        minute=minute,
        heads=heads,
        tail_targets=tail_targets,
        tail_flag=tail_flag,
        tail_raw=tail_raw,
        lifetime_totals_tenths_ml=[],
        raw_payload=payload,
    )


def _parse_lifetime_payload(payload: bytes) -> DoserStatus | None:
    """Parse response mode 0x1E: Lifetime dose totals (4 heads x 2 bytes each)."""
    if not payload or len(payload) < 6 or payload[0] != 0x5B:
        return None

    message_id = (payload[3], payload[4])
    response_mode = payload[5]

    weekday = None
    hour = None
    minute = None

    lifetime_totals_tenths_ml: list[int] = []
    lifetime_data = payload[6:]

    num_heads = min(4, len(lifetime_data) // 2)
    for i in range(num_heads):
        high_byte = lifetime_data[i * 2]
        low_byte = lifetime_data[i * 2 + 1]
        total_tenths_ml = (high_byte << 8) | low_byte
        lifetime_totals_tenths_ml.append(total_tenths_ml)

    return DoserStatus(
        message_id=message_id,
        response_mode=response_mode,
        weekday=weekday,
        hour=hour,
        minute=minute,
        heads=[],
        tail_targets=[],
        tail_flag=None,
        tail_raw=b"",
        lifetime_totals_tenths_ml=lifetime_totals_tenths_ml,
        raw_payload=payload,
    )


def parse_doser_payload(payload: bytes) -> DoserStatus | None:
    """Parse a doser status notification from the pump.

    Dispatches to the appropriate sub-parser based on response mode:
    - 0xFE: current schedule data and daily dosed amounts.
    - 0x1E: lifetime dose totals.
    """
    if not payload or len(payload) < 6 or payload[0] != 0x5B:
        return None

    response_mode = payload[5]
    if response_mode not in (0xFE, 0x1E):
        return None

    try:
        if response_mode == 0xFE:
            return _parse_status_payload(payload)
        return _parse_lifetime_payload(payload)
    except Exception:
        return None


# ─── LIGHT ────────────────────────────────────────────────────────────────────

# Each auto-schedule stored on the device occupies 13 bytes in the status body,
# mirroring the parameter list sent by create_add_auto_setting_command:
#   [sunrise_h, sunrise_m, sunset_h, sunset_m, ramp_up, weekdays,
#    ch0, ch1, ch2, ch3, 0xFF, 0xFF, 0xFF]
# Trailing 0xFF bytes are padding to fill the fixed 7-channel-slot layout.
_SCHEDULE_BLOCK_SIZE = 13

# Maximum number of schedules a device can store (protocol limit).
_MAX_SCHEDULES = 24

# Maximum number of brightness channels per schedule.
_MAX_CHANNELS = 4


def _parse_schedule_blocks(body: bytes, num_channels: int) -> list[LightSchedule]:
    """Parse the body of a light status payload into LightSchedule objects.

    Each block is _SCHEDULE_BLOCK_SIZE (13) bytes:
      offset 0: sunrise_hour
      offset 1: sunrise_minute
      offset 2: sunset_hour
      offset 3: sunset_minute
      offset 4: ramp_up_minutes
      offset 5: weekday_mask (7-bit bitmask)
      offset 6..(6+num_channels-1): brightness per channel (0-100)
      remaining: 0xFF padding up to offset 12
    """
    schedules: list[LightSchedule] = []
    i = 0
    while i + _SCHEDULE_BLOCK_SIZE <= len(body) and len(schedules) < _MAX_SCHEDULES:
        block = body[i : i + _SCHEDULE_BLOCK_SIZE]

        sunrise_h = block[0]
        sunrise_m = block[1]
        sunset_h = block[2]
        sunset_m = block[3]
        ramp_up = block[4]
        weekday_mask = block[5]
        brightness_bytes = block[6 : 6 + _MAX_CHANNELS]  # always read 4 slots

        # A block of all-0xFF or all-0x00 is an empty/unpopulated schedule slot — skip it.
        if (
            all(b == 0xFF for b in block)
            or all(b == 0x00 for b in block)
            or (sunrise_h == 0 and sunrise_m == 0 and sunset_h == 0 and sunset_m == 0)
        ):
            i += _SCHEDULE_BLOCK_SIZE
            continue

        # Validate: hour/minute values must be in range.
        if sunrise_h > 23 or sunrise_m > 59 or sunset_h > 23 or sunset_m > 59:
            # Not a valid schedule block — body layout may not match expectations.
            break

        # Extract only the valid channel slots (non-padding).
        channels = [brightness_bytes[c] for c in range(num_channels)]

        schedules.append(
            LightSchedule(
                sunrise_hour=sunrise_h,
                sunrise_minute=sunrise_m,
                sunset_hour=sunset_h,
                sunset_minute=sunset_m,
                ramp_up_minutes=ramp_up,
                weekday_mask=weekday_mask,
                channel_brightness=channels,
            )
        )
        i += _SCHEDULE_BLOCK_SIZE

    return schedules


def _parse_legacy_keyframes(body: bytes) -> tuple[list[LightKeyframe], list[tuple[int, int]]]:
    """Fall back to the original keyframe-stream parser for unknown device formats.

    Decodes the body as a mixed stream of:
    - 4-byte time markers (0x00 0x02 HH MM)
    - 3-byte keyframes (HH MM VALUE), monotonically increasing in time
    """
    keyframes: list[LightKeyframe] = []
    time_markers: list[tuple[int, int]] = []
    i = 0
    last_time: int | None = None
    length = len(body)

    while i < length:
        remaining = length - i
        if remaining >= 4 and body[i] == 0x00 and body[i + 1] == 0x02:
            time_markers.append((body[i + 2], body[i + 3]))
            i += 4
            continue

        if remaining < 3:
            break

        hour_kf = body[i]
        minute_kf = body[i + 1]
        value = body[i + 2]

        if (hour_kf, minute_kf, value) == (0, 0, 0):
            i += 3
            continue

        total_minutes = hour_kf * 60 + minute_kf
        if last_time is not None and total_minutes < last_time:
            break

        keyframes.append(LightKeyframe(hour=hour_kf, minute=minute_kf, value=value))
        last_time = total_minutes
        i += 3

    return keyframes, time_markers


def parse_light_payload(
    payload: bytes,
    num_channels: int = 0,
) -> LightStatus | None:
    """Decode a light status payload into schedules and raw keyframes.

    Args:
        payload: Raw BLE notification bytes.
        num_channels: Number of brightness channels for this device model
            (from DEVICE_REGISTRY). When > 0, the body is parsed as schedule
            blocks and LightStatus.schedules is populated. When 0, falls back
            to the legacy keyframe-stream parser.

    Returns:
        A LightStatus, or None if the payload is not a valid 0xFE status response.
    """
    if not payload or len(payload) < 6 or payload[0] != 0x5B:
        return None

    # Reject handshake ack and anything other than the status response mode.
    if payload[5] == 0x0A:
        return None
    if payload[5] != 0xFE:
        return None

    try:
        message_id = (payload[3], payload[4])
        response_mode = payload[5]
        weekday = payload[6] if len(payload) > 6 else None
        hour = payload[7] if len(payload) > 7 else None
        minute = payload[8] if len(payload) > 8 else None

        body = payload[9:] if len(payload) > 9 else b""

        # Strip the 5-byte tail.
        tail = body[-5:] if len(body) >= 5 else b""
        body_bytes = body[:-5] if len(body) >= 5 else body

        schedules: list[LightSchedule] = []
        keyframes: list[LightKeyframe] = []
        time_markers: list[tuple[int, int]] = []

        if num_channels > 0 and len(body_bytes) >= _SCHEDULE_BLOCK_SIZE:
            # Primary path: parse structured schedule blocks.
            schedules = _parse_schedule_blocks(body_bytes, num_channels)
        else:
            # Legacy fallback: variable-length keyframe stream.
            # Apply the pattern-strip heuristic used by the old parser.
            if (
                weekday is not None
                and hour is not None
                and minute is not None
                and len(body_bytes) >= 3
            ):
                pattern = bytes((weekday, hour, minute))
                idx = body_bytes.find(pattern)
                if idx != -1 and idx <= 16:
                    body_bytes = body_bytes[idx + 3 :]
            keyframes, time_markers = _parse_legacy_keyframes(body_bytes)

        return LightStatus(
            message_id=message_id,
            response_mode=response_mode,
            weekday=weekday,
            hour=hour,
            minute=minute,
            schedules=schedules,
            keyframes=keyframes,
            time_markers=time_markers,
            tail=tail,
            raw_payload=payload,
        )
    except Exception:
        # Return a minimal status so the coordinator does not drop the device.
        return LightStatus(
            message_id=None,
            response_mode=None,
            weekday=None,
            hour=None,
            minute=None,
            schedules=[],
            keyframes=[],
            time_markers=[],
            tail=b"",
            raw_payload=payload,
        )
