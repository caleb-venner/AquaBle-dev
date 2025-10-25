"""Serialization helpers for API responses.

These convert internal dataclasses into JSON-safe primitives.
"""

from __future__ import annotations

from typing import Any, Dict

from ..storage.models import DoserStatus, LightStatus


def serialize_doser_status(status: DoserStatus) -> Dict[str, Any]:
    """Convert a dosing status dataclass into JSON-safe primitives.

    Follows the actual BLE payload structure for clarity:
    - response_mode: First 3 bytes of payload in hex (e.g., "5B0630")
    - message_id: [high, low]
    - weekday: Day of week (0-6)
    - hour: Hour (0-23)
    - minute: Minute (0-59)
    - heads: List of head data
    - tail_targets: Target values for each head
    - tail_raw: Raw tail bytes as hex string
    - tail_flag: Final byte of tail

    Notes:
    - The top-level CachedStatus already carries the raw_payload as hex.
      To avoid duplication, we omit raw_payload from the nested parsed dict.
    """
    # Build response_mode field from first 3 bytes of payload
    response_mode_hex = ""
    if status.raw_payload and len(status.raw_payload) >= 3:
        response_mode_hex = status.raw_payload[:3].hex().upper()

    data = {
        "response_mode": response_mode_hex,
        "message_id": list(status.message_id) if status.message_id else None,
        "weekday": status.weekday,
        "hour": status.hour,
        "minute": status.minute,
        "heads": [],
        "tail_targets": status.tail_targets,
        "tail_raw": status.tail_raw.hex(),
        "tail_flag": status.tail_flag,
    }

    # Enrich per-head data with hex-encoded extras and human-friendly mode name
    for head_obj in status.heads:
        head_dict = {
            "mode": head_obj.mode,
            "mode_label": head_obj.mode_label(),
            "hour": head_obj.hour,
            "minute": head_obj.minute,
            "dosed_tenths_ml": head_obj.dosed_tenths_ml,
            "extra": head_obj.extra.hex(),
        }
        data["heads"].append(head_dict)

    # Add lifetime totals if present
    if status.lifetime_totals_tenths_ml:
        data["lifetime_totals_tenths_ml"] = status.lifetime_totals_tenths_ml

    return data


def serialize_light_status(status: LightStatus) -> Dict[str, Any]:
    """Convert a light status snapshot to a serializable dictionary.

    Follows the actual BLE payload structure for clarity:
    - response_mode: First 3 bytes of payload in hex (e.g., "5B0630")
    - message_id: [high, low]
    - weekday: Day of week (0-7)
    - hour: Hour (0-23)
    - minute: Minute (0-59)
    - keyframes: List of brightness points
    - time_markers: Time markers
    - tail: Raw tail bytes as hex string

    Notes:
    - Omit raw_payload from parsed to prevent duplication; it is available at
      the CachedStatus top level.
    """
    # Build response_mode field from first 3 bytes of raw payload
    response_mode_hex = ""
    if hasattr(status, "raw_payload") and status.raw_payload and len(status.raw_payload) >= 3:
        response_mode_hex = status.raw_payload[:3].hex().upper()

    # Include both the raw value (0..255) and a pre-computed percentage so
    # the frontend doesn't need to perform the conversion.
    data = {
        "response_mode": response_mode_hex,
        "message_id": list(status.message_id) if status.message_id else None,
        "weekday": status.weekday,
        "hour": status.hour,
        "minute": status.minute,
        "keyframes": [
            {
                "hour": frame.hour,
                "minute": frame.minute,
                "value": frame.value,
                "percent": (
                    int(round(frame.value))
                    if frame.value is not None and frame.value <= 100
                    else int(round((frame.value / 255) * 100))
                ),
            }
            for frame in status.keyframes
        ],
        "time_markers": status.time_markers,
        "tail": status.tail.hex(),
    }
    return data


def cached_status_to_dict(service, status) -> Dict[str, Any]:
    """Transform a cached status into the API response structure.

    Returns ONLY runtime connection state: address, device_type, connected, updated_at.

    Device naming, configuration, parsed status, and raw payloads are available
    via the /api/devices/{address}/configurations endpoint and are persisted
    in the device JSON files.

    This ultra-minimal payload keeps the status endpoint extremely lightweight
    and focused purely on connection state polling.
    """
    connected = service.current_device_address(status.device_type) == status.address

    return {
        "address": status.address,
        "device_type": status.device_type,
        "connected": connected,
        "updated_at": status.updated_at,
    }
