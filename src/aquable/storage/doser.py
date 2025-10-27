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

from ..utils.time import now_iso as _now_iso
from .base import BaseDeviceStorage
from .utils import ensure_unique_values

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
    headNames: dict[int, str] | None = None  # Map of head index to name
    autoReconnect: bool = False  # Auto-reconnect on service start
    configurations: list[DeviceConfiguration]
    activeConfigurationId: str | None = None
    model_code: str | None = None  # Device model code (e.g., "DYDOSE")
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
        """DEPRECATED: Get device metadata (names only) by id.

        Metadata is now stored in the device configuration itself (device_data).
        Use get_device() instead and access name/headNames/autoReconnect from the DoserDevice.

        This method is kept for backward compatibility during migration.
        """
        device = self.get_device(device_id)
        if device is None:
            return None

        return DoserMetadata(
            id=device.id,
            name=device.name,
            headNames=device.headNames,
            autoReconnect=device.autoReconnect,
            createdAt=device.createdAt,
            updatedAt=device.updatedAt,
        )

    def create_default_device(self, device_id: str, model_code: str | None = None) -> DoserDevice:
        """Create a skeleton DoserDevice with one minimal configuration.

        This is used when a device is discovered but has no saved configuration yet.
        Creates a device with one empty configuration with 4 disabled heads.

        Args:
            device_id: Device MAC address (e.g., '58159AE1-5E0A-7915-3207-7868CBF2C600')
            model_code: Optional device model code (e.g., 'DYDOSE')

        Returns:
            DoserDevice with one default configuration
        """
        now = _now_iso()
        config_id = str(uuid4())

        # Create 4 disabled heads with minimal schedules
        heads = [
            DoserHead(
                index=1,
                active=False,
                label=None,
                schedule=SingleSchedule(mode="single", dailyDoseMl=1.0, startTime="00:00"),
                recurrence=Recurrence(days=["monday"]),
                missedDoseCompensation=False,
                calibration=Calibration(mlPerSecond=1.0, lastCalibratedAt=now),
                stats=None,
            ),
            DoserHead(
                index=2,
                active=False,
                label=None,
                schedule=SingleSchedule(mode="single", dailyDoseMl=1.0, startTime="00:00"),
                recurrence=Recurrence(days=["monday"]),
                missedDoseCompensation=False,
                calibration=Calibration(mlPerSecond=1.0, lastCalibratedAt=now),
                stats=None,
            ),
            DoserHead(
                index=3,
                active=False,
                label=None,
                schedule=SingleSchedule(mode="single", dailyDoseMl=1.0, startTime="00:00"),
                recurrence=Recurrence(days=["monday"]),
                missedDoseCompensation=False,
                calibration=Calibration(mlPerSecond=1.0, lastCalibratedAt=now),
                stats=None,
            ),
            DoserHead(
                index=4,
                active=False,
                label=None,
                schedule=SingleSchedule(mode="single", dailyDoseMl=1.0, startTime="00:00"),
                recurrence=Recurrence(days=["monday"]),
                missedDoseCompensation=False,
                calibration=Calibration(mlPerSecond=1.0, lastCalibratedAt=now),
                stats=None,
            ),
        ]

        revision = ConfigurationRevision(
            revision=1,
            savedAt=now,
            heads=heads,
            note="Default configuration created on first discovery",
            savedBy="system",
        )

        config = DeviceConfiguration(
            id=config_id,
            name="Default",
            description="Default configuration created on first discovery",
            revisions=[revision],
            createdAt=now,
            updatedAt=now,
        )

        device = DoserDevice(
            id=device_id,
            name=None,
            headNames=None,
            autoReconnect=False,
            configurations=[config],
            activeConfigurationId=config_id,
            model_code=model_code,
            createdAt=now,
            updatedAt=now,
        )

        return device

    def upsert_device_metadata(self, metadata: DoserMetadata) -> DoserMetadata:
        """DEPRECATED: Create or update device metadata (names only).

        Metadata is now stored in the device configuration itself.
        Use upsert_device() with a DoserDevice that has naming fields set.

        This method is kept for backward compatibility during migration.
        """
        # Try to get existing device
        existing_device = self.get_device(metadata.id)

        current_time = _now_iso()

        if existing_device:
            # Update existing device with new names
            existing_device.name = metadata.name
            existing_device.headNames = metadata.headNames
            existing_device.autoReconnect = metadata.autoReconnect
            existing_device.updatedAt = current_time
            self.upsert_device(existing_device)
            return metadata
        else:
            # Create new device with minimal config if it doesn't exist
            # This shouldn't happen in practice (configurations should be created explicitly)
            # Just for backward compat, don't actually persist
            return metadata

    # Legacy method - no longer used internally
    def _update_head_names_in_device(self, device_id: str, head_names: dict) -> None:
        """INTERNAL: Update head names in the latest revision."""
        pass

    def list_device_metadata(self) -> list[DoserMetadata]:
        """DEPRECATED: List all device metadata from the metadata dictionary.

        Metadata is now stored in device configurations themselves.
        This method is kept for backward compatibility but will be empty
        as metadata is no longer maintained in a separate dictionary.
        """
        # Return empty list - metadata is now in device configurations
        return []


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
