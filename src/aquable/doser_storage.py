"""Persistent storage models and helpers for Chihiros dosing pumps.

This module provides individual file-based storage for each device,
with each device configuration saved as a separate JSON file named by MAC address.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .base_device_storage import BaseDeviceStorage
from .storage_utils import ensure_unique_values
from .time_utils import now_iso as _now_iso

logger = logging.getLogger(__name__)

Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ModeKind = Literal["single", "every_hour", "custom_periods", "timer"]
TimeString = Field(pattern=r"^\d{2}:\d{2}$")


class DoserMetadata(BaseModel):
    """Lightweight doser metadata for server-side name storage only."""

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


class EveryHourSchedule(BaseModel):
    """Schedule dosing every N hours starting at a time."""

    mode: Literal["every_hour"]
    dailyDoseMl: float = Field(gt=0)
    startTime: str = TimeString

    model_config = ConfigDict(extra="forbid")


class CustomPeriod(BaseModel):
    """A single custom period in a custom_periods schedule."""

    startTime: str = TimeString
    endTime: str = TimeString
    doses: int = Field(ge=1)

    model_config = ConfigDict(extra="forbid")


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


class ConfigurationRevision(BaseModel):
    """A single revision snapshot containing head definitions."""

    revision: int = Field(ge=1)
    savedAt: str
    heads: list[DoserHead]
    note: str | None = None
    savedBy: str | None = None

    model_config = ConfigDict(extra="forbid")

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


class DoserStorage(BaseDeviceStorage[DoserDevice]):
    """A lightweight JSON-backed store for dosing pump configurations.

    Each device is stored in its own JSON file named by MAC address.
    For example: ~/.aqua-ble/doser_configs/58159AE1-5E0A-7915-3207-7868CBF2C600.json

    Inherits common file I/O operations from BaseDeviceStorage.
    """

    def __init__(self, path: Path | str, metadata_dict: Dict[str, dict]):
        """Initialize the storage backed by the given directory path."""
        # Store base path for compatibility with existing code
        self._base_path = Path(path)
        # Call parent constructor which sets up _storage_dir
        super().__init__(path, metadata_dict)

    @property
    def device_type(self) -> str:
        """Return the device type string."""
        return "doser"

    def _validate_device(self, device: DoserDevice | dict) -> DoserDevice:
        """Validate or coerce an input into a DoserDevice model."""
        if isinstance(device, DoserDevice):
            return device
        return DoserDevice.model_validate(device)

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

    def get_device_metadata(self, device_id: str) -> DoserMetadata | None:
        """Get device metadata (names only) by id.

        Returns metadata stored in the metadata dictionary, which is the
        authoritative source for head names and device names.
        """
        metadata_raw = self._metadata_dict.get(device_id)
        if metadata_raw is None:
            return None

        return DoserMetadata(
            id=metadata_raw.get("id", device_id),
            name=metadata_raw.get("name"),
            headNames=metadata_raw.get("headNames"),
            autoReconnect=metadata_raw.get("autoReconnect", False),
            createdAt=metadata_raw.get("createdAt"),
            updatedAt=metadata_raw.get("updatedAt"),
        )

    def upsert_device_metadata(self, metadata: DoserMetadata) -> DoserMetadata:
        """Create or update device metadata (names only).

        Stores metadata in the in-memory dictionary and persists to disk.
        Also updates the device configuration's head labels if the device exists.
        """
        current_time = _now_iso()
        metadata.updatedAt = current_time
        if not metadata.createdAt:
            metadata.createdAt = current_time

        # Store in metadata dict (primary storage)
        metadata_dict = metadata.model_dump()
        self._metadata_dict[metadata.id] = metadata_dict

        # Persist to disk
        self._write_metadata_file(metadata.id, metadata_dict)

        # Check if device already exists and update it too
        # This keeps the device configuration's head labels in sync
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

        return metadata

    def list_device_metadata(self) -> list[DoserMetadata]:
        """List all device metadata from the metadata dictionary.

        Returns metadata stored in the metadata dict, which is the
        authoritative source for head names and device names.
        """
        metadata_list = []
        for device_id, metadata_raw in self._metadata_dict.items():
            metadata = DoserMetadata(
                id=metadata_raw.get("id", device_id),
                name=metadata_raw.get("name"),
                headNames=metadata_raw.get("headNames"),
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
    "DoserDevice",
    "DoserHead",
    "DoserHeadStats",
    "DoserMetadata",
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
