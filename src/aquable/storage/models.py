"""Status parsing models for device BLE notifications.

This module combines status parsing functionality for both doser and light devices,
providing structured representations of the raw BLE payload data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# ===== Doser Status Models =====


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


def parse_doser_payload(payload: bytes) -> DoserStatus:
    """Parse the 0xFE status notification from the pump."""
    if not payload:
        raise ValueError("payload too short")

    message_id: tuple[int, int] | None = None
    response_mode: int | None = None
    weekday: int | None = None
    hour: int | None = None
    minute: int | None = None

    body = payload
    if payload[0] == 0x5B:
        if len(payload) < 9:
            raise ValueError("payload too short")
        message_id = (payload[3], payload[4])
        response_mode = payload[5]
        response_mode = payload[5]
        maybe_wd = payload[6]
        maybe_hr = payload[7]
        maybe_min = payload[8]
        if not _plausible_time(maybe_wd, maybe_hr, maybe_min):
            weekday = None
            hour = None
            minute = None
            body = payload[6:]
        else:
            weekday = maybe_wd
            hour = maybe_hr
            minute = maybe_min
            body = payload[9:]
            if len(body) >= 3 and weekday is not None and hour is not None and minute is not None:
                scan_limit = min(32, len(body) - 2)
                adjusted_start = None
                for off in range(0, scan_limit):
                    wd2, hr2, min2 = body[off], body[off + 1], body[off + 2]
                    if (
                        _plausible_time(wd2, hr2, min2)
                        and _minutes_distance(hour, minute, hr2, min2) <= 1
                    ):
                        adjusted_start = off + 3
                        break
                if adjusted_start is not None and adjusted_start > 0:
                    body = body[adjusted_start:]
    else:
        if len(payload) < 3:
            raise ValueError("payload too short")
        weekday, hour, minute = payload[0], payload[1], payload[2]
        body = payload[3:]

    tail_raw = b""
    if len(body) >= 5:
        tail_raw = body[-5:]
        head_bytes = body[:-5]
    else:
        head_bytes = body

    heads: list[HeadSnapshot] = []
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

    tail_targets: list[int] = []
    tail_flag: int | None = None
    if tail_raw:
        tail_targets = list(tail_raw[:4])
        if len(tail_raw) > 4:
            tail_flag = tail_raw[4]

    lifetime_totals_tenths_ml: list[int] = []
    if weekday is None and hour is None and minute is None and len(body) >= 8:
        usable_bytes = (len(body) // 2) * 2
        num_heads = min(4, usable_bytes // 2)
        for i in range(num_heads):
            high_byte = body[i * 2]
            low_byte = body[i * 2 + 1]
            total_tenths_ml = (high_byte << 8) | low_byte
            lifetime_totals_tenths_ml.append(total_tenths_ml)

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
        lifetime_totals_tenths_ml=lifetime_totals_tenths_ml,
        raw_payload=payload,
    )


# ===== Light Status Models =====


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
