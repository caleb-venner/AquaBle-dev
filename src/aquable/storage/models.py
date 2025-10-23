"""Status parsing models for device BLE notifications.

This module combines status parsing functionality for both doser and light devices,
providing structured representations of the raw BLE payload data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# ============================================================================
# Doser Status Models
# ============================================================================


MODE_NAMES = {
    0x00: "daily",
    0x01: "24h",
    0x02: "custom",
    0x03: "timer",
    0x04: "disabled",
}


@dataclass(slots=True)
class HeadSnapshot:
    """Decoded information for a single head in the status frame."""

    mode: int
    hour: int
    minute: int
    dosed_tenths_ml: int
    extra: bytes

    def mode_label(self) -> str:
        """Return a human friendly mode name if known."""
        return MODE_NAMES.get(self.mode, f"0x{self.mode:02X}")

    def dosed_ml(self) -> float:
        """Return the ml already dispensed today."""
        return self.dosed_tenths_ml / 10


@dataclass(slots=True)
class DoserStatus:
    """High level representation of a status notification."""

    message_id: tuple[int, int] | None
    response_mode: int | None
    weekday: int | None
    hour: int | None
    minute: int | None
    heads: list[HeadSnapshot]
    tail_targets: list[int]
    tail_flag: int | None
    tail_raw: bytes
    lifetime_totals_tenths_ml: list[int]
    raw_payload: bytes = b""

    def lifetime_totals_ml(self) -> list[float]:
        """Return lifetime totals in mL for all heads."""
        return [total / 10.0 for total in self.lifetime_totals_tenths_ml]


def _parse_status_payload(payload: bytes) -> DoserStatus:
    """Parse response mode 0xFE: Head data with schedule info and daily dosed amounts.

    The payload structure is:
    - Bytes 0-8: Standard header (0x5B, msg_id_hi, msg_id_lo, msg_id_hi,
                 msg_id_lo, 0xFE, weekday, hour, minute)
    - Bytes 09-17: Head 1 (9 bytes)
    - Bytes 18-26: Head 2 (9 bytes)
    - Bytes 27-35: Head 3 (9 bytes)
    - Bytes 36-44: Head 4 (9 bytes)
    - Last 5 bytes: Tail (contains daily set dose amounts for each head)
    """
    if not payload or len(payload) < 9 or payload[0] != 0x5B:
        raise ValueError("Invalid payload structure")

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


def _parse_lifetime_payload(payload: bytes) -> DoserStatus:
    """Parse response mode 0x1E: Lifetime dose totals (4 heads x 2 bytes each).

    For mode 0x1E, the structure is:
    - Bytes 0-5: Standard header (0x5B, msg_id_hi, msg_id_lo, msg_id_hi, msg_id_lo, 0x1E)
    - Bytes 6+: Lifetime totals (2 bytes per head)
    """
    if not payload or len(payload) < 6 or payload[0] != 0x5B:
        raise ValueError("Invalid payload structure")

    message_id = (payload[3], payload[4])
    response_mode = payload[5]

    # For 0x1E payloads, time fields are not present
    weekday = None
    hour = None
    minute = None

    lifetime_totals_tenths_ml: list[int] = []

    # Lifetime data starts at byte 6
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


def parse_doser_payload(payload: bytes) -> DoserStatus:
    """Parse a doser status notification from the pump.

    Dispatches to appropriate parser based on response mode:
    - 0xFE: Head data with schedule info and daily dosed amounts (includes time fields)
    - 0x1E: Lifetime dose totals (no time fields)
    """
    if not payload or len(payload) < 6:
        raise ValueError("payload too short")

    # Extract response_mode (byte 5) to determine which parser to use
    response_mode = payload[5]

    if response_mode == 0xFE:
        return _parse_status_payload(payload)
    elif response_mode == 0x1E:
        return _parse_lifetime_payload(payload)
    else:
        # Default behavior: treat as status payload if response_mode is unknown
        return _parse_status_payload(payload)


# ============================================================================
# Light Status Models
# ============================================================================


@dataclass(slots=True)
class LightKeyframe:
    """Single scheduled point (hour, minute, intensity)."""

    hour: int
    minute: int
    value: int

    def as_time(self) -> str:
        """Return the keyframe timestamp formatted as HH:MM."""
        return f"{self.hour:02d}:{self.minute:02d}"


@dataclass(slots=True)
class LightStatus:
    """Decoded view of a WRGB status notification."""

    message_id: Optional[Tuple[int, int]]
    response_mode: Optional[int]
    weekday: Optional[int]
    hour: Optional[int]
    minute: Optional[int]
    keyframes: list[LightKeyframe]
    time_markers: list[Tuple[int, int]]
    tail: bytes
    raw_payload: bytes


def _plausible_time(wd: int, hr: int, minute: int) -> bool:
    return 0 <= wd <= 7 and 0 <= hr <= 23 and 0 <= minute <= 59


def _minutes_distance(h1: int, m1: int, h2: int, m2: int) -> int:
    """Return minimal absolute distance in minutes between two HH:MM values.

    Computed modulo 24h so wrap-around at midnight is handled.
    """
    a = (h1 * 60 + m1) % (24 * 60)
    b = (h2 * 60 + m2) % (24 * 60)
    diff = abs(a - b)
    return min(diff, (24 * 60) - diff)


def _split_body(
    payload: bytes,
) -> Tuple[
    Optional[Tuple[int, int]],
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[int],
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


def parse_light_payload(payload: bytes) -> LightStatus:
    """Decode a WRGB status payload into keyframes and markers."""
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
    last_time: Optional[int] = None
    length = len(body_bytes)
    while i < length:
        remaining = length - i
        if remaining >= 4 and body_bytes[i] == 0x00 and body_bytes[i + 1] == 0x02:
            time_markers.append((body_bytes[i + 2], body_bytes[i + 3]))
            i += 4
            continue

        if remaining < 3:
            break

        hour = body_bytes[i]
        minute = body_bytes[i + 1]
        value = body_bytes[i + 2]
        triple = (hour, minute, value)

        if triple == (0, 0, 0):
            i += 3
            continue

        total_minutes = hour * 60 + minute
        if last_time is not None and total_minutes < last_time:
            break

        keyframes.append(LightKeyframe(hour=hour, minute=minute, value=value))
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


__all__ = [
    "DoserStatus",
    "HeadSnapshot",
    "LightKeyframe",
    "LightStatus",
    "MODE_NAMES",
    "parse_doser_payload",
    "parse_light_payload",
]
