"""Generic base class for device storage with common file I/O operations.

This module provides a base class for managing device configurations stored
as individual JSON files. It handles file I/O, metadata management, and common
CRUD operations that are shared between DoserStorage and LightStorage.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel

from ..utils.time import now_iso as _now_iso
from .utils import filter_device_json_files

logger = logging.getLogger(__name__)


# Generic type variable for device models (DoserDevice, LightDevice, etc.)
# Bounded by BaseModel to ensure model_dump() is available
TDevice = TypeVar("TDevice", bound=BaseModel)


class BaseDeviceStorage(ABC, Generic[TDevice]):
    """Abstract base class for device storage with common file operations.

    This class provides the common file I/O and CRUD operations needed for
    managing device configurations stored in individual JSON files following
    the unified storage format.

    Subclasses should implement the device_type property and _validate_device
    method for device-specific validation.
    """

    def __init__(self, storage_dir: Path | str, metadata_dict: Dict[str, dict]):
        """Initialize storage with unified directory structure.

        Args:
            storage_dir: Directory containing individual device files
            metadata_dict: Shared dictionary for metadata across storage instances
        """
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_dict = metadata_dict

        # Load metadata from all device files on initialization
        self._load_all_metadata_from_disk()

    @property
    @abstractmethod
    def device_type(self) -> str:
        """Return the device type string (e.g., 'doser', 'light')."""
        pass

    @abstractmethod
    def _validate_device(self, device: TDevice | dict) -> TDevice:
        """Validate or coerce an input into the appropriate device model.

        Args:
            device: Device object or dictionary to validate

        Returns:
            Validated device model instance

        Raises:
            ValueError: If validation fails
        """
        pass

    def _get_device_file_path(self, device_id: str) -> Path:
        """Get the file path for a specific device.

        Handles both underscore-escaped format (AA_BB_CC_DD_EE_FF) and
        colon format (AA:BB:CC:DD:EE:FF) for backward compatibility.

        Args:
            device_id: Device identifier (MAC address)

        Returns:
            Path to the device's configuration file
        """
        safe_id = device_id.replace(":", "_")
        escaped_path = self._storage_dir / f"{safe_id}.json"

        # If the underscore-escaped version exists, use it
        if escaped_path.exists():
            return escaped_path

        # Otherwise, try the colon version for backward compatibility with old files
        colon_path = self._storage_dir / f"{device_id}.json"
        if colon_path.exists():
            return colon_path

        # If neither exists, return the preferred escaped format for new files
        return escaped_path

    def _load_all_metadata_from_disk(self) -> None:
        """Load metadata from all device files on startup.

        DEPRECATED: Metadata is now stored in device_data. This method is kept
        for backward compatibility but is effectively a no-op.
        """
        # Metadata is now part of the device configuration (device_data)
        # This method is kept for backward compatibility but does nothing
        pass

    def _read_device_file(self, device_id: str) -> TDevice | None:
        """Read a single device from its JSON file (unified format).

        Args:
            device_id: Device identifier (MAC address)

        Returns:
            Device model instance or None if not found or device_data is missing
        """
        device_file = self._get_device_file_path(device_id)
        if not device_file.exists():
            return None

        try:
            raw = device_file.read_text(encoding="utf-8").strip()
            if not raw:
                return None

            data = json.loads(raw)

            # Validate device type matches
            if data.get("device_type") != self.device_type:
                logger.warning(
                    f"Device file {device_file} has wrong type: "
                    f"expected {self.device_type}, got {data.get('device_type')}"
                )
                return None

            # Extract device_data (configuration)
            # Metadata is now stored within device_data, not separately
            device_data = data.get("device_data")

            # If device_data is None, this is a metadata-only file (legacy format)
            if device_data is None:
                return None

            return self._validate_device(device_data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(f"Could not parse device file {device_file}: {exc}")
            raise ValueError(f"Could not parse device file {device_file}: {exc}") from exc

    def _write_device_file(self, device_file: Path, device: TDevice) -> None:
        """Write a device to its JSON file atomically (unified format).

        Preserves existing last_status if present in the file.
        Metadata is now stored within device_data.

        Args:
            device_file: Path to the device file
            device: Device model to write
        """
        device_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing file to preserve last_status
        existing_last_status = None
        if device_file.exists():
            try:
                existing_data = json.loads(device_file.read_text(encoding="utf-8"))
                existing_last_status = existing_data.get("last_status")
            except (json.JSONDecodeError, OSError):
                # If we can't read the file, proceed without last_status
                pass

        # Get device id from the device model
        device_id = getattr(device, "id")

        # Build unified device file (metadata no longer separate)
        data = {
            "device_type": self.device_type,
            "device_id": device_id,
            "last_updated": _now_iso(),
            "device_data": device.model_dump(mode="json"),
        }

        # Preserve last_status if it existed
        if existing_last_status:
            data["last_status"] = existing_last_status

        # Atomic write using temporary file
        tmp_file = device_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp_file.replace(device_file)

    def _write_metadata_file(self, device_id: str, metadata: dict) -> None:
        """DEPRECATED: Write metadata-only file for a device.

        This method is deprecated as metadata is now stored within device_data.
        It is kept for backward compatibility but does nothing.

        Args:
            device_id: Device identifier (MAC address)
            metadata: Metadata dictionary to write (ignored)
        """
        # Metadata is now part of device_data. This method is deprecated.
        pass

    def _list_device_files(self) -> list[Path]:
        """List all device JSON files in the storage directory.

        Returns:
            List of Path objects for device files
        """
        return filter_device_json_files(self._storage_dir)

    def list_devices(self) -> list[TDevice]:
        """Return all persisted devices.

        Returns:
            List of device model instances
        """
        devices = []
        for device_file in self._list_device_files():
            try:
                device_id = device_file.stem.replace("_", ":")
                device = self._read_device_file(device_id)
                if device:
                    devices.append(device)
            except ValueError as exc:
                logger.warning(f"Could not load device from {device_file}: {exc}")
        return devices

    def get_device(self, device_id: str) -> TDevice | None:
        """Return a device by id or None if not found.

        Args:
            device_id: Device identifier (MAC address)

        Returns:
            Device model instance or None
        """
        return self._read_device_file(device_id)

    def get_device_with_status(self, device_id: str) -> dict | None:
        """Return device configuration with last_status included for API responses.

        This reads the complete device file including the last_status field,
        useful for frontend display of live device information.

        Args:
            device_id: Device identifier (MAC address)

        Returns:
            Dictionary containing device data and last_status, or None if not found
        """
        device_file = self._get_device_file_path(device_id)
        if not device_file.exists():
            return None

        try:
            raw = device_file.read_text(encoding="utf-8").strip()
            if not raw:
                return None

            data = json.loads(raw)

            # Validate device type matches
            if data.get("device_type") != self.device_type:
                logger.warning(
                    f"Device file {device_file} has wrong type: "
                    f"expected {self.device_type}, got {data.get('device_type')}"
                )
                return None

            # Extract device_data
            device_data = data.get("device_data")
            if device_data is None:
                return None

            # Validate the device_data
            self._validate_device(device_data)

            # Build response with device_data and optional last_status
            response = device_data.copy() if isinstance(device_data, dict) else device_data
            if "last_status" in data:
                if isinstance(response, dict):
                    response["last_status"] = data["last_status"]
                else:
                    # If response is a Pydantic model, convert to dict and add last_status
                    response = {
                        **response.model_dump(mode="json"),
                        "last_status": data["last_status"],
                    }

            return response
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(f"Could not parse device file {device_file}: {exc}")
            return None

    def upsert_device(self, device: TDevice | dict) -> TDevice:
        """Insert or update a device and persist to its individual file.

        Args:
            device: Device model or dictionary to save

        Returns:
            Validated device model instance
        """
        model = self._validate_device(device)
        device_id = getattr(model, "id")
        device_file = self._get_device_file_path(device_id)
        self._write_device_file(device_file, model)
        return model

    def delete_device(self, device_id: str) -> bool:
        """Delete a device by id.

        Args:
            device_id: Device identifier (MAC address)

        Returns:
            True if device was deleted, False if it didn't exist
        """
        device_file = self._get_device_file_path(device_id)
        if device_file.exists():
            try:
                device_file.unlink()
                # Also remove metadata from cache
                self._metadata_dict.pop(device_id, None)
                return True
            except OSError as exc:
                logger.error(f"Could not delete device file {device_file}: {exc}")
                return False
        return False

    def _require_device(self, device_id: str) -> TDevice:
        """Return a device by id or raise KeyError if missing.

        Args:
            device_id: Device identifier (MAC address)

        Returns:
            Device model instance

        Raises:
            KeyError: If device not found
        """
        device = self.get_device(device_id)
        if device is None:
            raise KeyError(device_id)
        return device

    def update_device_status(self, device_id: str, status: Dict[str, Any]) -> None:
        """Update only the status portion of a device file.

        Creates the device file if it doesn't exist (for newly discovered devices).
        Preserves existing metadata and device_data if present.

        Args:
            device_id: Device identifier (MAC address)
            status: Status dictionary to store (should match DeviceStatus format)
        """
        device_file = self._get_device_file_path(device_id)

        # Read existing data if file exists
        existing_data = {}
        if device_file.exists():
            try:
                existing_data = json.loads(device_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                # If we can't read the file, start fresh
                pass

        # Create or update data structure
        data = existing_data or {
            "device_type": self.device_type,
            "device_id": device_id,
        }

        # Update status and timestamp
        data["last_status"] = status
        data["last_updated"] = _now_iso()

        # Ensure device_type is set correctly
        data["device_type"] = self.device_type
        data["device_id"] = device_id

        # Write atomically
        device_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = device_file.with_suffix(".tmp")
        tmp_file.write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp_file.replace(device_file)

    def get_device_status(self, device_id: str) -> Dict[str, Any] | None:
        """Get the last known status for a device.

        Args:
            device_id: Device identifier (MAC address)

        Returns:
            Status dictionary or None if no status available
        """
        device_file = self._get_device_file_path(device_id)
        if not device_file.exists():
            return None

        try:
            data = json.loads(device_file.read_text(encoding="utf-8"))
            return data.get("last_status")
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(f"Could not read status from {device_file}: {exc}")
            return None

    def list_all_devices_with_metadata(self) -> list[Dict[str, Any]]:
        """List all devices including those with only metadata (no device_data).

        Returns a list of dictionaries with device information, suitable for
        BLEService to enumerate all known devices.

        Returns:
            List of device info dictionaries with keys:
                - device_id: Device MAC address
                - device_type: 'doser' or 'light'
                - has_device_data: Whether device has configurations
                - metadata: Device metadata if present
                - last_status: Last status if present
        """
        devices = []
        for device_file in self._list_device_files():
            try:
                device_id = device_file.stem.replace("_", ":")
                data = json.loads(device_file.read_text(encoding="utf-8"))

                # Only include devices of this storage type
                if data.get("device_type") != self.device_type:
                    continue

                device_info = {
                    "device_id": device_id,
                    "device_type": self.device_type,
                    "has_device_data": data.get("device_data") is not None,
                    "metadata": data.get("metadata"),
                    "last_status": data.get("last_status"),
                }
                devices.append(device_info)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(f"Could not read device file {device_file}: {exc}")
                continue

        return devices


__all__ = ["BaseDeviceStorage"]
