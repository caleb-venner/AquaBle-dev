"""Storage package for device persistence and configuration management.

This package provides type-safe storage facades for different device types,
all built on a common base storage class that handles file I/O operations.
"""

# Base storage
from .base import BaseDeviceStorage

# Device-specific storage classes
from .doser import (
    Calibration,
    ConfigurationRevision,
    CustomPeriod,
    CustomPeriodsSchedule,
    DeviceConfiguration,
    DoserDevice,
    DoserHead,
    DoserHeadStats,
    DoserMetadata,
    DoserStorage,
    EveryHourSchedule,
    ModeKind,
    Recurrence,
    SingleSchedule,
    TimerDose,
    TimerSchedule,
    VolumeTracking,
)
from .doser import Weekday as DoserWeekday
from .light import (
    AutoProfile,
    AutoProgram,
    ChannelDef,
    CustomPoint,
    CustomProfile,
    InterpolationKind,
    LightConfiguration,
    LightDevice,
    LightMetadata,
    LightProfileRevision,
    LightStorage,
    ManualProfile,
)
from .light import Weekday as LightWeekday

# Status models
from .models import DoserStatus, LightStatus

# Storage utilities
from .utils import ensure_unique_values, filter_device_json_files

__all__ = [
    # Base
    "BaseDeviceStorage",
    # Doser
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
    "DoserWeekday",
    "EveryHourSchedule",
    "ModeKind",
    "Recurrence",
    "SingleSchedule",
    "TimerDose",
    "TimerSchedule",
    "VolumeTracking",
    # Light
    "AutoProfile",
    "AutoProgram",
    "ChannelDef",
    "CustomPoint",
    "CustomProfile",
    "InterpolationKind",
    "LightConfiguration",
    "LightDevice",
    "LightMetadata",
    "LightProfileRevision",
    "LightStorage",
    "LightWeekday",
    "ManualProfile",
    # Utils
    "ensure_unique_values",
    "filter_device_json_files",
    # Status models
    "DoserStatus",
    "LightStatus",
]
