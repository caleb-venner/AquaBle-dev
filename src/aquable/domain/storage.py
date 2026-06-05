"""Pure functional storage layer for device configurations.

Provides stateless file I/O operations for saving and loading device state
from JSON files. Replaces the old Object-Oriented BaseDeviceStorage hierarchy.
"""

import dataclasses
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from ..core.system_time import now_iso

logger = logging.getLogger(__name__)

TDevice = TypeVar("TDevice")

def _get_device_file_path(storage_dir: Path, device_id: str) -> Path:
    """Get the file path for a specific device, supporting legacy colon-based names."""
    safe_id = device_id.replace(":", "_")
    escaped_path = storage_dir / f"{safe_id}.json"

    if escaped_path.exists():
        return escaped_path

    colon_path = storage_dir / f"{device_id}.json"
    if colon_path.exists():
        return colon_path

    return escaped_path

def list_device_files(storage_dir: Path) -> list[Path]:
    """List all device JSON files in the storage directory."""
    if not storage_dir.exists():
        return []
    return [p for p in storage_dir.glob("*.json") if p.name != "proxy.json"]

def load_device(
    storage_dir: Path, 
    device_id: str, 
    expected_type: str, 
    parser_fn: Callable[[dict], Any]
) -> Any | None:
    """Read a device from its JSON file."""
    device_file = _get_device_file_path(storage_dir, device_id)
    if not device_file.exists():
        return None

    try:
        raw = device_file.read_text(encoding="utf-8").strip()
        if not raw:
            return None

        data = json.loads(raw)
        
        if data.get("device_type") != expected_type:
            logger.debug(f"Device file {device_file} has wrong type: expected {expected_type}")
            return None

        device_data = data.get("device_data")
        if device_data is None:
            return None

        return parser_fn(device_data)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error(f"Could not parse device file {device_file}: {exc}")
        return None

def save_device(storage_dir: Path, device: Any, device_type: str) -> None:
    """Write a device to its JSON file atomically."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    device_file = _get_device_file_path(storage_dir, device.id)
    
    # Read existing file to preserve last_status
    existing_last_status = None
    if device_file.exists():
        try:
            existing_data = json.loads(device_file.read_text(encoding="utf-8"))
            existing_last_status = existing_data.get("last_status")
        except (json.JSONDecodeError, OSError):
            pass

    data = {
        "device_type": device_type,
        "device_id": device.id,
        "last_updated": now_iso(),
        "device_data": dataclasses.asdict(device),
    }

    if existing_last_status:
        data["last_status"] = existing_last_status

    tmp_file = device_file.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp_file.replace(device_file)

def update_device_status(storage_dir: Path, device_id: str, device_type: str, status: dict[str, Any]) -> None:
    """Update only the status portion of a device file."""
    device_file = _get_device_file_path(storage_dir, device_id)

    existing_data = {}
    if device_file.exists():
        try:
            existing_data = json.loads(device_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    data = existing_data or {
        "device_type": device_type,
        "device_id": device_id,
        "device_data": {"id": device_id, "configurations": []},
    }
    
    if "device_data" not in data:
        data["device_data"] = {"id": device_id, "configurations": []}

    if "device_name" in status:
        data["device_name"] = status.pop("device_name")

    data["last_status"] = status
    data["last_updated"] = now_iso()
    data["device_type"] = device_type
    data["device_id"] = device_id

    storage_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = device_file.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp_file.replace(device_file)

def get_device_status(storage_dir: Path, device_id: str) -> dict[str, Any] | None:
    """Get the last known status for a device."""
    device_file = _get_device_file_path(storage_dir, device_id)
    if not device_file.exists():
        return None

    try:
        data = json.loads(device_file.read_text(encoding="utf-8"))
        return data.get("last_status")
    except (json.JSONDecodeError, OSError):
        return None

def delete_device(storage_dir: Path, device_id: str) -> bool:
    """Delete a device file."""
    device_file = _get_device_file_path(storage_dir, device_id)
    if device_file.exists():
        try:
            device_file.unlink()
            return True
        except OSError as exc:
            logger.error(f"Could not delete device file {device_file}: {exc}")
            return False
    return False

def get_device_with_status(storage_dir: Path, device_id: str, expected_type: str, parser_fn: Callable[[dict], Any]) -> dict | None:
    """Load device config and combine it with last_status for frontend API."""
    device_file = _get_device_file_path(storage_dir, device_id)
    if not device_file.exists():
        return None

    try:
        raw = device_file.read_text(encoding="utf-8").strip()
        if not raw:
            return None

        data = json.loads(raw)
        
        if data.get("device_type") != expected_type:
            return None

        device_data = data.get("device_data")
        if device_data is None:
            return None

        # Validate by parsing and dumping back to dict to ensure correct schema
        parsed_device = parser_fn(device_data)
        response = dataclasses.asdict(parsed_device)
        
        if "last_status" in data:
            response["last_status"] = data["last_status"]

        return response
    except (json.JSONDecodeError, ValueError):
        return None
