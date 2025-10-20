"""Persistent storage models and helpers for Chihiros dosing pumps.

This module provides individual file-based storage for each device,
with each device configuration saved as a separate JSON file named by MAC address.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .storage_utils import ensure_unique_values, filter_device_json_files
from .time_utils import now_iso as _now_iso

logger = logging.getLogger(__name__)

Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ModeKind = Literal["single", "every_hour", "custom_periods", "timer"]
TimeString = Field(pattern=r"^\d{2}:\d{2}$")


class DeviceMetadata(BaseModel):
    """Lightweight device metadata for server-side name storage only."""

    id: str
    name: str | None = None
    headNames: dict[int, str] | None = None  # Map of head index to name
    autoReconnect: bool = False  # Auto-reconnect on service start
    createdAt: str | None = None
    updatedAt: str | None = None

    model_config = ConfigDict(extra="forbid")


class Recurrence(BaseModel):
    """Represents the weekdays a schedule runs on."""

    days: list[Weekday]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_days(self) -> "Recurrence":
        """Validate recurrence days are present and unique."""
        if not self.days:
            raise ValueError("Recurrence must include at least one day")
        ensure_unique_values(self.days, "weekday")
        return self


class VolumeTracking(BaseModel):
    """Volume tracking metadata for a dosing head."""

    enabled: bool
    capacityMl: float | None = Field(default=None, ge=0)
    currentMl: float | None = Field(default=None, ge=0)
    lowThresholdMl: float | None = Field(default=None, ge=0)
    updatedAt: str | None = None  # ISO string kept verbatim

    model_config = ConfigDict(extra="forbid")

    def __init__(self, **data):
        """Minimal initializer to satisfy docstring checks for __init__."""
        super().__init__(**data)


class Calibration(BaseModel):
    """Calibration information mapping seconds to millilitres."""

    mlPerSecond: float = Field(gt=0)
    lastCalibratedAt: str  # ISO date string

    model_config = ConfigDict(extra="forbid")

    def __repr__(self) -> str:  # pragma: no cover - helpful repr
        """Return a concise representation for debugging/testing."""
        return f"Calibration(mlPerSecond={self.mlPerSecond})"


class DoserHeadStats(BaseModel):
    """Runtime statistics for a dosing head."""

    dosesToday: int | None = Field(default=None, ge=0)
    mlDispensedToday: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")

    def __repr__(self) -> str:  # pragma: no cover - concise repr
        """Return a concise representation for doser head stats."""
        return f"DoserHeadStats(dosesToday={self.dosesToday})"


class SingleSchedule(BaseModel):
    """Single daily dose schedule."""

    mode: Literal["single"]
    dailyDoseMl: float = Field(gt=0)
    startTime: str = TimeString

    model_config = ConfigDict(extra="forbid")

    """Schedule representing a single daily dose at a fixed time."""


class EveryHourSchedule(BaseModel):
    """Schedule dosing every N hours starting at a time."""

    mode: Literal["every_hour"]
    dailyDoseMl: float = Field(gt=0)
    startTime: str = TimeString

    model_config = ConfigDict(extra="forbid")

    """Schedule for dosing every hour starting at a time."""


class CustomPeriod(BaseModel):
    """A single custom period in a custom_periods schedule."""

    startTime: str = TimeString
    endTime: str = TimeString
    doses: int = Field(ge=1)

    model_config = ConfigDict(extra="forbid")

    """A period entry within a custom periods schedule."""


class CustomPeriodsSchedule(BaseModel):
    """Schedule composed of named time periods with dose counts."""

    mode: Literal["custom_periods"]
    dailyDoseMl: float = Field(gt=0)
    periods: list[CustomPeriod]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_periods(self) -> "CustomPeriodsSchedule":
        """Validate that custom periods are present and sane."""
        if not self.periods:
            raise ValueError("Custom periods schedule requires at least one period")

        total_doses = sum(period.doses for period in self.periods)
        if total_doses > 24:
            raise ValueError("Custom periods schedule cannot exceed 24 doses in total")
        return self


class TimerDose(BaseModel):
    """A single timed dose entry for a timer schedule."""

    time: str = TimeString
    quantityMl: float = Field(gt=0)

    model_config = ConfigDict(extra="forbid")

    """Represents a timed single dose within a timer schedule."""


class TimerSchedule(BaseModel):
    """Timer-based schedule with explicit dose times."""

    mode: Literal["timer"]
    doses: list[TimerDose]
    defaultDoseQuantityMl: float | None = Field(default=None, gt=0)
    dailyDoseMl: float | None = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_doses(self) -> "TimerSchedule":
        """Validate doses list for a timer schedule."""
        if not self.doses:
            raise ValueError("Timer schedule requires at least one dose")
        if len(self.doses) > 24:
            raise ValueError("Timer schedule cannot include more than 24 doses")
        return self


Schedule = Field(discriminator="mode")


class DoserHead(BaseModel):
    """Model for a dosing head (index, schedule, calibration, stats)."""

    index: Literal[1, 2, 3, 4]
    label: str | None = None
    active: bool
    schedule: SingleSchedule | EveryHourSchedule | CustomPeriodsSchedule | TimerSchedule = Schedule
    recurrence: Recurrence
    missedDoseCompensation: bool
    volumeTracking: VolumeTracking | None = None
    calibration: Calibration
    stats: DoserHeadStats | None = None

    model_config = ConfigDict(extra="forbid")

    """Representation of a dosing head on a device."""


class ConfigurationRevision(BaseModel):
    """A single revision snapshot containing head definitions."""

    revision: int = Field(ge=1)
    savedAt: str
    heads: list[DoserHead]
    note: str | None = None
    savedBy: str | None = None

    model_config = ConfigDict(extra="forbid")

    """A single saved revision of a device configuration."""

    @model_validator(mode="after")
    def validate_heads(self) -> "ConfigurationRevision":
        """Ensure a configuration revision contains valid head entries."""
        if not self.heads:
            raise ValueError("Configuration revision must include at least one head")
        if len(self.heads) > 4:
            raise ValueError("Configuration revision cannot have more than four heads")
        ensure_unique_values([str(head.index) for head in self.heads], "head index")
        return self


class DeviceConfiguration(BaseModel):
    """A named device configuration composed of sequential revisions."""

    id: str
    name: str
    revisions: list[ConfigurationRevision]
    createdAt: str
    updatedAt: str
    description: str | None = None

    model_config = ConfigDict(extra="forbid")

    """Named configuration containing an ordered list of revisions."""

    @model_validator(mode="after")
    def validate_revisions(self) -> "DeviceConfiguration":
        """Validate the ordering and uniqueness of configuration revisions."""
        if not self.revisions:
            raise ValueError("Device configuration must include at least one revision")

        self.revisions.sort(key=lambda revision: revision.revision)
        revision_numbers = [revision.revision for revision in self.revisions]
        if len(set(revision_numbers)) != len(revision_numbers):
            raise ValueError("Configuration revisions must be unique")
        if revision_numbers[0] != 1:
            raise ValueError("Configuration revisions must start at 1")
        for previous, current in zip(revision_numbers, revision_numbers[1:]):
            if current != previous + 1:
                raise ValueError("Configuration revision numbers must increase sequentially")
        return self

    def latest_revision(self) -> ConfigurationRevision:
        """Return the latest revision in this configuration."""
        return self.revisions[-1]


class DoserDevice(BaseModel):
    """Top-level device model for dosing pumps, containing configurations."""

    id: str
    name: str | None = None
    configurations: list[DeviceConfiguration]
    activeConfigurationId: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None

    model_config = ConfigDict(extra="forbid")

    """Top-level device model for a dosing pump, including configs."""

    @model_validator(mode="after")
    def validate_configurations(self) -> "DoserDevice":
        """Validate the device has configurations and an active selection."""
        if not self.configurations:
            raise ValueError("A doser device must have at least one configuration")

        ids = [config.id for config in self.configurations]
        ensure_unique_values(ids, "configuration id")

        if self.activeConfigurationId is None:
            self.activeConfigurationId = self.configurations[0].id
        else:
            if self.activeConfigurationId not in ids:
                raise ValueError("Active configuration id does not match any configuration")
        return self

    def get_configuration(self, configuration_id: str) -> DeviceConfiguration:
        """Return the configuration with the given id or raise KeyError."""
        for configuration in self.configurations:
            if configuration.id == configuration_id:
                return configuration
        raise KeyError(configuration_id)

    def get_active_configuration(self) -> DeviceConfiguration:
        """Return the currently active configuration for this device."""
        if self.activeConfigurationId is None:
            raise ValueError("Device does not have an active configuration set")
        return self.get_configuration(self.activeConfigurationId)


class DoserDeviceCollection(BaseModel):
    """Container for a collection of doser devices (persisted store)."""

    devices: list[DoserDevice] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "DoserDeviceCollection":
        """Ensure device ids are unique within the collection."""
        ensure_unique_values([device.id for device in self.devices], "device id")
        return self


class DoserStorage:
    """A lightweight JSON-backed store for dosing pump configurations.

    Each device is stored in its own JSON file named by MAC address.
    For example: ~/.aqua-ble/doser_configs/58159AE1-5E0A-7915-3207-7868CBF2C600.json
    """

    def __init__(self, path: Path | str, metadata_dict: Dict[str, dict]):
        """Initialize the storage backed by the given directory path."""
        self._base_path = Path(path)
        self._metadata_dict = metadata_dict

        # Ensure the directory exists
        self._base_path.mkdir(parents=True, exist_ok=True)

        # Load metadata from all device files (including metadata-only files)
        self._load_all_metadata_from_disk()

    def _get_device_file_path(self, device_id: str) -> Path:
        """Get the file path for a specific device."""
        return self._base_path / f"{device_id}.json"

    def _load_all_metadata_from_disk(self) -> None:
        """Load metadata from all device files (including metadata-only files).
        
        This ensures that metadata for newly discovered devices without
        configurations is loaded from disk on startup.
        """
        try:
            for device_file in self._list_device_files():
                try:
                    device_id = device_file.stem  # filename without .json
                    raw = device_file.read_text(encoding="utf-8").strip()
                    if not raw:
                        continue

                    data = json.loads(raw)

                    # Load metadata if present
                    if "metadata" in data and data["metadata"]:
                        self._metadata_dict[device_id] = data["metadata"]
                except (json.JSONDecodeError, OSError):
                    # Skip files that can't be read
                    pass
        except (OSError, ValueError):
            # Directory might not exist or other issues - that's ok
            pass

    def _read_device_file(self, device_id: str) -> DoserDevice | None:
        """Read a single device from its JSON file (unified format)."""
        device_file = self._get_device_file_path(device_id)
        if not device_file.exists():
            return None

        try:
            raw = device_file.read_text(encoding="utf-8").strip()
            if not raw:
                return None

            data = json.loads(raw)

            # Handle both old format (direct device data) and unified format
            if "device_type" in data:
                # Unified format with metadata and status
                if data.get("device_type") != "doser":
                    return None  # Wrong device type

                # Extract device_data (configuration)
                device_data = data.get("device_data")

                # Load metadata into shared dict if present
                if "metadata" in data and data["metadata"]:
                    self._metadata_dict[device_id] = data["metadata"]

                # If device_data is None, this is a metadata-only file
                # (newly discovered device without config)
                if device_data is None:
                    return None
            else:
                # Old format (direct device data) - backward compatibility
                device_data = data

            return DoserDevice.model_validate(device_data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"Could not parse device file {device_file}: {exc}") from exc

    def _write_device_file(self, device_file: Path, device: DoserDevice) -> None:
        """Write a single device to its JSON file atomically (unified format).

        Preserves existing last_status if present in the file.
        """
        device_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing file to preserve last_status
        existing_last_status = None
        if device_file.exists():
            try:
                existing_data = json.loads(device_file.read_text(encoding="utf-8"))
                existing_last_status = existing_data.get("last_status")
            except (json.JSONDecodeError, OSError):
                # If we can't read the file, just proceed without last_status
                pass

        # Build unified device file
        data = {
            "device_type": "doser",
            "device_id": device.id,
            "last_updated": _now_iso(),
            "device_data": device.model_dump(mode="json"),
        }

        # Add metadata if present
        if device.id in self._metadata_dict:
            data["metadata"] = self._metadata_dict[device.id]

        # Preserve last_status if it existed
        if existing_last_status:
            data["last_status"] = existing_last_status

        tmp_file = device_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp_file.replace(device_file)

    def _write_metadata_file(self, device_id: str, metadata: dict) -> None:
        """Write metadata-only file for a device (for devices without configurations).
        
        This preserves existing device files but ensures metadata is persisted.
        """
        device_file = self._get_device_file_path(device_id)
        device_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing file if it exists to preserve device_data and last_status
        existing_data = {}
        if device_file.exists():
            try:
                existing_data = json.loads(device_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        # Update or create file with metadata
        data = existing_data or {
            "device_type": "doser",
            "device_id": device_id,
            "last_updated": _now_iso(),
        }
        
        # Update metadata
        data["metadata"] = metadata
        data["last_updated"] = _now_iso()

        tmp_file = device_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp_file.replace(device_file)

    def _list_device_files(self) -> list[Path]:
        """List all device JSON files in the storage directory.

        Excluding metadata files.
        """
        return filter_device_json_files(self._base_path)

    def list_devices(self) -> list[DoserDevice]:
        """Return all persisted devices."""
        devices = []
        for device_file in self._list_device_files():
            try:
                device_id = device_file.stem  # filename without .json
                device = self._read_device_file(device_id)
                if device:
                    devices.append(device)
            except ValueError as exc:
                # Log error but continue with other devices
                logger.warning(f"Could not load device from {device_file}: {exc}")
        return devices

    def get_device(self, device_id: str) -> DoserDevice | None:
        """Return a device by id or None if not found."""
        return self._read_device_file(device_id)

    def upsert_device(self, device: DoserDevice | dict) -> DoserDevice:
        """Insert or update a device and persist to its individual file."""
        model = self._validate_device(device)
        device_file = self._get_device_file_path(model.id)
        self._write_device_file(device_file, model)
        return model

    def upsert_many(self, devices: Iterable[DoserDevice | dict]) -> list[DoserDevice]:
        """Replace all devices with the provided devices."""
        models = [self._validate_device(device) for device in devices]

        # Remove all existing device files
        for device_file in self._list_device_files():
            device_file.unlink()

        # Write new devices
        for model in models:
            device_file = self._get_device_file_path(model.id)
            self._write_device_file(device_file, model)

        return models

    def delete_device(self, device_id: str) -> bool:
        """Delete a device by id, returning True if removed."""
        device_file = self._get_device_file_path(device_id)
        if device_file.exists():
            device_file.unlink()
            return True
        return False

    def list_configurations(self, device_id: str) -> list[DeviceConfiguration]:
        """List configurations for a given device id."""
        device = self._require_device(device_id)
        return list(device.configurations)

    def get_configuration(self, device_id: str, configuration_id: str) -> DeviceConfiguration:
        """Retrieve a specific configuration for a device."""
        device = self._require_device(device_id)
        return device.get_configuration(configuration_id)

    def create_configuration(
        self,
        device_id: str,
        name: str,
        heads: Iterable[DoserHead | dict],
        *,
        description: str | None = None,
        configuration_id: str | None = None,
        saved_by: str | None = None,
        note: str | None = None,
        saved_at: str | None = None,
        set_active: bool = False,
    ) -> DeviceConfiguration:
        """Create and append a new named configuration for a device."""
        device = self._require_device(device_id)

        new_id = configuration_id or str(uuid4())
        if any(configuration.id == new_id for configuration in device.configurations):
            raise ValueError(f"Configuration '{new_id}' already exists for device '{device_id}'")

        timestamp = saved_at or _now_iso()
        # Convert heads to proper DoserHead objects
        validated_heads = [
            (head if isinstance(head, DoserHead) else DoserHead.model_validate(head))
            for head in heads
        ]
        revision = ConfigurationRevision(
            revision=1,
            savedAt=timestamp,
            heads=validated_heads,
            note=note,
            savedBy=saved_by,
        )
        configuration = DeviceConfiguration(
            id=new_id,
            name=name,
            description=description,
            createdAt=timestamp,
            updatedAt=timestamp,
            revisions=[revision],
        )
        device.configurations.append(configuration)
        device.updatedAt = timestamp
        configuration.updatedAt = timestamp
        if set_active or device.activeConfigurationId is None:
            device.activeConfigurationId = configuration.id

        # Save the updated device
        self.upsert_device(device)
        return configuration

    def add_revision(
        self,
        device_id: str,
        configuration_id: str,
        heads: Iterable[DoserHead | dict],
        *,
        note: str | None = None,
        saved_by: str | None = None,
        saved_at: str | None = None,
    ) -> ConfigurationRevision:
        """Add a new revision to an existing configuration."""
        device = self._require_device(device_id)
        configuration = device.get_configuration(configuration_id)

        # Get next revision number
        latest_revision = max(rev.revision for rev in configuration.revisions)
        next_revision = latest_revision + 1

        timestamp = saved_at or _now_iso()
        # Convert heads to proper DoserHead objects
        validated_heads = [
            (head if isinstance(head, DoserHead) else DoserHead.model_validate(head))
            for head in heads
        ]
        revision = ConfigurationRevision(
            revision=next_revision,
            savedAt=timestamp,
            heads=validated_heads,
            note=note,
            savedBy=saved_by,
        )

        configuration.revisions.append(revision)
        configuration.updatedAt = timestamp
        device.updatedAt = timestamp

        # Save the updated device
        self.upsert_device(device)
        return revision

    def set_active_configuration(
        self, device_id: str, configuration_id: str
    ) -> DeviceConfiguration:
        """Set the active configuration id on a device and persist."""
        device = self._require_device(device_id)
        configuration = device.get_configuration(configuration_id)
        device.activeConfigurationId = configuration.id
        device.updatedAt = _now_iso()

        # Save the updated device
        self.upsert_device(device)
        return configuration

    def _validate_device(self, device: DoserDevice | dict) -> DoserDevice:
        """Validate or coerce an input into a DoserDevice model."""
        if isinstance(device, DoserDevice):
            return device
        return DoserDevice.model_validate(device)

    def _require_device(self, device_id: str) -> DoserDevice:
        """Return a device by id or raise KeyError if missing."""
        device = self.get_device(device_id)
        if device is None:
            raise KeyError(device_id)
        return device

    def get_device_metadata(self, device_id: str) -> DeviceMetadata | None:
        """Get device metadata (names only) by id."""
        metadata_raw = self._metadata_dict.get(device_id)
        if metadata_raw is None:
            return None

        # Extract head names from the latest revision if available
        head_names = {}
        device = self.get_device(device_id)
        if device and device.configurations:
            latest_config = device.configurations[-1]
            if latest_config.revisions:
                latest_revision = latest_config.revisions[-1]
                for head in latest_revision.heads:
                    if head.label:
                        head_names[head.index] = head.label

        return DeviceMetadata(
            id=metadata_raw.get("id", device_id),
            name=metadata_raw.get("name"),
            headNames=(head_names if head_names else metadata_raw.get("headNames")),
            autoReconnect=metadata_raw.get("autoReconnect", False),
            createdAt=metadata_raw.get("createdAt"),
            updatedAt=metadata_raw.get("updatedAt"),
        )

    def upsert_device_metadata(self, metadata: DeviceMetadata) -> DeviceMetadata:
        """Create or update device metadata (names only)."""
        current_time = _now_iso()
        metadata.updatedAt = current_time
        if not metadata.createdAt:
            metadata.createdAt = current_time

        # Store in metadata dict
        self._metadata_dict[metadata.id] = metadata.model_dump()

        # Check if device already exists and update it too
        existing_device = self.get_device(metadata.id)
        if existing_device:
            # Update existing device with new names
            existing_device.name = metadata.name
            existing_device.updatedAt = current_time

            # Update head names in the latest revision
            if metadata.headNames and existing_device.configurations:
                latest_config = existing_device.configurations[-1]
                if latest_config.revisions:
                    latest_revision = latest_config.revisions[-1]
                    for head in latest_revision.heads:
                        if head.index in metadata.headNames:
                            head.label = metadata.headNames[head.index]

            self.upsert_device(existing_device)
        else:
            # Device doesn't exist yet - persist metadata to disk independently
            self._write_metadata_file(metadata.id, metadata.model_dump())

        return metadata

    def list_device_metadata(self) -> list[DeviceMetadata]:
        """List all device metadata from the metadata dict."""
        metadata_list = []
        for device_id, metadata_raw in self._metadata_dict.items():
            # Extract head names from the latest revision if available
            head_names = {}
            device = self.get_device(device_id)
            if device and device.configurations:
                latest_config = device.configurations[-1]
                if latest_config.revisions:
                    latest_revision = latest_config.revisions[-1]
                    for head in latest_revision.heads:
                        if head.label:
                            head_names[head.index] = head.label

            metadata = DeviceMetadata(
                id=metadata_raw.get("id", device_id),
                name=metadata_raw.get("name"),
                headNames=(head_names if head_names else metadata_raw.get("headNames")),
                autoReconnect=metadata_raw.get("autoReconnect", False),
                createdAt=metadata_raw.get("createdAt"),
                updatedAt=metadata_raw.get("updatedAt"),
            )
            metadata_list.append(metadata)

        return metadata_list


__all__ = [
    "Calibration",
    "ConfigurationRevision",
    "CustomPeriod",
    "CustomPeriodsSchedule",
    "DeviceConfiguration",
    "DeviceMetadata",
    "DoserDevice",
    "DoserDeviceCollection",
    "DoserHead",
    "DoserHeadStats",
    "DoserStorage",
    "EveryHourSchedule",
    "ModeKind",
    "Recurrence",
    "SingleSchedule",
    "TimerDose",
    "TimerSchedule",
    "VolumeTracking",
    "Weekday",
]
