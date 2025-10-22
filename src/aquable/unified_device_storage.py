"""Unified device storage combining status cache and configuration in single files.

This module replaces the dual-storage system (state.json + devices/*.json) with
a single per-device file structure that includes:
- Device metadata (name, auto-reconnect settings)
- Last known status (BLE payload, parsed data, timestamp)
- User configurations (schedules, profiles, settings)

Each device gets one file: ~/.aquable/devices/{address}.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict

from .doser_storage import DoserDevice, DoserMetadata
from .light_storage import LightDevice, LightMetadata
from .time_utils import now_iso

logger = logging.getLogger(__name__)


class DeviceStatus(BaseModel):
    """Last known device status from BLE communication."""

    model_name: str | None = None
    raw_payload: str | None = None
    parsed: Dict[str, Any] | None = None
    updated_at: float
    channels: Dict[str, int] | None = None  # Only for light devices (color name -> channel index)

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class UnifiedDoserDevice(BaseModel):
    """Unified storage for a doser device."""

    device_type: Literal["doser"] = "doser"
    device_id: str
    last_updated: str  # ISO timestamp of file modification

    # Metadata (names, auto-reconnect, etc.)
    metadata: DoserMetadata | None = None

    # Last known status from BLE
    last_status: DeviceStatus | None = None

    # Configuration data (schedules, etc.) - None for newly discovered devices
    device_data: DoserDevice | None = None

    model_config = ConfigDict(extra="forbid")


class UnifiedLightDevice(BaseModel):
    """Unified storage for a light device."""

    device_type: Literal["light"] = "light"
    device_id: str
    last_updated: str  # ISO timestamp of file modification

    # Metadata (names, auto-reconnect, etc.)
    metadata: LightMetadata | None = None

    # Last known status from BLE
    last_status: DeviceStatus | None = None

    # Configuration data (profiles, channels, etc.) - None for newly discovered devices
    device_data: LightDevice | None = None

    model_config = ConfigDict(extra="forbid")


UnifiedDevice = UnifiedDoserDevice | UnifiedLightDevice


class UnifiedDeviceStorage:
    """Storage manager for unified device files."""

    def __init__(self, devices_dir: Path | str):
        """Initialize storage with the devices directory."""
        self._devices_dir = Path(devices_dir)
        self._devices_dir.mkdir(parents=True, exist_ok=True)

    def _get_device_file_path(self, device_id: str) -> Path:
        """Get the file path for a specific device."""
        safe_id = device_id.replace(":", "_")
        return self._devices_dir / f"{safe_id}.json"

    def read_device(self, device_id: str) -> UnifiedDoserDevice | UnifiedLightDevice | None:
        """Read a unified device file."""
        device_file = self._get_device_file_path(device_id)
        if not device_file.exists():
            return None

        try:
            data = json.loads(device_file.read_text(encoding="utf-8"))
            device_type = data.get("device_type")

            if device_type == "doser":
                return UnifiedDoserDevice.model_validate(data)
            elif device_type == "light":
                return UnifiedLightDevice.model_validate(data)
            else:
                logger.warning(f"Unknown device type '{device_type}' in {device_file}")
                return None
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(f"Failed to read device file {device_file}: {exc}")
            return None

    def write_device(self, device: UnifiedDoserDevice | UnifiedLightDevice) -> None:
        """Write a unified device file atomically."""
        device_file = self._get_device_file_path(device.device_id)
        device_file.parent.mkdir(parents=True, exist_ok=True)

        # Update timestamp
        device.last_updated = now_iso()

        # Write atomically
        tmp_file = device_file.with_suffix(".tmp")
        tmp_file.write_text(
            json.dumps(device.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp_file.replace(device_file)

    def update_status(
        self,
        device_id: str,
        device_type: Literal["doser", "light"],
        status: DeviceStatus,
    ) -> None:
        """Update only the status portion of a device file.

        Creates the device file if it doesn't exist (for newly discovered devices).
        """
        device = self.read_device(device_id)

        if device is None:
            # Create new device with status only - no configurations yet
            if device_type == "doser":
                device = UnifiedDoserDevice(
                    device_id=device_id,
                    last_updated=now_iso(),
                    last_status=status,
                    device_data=None,  # No configurations yet
                )
            else:  # light
                device = UnifiedLightDevice(
                    device_id=device_id,
                    last_updated=now_iso(),
                    last_status=status,
                    device_data=None,  # No configurations yet
                )
        else:
            # Update existing device's status
            device.last_status = status

        self.write_device(device)

    def list_all_devices(self) -> list[UnifiedDoserDevice | UnifiedLightDevice]:
        """List all unified device files."""
        devices = []
        for device_file in sorted(self._devices_dir.glob("*.json")):
            # Skip metadata files
            if device_file.name.endswith(".metadata.json"):
                continue

            device_id = device_file.stem.replace("_", ":")
            device = self.read_device(device_id)
            if device:
                devices.append(device)

        return devices

    def delete_device(self, device_id: str) -> bool:
        """Delete a device file."""
        device_file = self._get_device_file_path(device_id)
        if device_file.exists():
            device_file.unlink()
            return True
        return False

    def clear_device_configurations(self, device_id: str) -> bool:
        """Clear all configurations from a device, preserve metadata and status."""
        try:
            device = self.read_device(device_id)
            if device is None:
                return False

            # Clear device_data (configurations) while preserving metadata and status
            device.device_data = None
            self.write_device(device)
            logger.info(f"Cleared configurations for device {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear configurations for device {device_id}: {e}")
            return False
