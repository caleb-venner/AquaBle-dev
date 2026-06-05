"""Domain package for device data structures and configuration management.

This package provides pure functional models for dosers and lights.
"""

from . import storage, validation
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
    DoserStatus,
    EveryHourSchedule,
    HeadSnapshot,
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
    CustomKeyframe,
    CustomProfile,
    LightConfiguration,
    LightDevice,
    LightKeyframe,
    LightProfileRevision,
    LightStatus,
    ManualProfile,
)

__all__ = [
    "storage",
    "validation",
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
    "DoserStatus",
    "DoserWeekday",
    "EveryHourSchedule",
    "HeadSnapshot",
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
    "CustomKeyframe",
    "CustomProfile",
    "LightConfiguration",
    "LightDevice",
    "LightKeyframe",
    "LightProfileRevision",
    "LightStatus",
    "ManualProfile",
]
