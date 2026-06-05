from dataclasses import dataclass
from typing import Any

from ..validation import ensure_unique_values
from .schedule import Recurrence, parse_schedule


@dataclass(slots=True)
class VolumeTracking:
    enabled: bool
    capacityMl: float | None = None
    currentMl: float | None = None
    lowThresholdMl: float | None = None
    updatedAt: str | None = None

@dataclass(slots=True)
class Calibration:
    mlPerSecond: float
    lastCalibratedAt: str

    def __post_init__(self):
        if self.mlPerSecond <= 0:
            raise ValueError("mlPerSecond must be > 0")

@dataclass(slots=True)
class DoserHeadStats:
    dosesToday: int | None = None
    mlDispensedToday: float | None = None

@dataclass(slots=True)
class DoserHead:
    index: int
    active: bool
    schedule: Any
    recurrence: Recurrence
    missedDoseCompensation: bool
    calibration: Calibration
    label: str | None = None
    volumeTracking: VolumeTracking | None = None
    stats: DoserHeadStats | None = None

    @classmethod
    def from_dict(cls, data: dict) -> 'DoserHead':
        data = data.copy()
        if "schedule" in data and isinstance(data["schedule"], dict):
            data["schedule"] = parse_schedule(data["schedule"])
        if "recurrence" in data and isinstance(data["recurrence"], dict):
            data["recurrence"] = Recurrence(**data["recurrence"])
        if "calibration" in data and isinstance(data["calibration"], dict):
            data["calibration"] = Calibration(**data["calibration"])
        if "volumeTracking" in data and isinstance(data["volumeTracking"], dict):
            data["volumeTracking"] = VolumeTracking(**data["volumeTracking"])
        if "stats" in data and isinstance(data["stats"], dict):
            data["stats"] = DoserHeadStats(**data["stats"])
        return cls(**data)

@dataclass(slots=True)
class ConfigurationRevision:
    revision: int
    savedAt: str
    heads: list[DoserHead]
    note: str | None = None
    savedBy: str | None = None

    def __post_init__(self):
        if not self.heads:
            raise ValueError("Configuration revision must include at least one head")
        if len(self.heads) > 4:
            raise ValueError("Configuration revision cannot have more than four heads")
        ensure_unique_values([str(head.index) for head in self.heads], "head index")

    @classmethod
    def from_dict(cls, data: dict) -> 'ConfigurationRevision':
        data = data.copy()
        if "heads" in data:
            data["heads"] = [DoserHead.from_dict(h) if isinstance(h, dict) else h for h in data["heads"]]
        return cls(**data)

@dataclass(slots=True)
class DeviceConfiguration:
    id: str
    name: str
    revisions: list[ConfigurationRevision]
    createdAt: str
    updatedAt: str
    description: str | None = None

    def __post_init__(self):
        if not self.revisions:
            raise ValueError("Device configuration must include at least one revision")
        self.revisions.sort(key=lambda rev: rev.revision)
        revision_numbers = [rev.revision for rev in self.revisions]
        if len(set(revision_numbers)) != len(revision_numbers):
            raise ValueError("Configuration revisions must be unique")
        if revision_numbers[0] != 1:
            raise ValueError("Configuration revisions must start at 1")
        for previous, current in zip(revision_numbers, revision_numbers[1:], strict=False):
            if current != previous + 1:
                raise ValueError("Configuration revision numbers must increase sequentially")

    def latest_revision(self) -> ConfigurationRevision:
        return self.revisions[-1]

    @classmethod
    def from_dict(cls, data: dict) -> 'DeviceConfiguration':
        data = data.copy()
        if "revisions" in data:
            data["revisions"] = [ConfigurationRevision.from_dict(r) if isinstance(r, dict) else r for r in data["revisions"]]
        return cls(**data)
