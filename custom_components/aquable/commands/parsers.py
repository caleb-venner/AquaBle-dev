"""Payload parsers for BLE device notifications.

Decodes raw byte payloads into strongly typed domain models.
"""

from ..domain.doser.status import DoserStatus, HeadSnapshot
from ..domain.light.status import LightKeyframe, LightStatus


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

    Includes safety checks previously housed in the Doser class.
    Dispatches to appropriate parser based on response mode.
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


def _split_body(
    payload: bytes,
) -> tuple[
    tuple[int, int] | None,
    int | None,
    int | None,
    int | None,
    int | None,
    bytes,
]:
    """Return header fields and body bytes."""
    message_id = response_mode = weekday = hour = minute = None
    body = payload
    if payload and payload[0] == 0x5B and len(payload) >= 9:
        message_id = (payload[3], payload[4])
        response_mode = payload[5]
        weekday = payload[6]
        hour = payload[7]
        minute = payload[8]
        body = payload[9:]
    return message_id, response_mode, weekday, hour, minute, body


def parse_light_payload(payload: bytes) -> LightStatus | None:
    """Decode a WRGB status payload into keyframes and markers.

    Includes safety checks previously housed in the LightDevice class.
    """
    if not payload or len(payload) < 6 or payload[0] != 0x5B:
        return None

    # Handle handshake ack
    if payload[5] == 0x0A:
        return None

    if payload[5] != 0xFE:
        return None

    try:
        (
            message_id,
            response_mode,
            weekday,
            hour,
            minute,
            body,
        ) = _split_body(payload)

        tail = body[-5:] if len(body) >= 5 else b""
        body_bytes = body[:-5] if len(body) >= 5 else body

        if weekday is not None and hour is not None and minute is not None and len(body_bytes) >= 3:
            pattern = bytes((weekday, hour, minute))
            idx = body_bytes.find(pattern)
            if idx != -1 and idx <= 16:
                body_bytes = body_bytes[idx + 3 :]

        keyframes: list[LightKeyframe] = []
        time_markers: list[tuple[int, int]] = []

        i = 0
        last_time: int | None = None
        length = len(body_bytes)
        while i < length:
            remaining = length - i
            if remaining >= 4 and body_bytes[i] == 0x00 and body_bytes[i + 1] == 0x02:
                time_markers.append((body_bytes[i + 2], body_bytes[i + 3]))
                i += 4
                continue

            if remaining < 3:
                break

            hour_kf = body_bytes[i]
            minute_kf = body_bytes[i + 1]
            value = body_bytes[i + 2]
            triple = (hour_kf, minute_kf, value)

            if triple == (0, 0, 0):
                i += 3
                continue

            total_minutes = hour_kf * 60 + minute_kf
            if last_time is not None and total_minutes < last_time:
                break

            keyframes.append(LightKeyframe(hour=hour_kf, minute=minute_kf, value=value))
            last_time = total_minutes
            i += 3

        return LightStatus(
            message_id=message_id,
            response_mode=response_mode,
            weekday=weekday,
            hour=hour,
            minute=minute,
            keyframes=keyframes,
            time_markers=time_markers,
            tail=tail,
            raw_payload=payload,
        )
    except Exception:
        # Fallback to minimal status so raw payload is available for debugging
        return LightStatus(
            message_id=None,
            response_mode=None,
            weekday=None,
            hour=None,
            minute=None,
            keyframes=[],
            time_markers=[],
            tail=b"",
            raw_payload=payload,
        )
