"""High-level Orchestrator.

Glues together:
- `commands.generators` (what bytes to send)
- `core.ble_client` (how to send them)
- `commands.parsers` (how to interpret the response)
- `domain.storage` (where to save the result)
"""

import dataclasses
import logging
from collections.abc import Sequence
from pathlib import Path

from ..commands import generators, parsers
from ..domain import storage
from ..domain.doser.status import DoserStatus
from ..domain.light.status import LightStatus
from . import ble_client

logger = logging.getLogger(__name__)

async def request_status_and_update(
    config_dir: Path, 
    device_id: str, 
    device_type: str,
    msg_id: tuple[int, int]
) -> tuple[tuple[int, int], DoserStatus | LightStatus | None]:
    """Request status from a device, save it to storage, and return the parsed status."""
    
    new_msg_id, payloads = generators.generate_handshake_sequence(msg_id)
    
    packets = await ble_client.execute_ble_commands(
        address=device_id,
        payloads=payloads,
        wait_for_status=True,
    )
    
    final_status = None
    all_raw_payloads = [packet.hex() for packet in packets]
    
    if device_type == "doser":
        for packet in packets:
            parsed = parsers.parse_doser_payload(packet)
            if parsed:
                if final_status is None:
                    final_status = parsed
                else:
                    final_status.update_from(parsed)
                    
    elif device_type == "light":
        for packet in packets:
            parsed = parsers.parse_light_payload(packet)
            if parsed:
                # Lights don't have multiple disjoint packets like dosers, first valid is fine
                final_status = parsed
                break

    if final_status:
        # Convert Dataclass to dictionary for storage
        status_dict = dataclasses.asdict(final_status)
        status_dict.pop("raw_payload", None)
        
        # Filter out the static handshake payload (0x0A)
        filtered_raw = []
        for p in all_raw_payloads:
            try:
                b = bytes.fromhex(p)
                if len(b) > 5 and b[5] != 0x0A:
                    filtered_raw.append(p)
            except Exception:
                filtered_raw.append(p)
                
        status_dict["raw_payloads"] = filtered_raw
        
        def _convert_bytes(obj):
            if isinstance(obj, (bytes, bytearray)):
                return obj.hex()
            elif isinstance(obj, dict):
                return {k: _convert_bytes(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_convert_bytes(v) for v in obj]
            return obj
            
        status_dict = _convert_bytes(status_dict)
                    
        storage.update_device_status(config_dir, device_id, device_type, status_dict)
        logger.info(f"[{device_id}] Status updated and persisted.")
    else:
        logger.warning(f"[{device_id}] No valid status parsed from {len(packets)} packets.")
        
    return new_msg_id, final_status


async def set_doser_schedule(
    config_dir: Path,
    device_id: str,
    msg_id: tuple[int, int],
    head_index: int,
    volume_tenths_ml: int,
    hour: int,
    minute: int,
    weekdays: Sequence[str] | None = None,
) -> tuple[tuple[int, int], DoserStatus | None]:
    """Configure a doser schedule and request the new status."""
    
    new_msg_id, schedule_payloads = generators.generate_doser_set_daily_dose_sequence(
        start_msg_id=msg_id,
        head_index=head_index,
        volume_tenths_ml=volume_tenths_ml,
        hour=hour,
        minute=minute,
        weekdays=weekdays,
    )
    
    # After scheduling, we want to retrieve the status immediately
    new_msg_id, handshake_payloads = generators.generate_handshake_sequence(new_msg_id)
    
    # Combine the commands
    all_payloads = schedule_payloads + handshake_payloads
    
    packets = await ble_client.execute_ble_commands(
        address=device_id,
        payloads=all_payloads,
        wait_for_status=True,
    )
    
    # Parse the incoming status
    final_status = None
    all_raw_payloads = []
    for packet in packets:
        all_raw_payloads.append(packet.hex())
        parsed = parsers.parse_doser_payload(packet)
        if parsed:
            if final_status is None:
                final_status = parsed
            else:
                final_status.update_from(parsed)
                
    if final_status:
        status_dict = dataclasses.asdict(final_status)
        status_dict.pop("raw_payload", None)
        status_dict["raw_payloads"] = all_raw_payloads
        status_dict["tail_raw"] = status_dict["tail_raw"].hex()
        for head in status_dict.get("heads", []):
            if "extra" in head:
                head["extra"] = head["extra"].hex()
        storage.update_device_status(config_dir, device_id, "doser", status_dict)

    return new_msg_id, final_status


async def set_light_brightness(
    config_dir: Path,
    device_id: str,
    msg_id: tuple[int, int],
    colors: dict[int, int]
) -> tuple[tuple[int, int], LightStatus | None]:
    """Set manual light brightness and request the new status."""
    
    new_msg_id, brightness_payloads = generators.generate_light_set_brightness_sequence(
        start_msg_id=msg_id,
        colors=colors,
    )
    
    new_msg_id, handshake_payloads = generators.generate_handshake_sequence(new_msg_id)
    all_payloads = brightness_payloads + handshake_payloads
    
    packets = await ble_client.execute_ble_commands(
        address=device_id,
        payloads=all_payloads,
        wait_for_status=True,
    )
    
    final_status = None
    all_raw_payloads = []
    for packet in packets:
        all_raw_payloads.append(packet.hex())
        parsed = parsers.parse_light_payload(packet)
        if parsed:
            final_status = parsed
            break
            
    if final_status:
        status_dict = dataclasses.asdict(final_status)
        status_dict.pop("raw_payload", None)
        status_dict["raw_payloads"] = all_raw_payloads
        status_dict["tail"] = status_dict["tail"].hex()
        storage.update_device_status(config_dir, device_id, "light", status_dict)

    return new_msg_id, final_status
