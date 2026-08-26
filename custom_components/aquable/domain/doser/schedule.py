from dataclasses import dataclass
from typing import Any, Literal

from ..validation import ensure_unique_values

Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ModeKind = Literal["single", "every_hour", "custom_periods", "timer"]


@dataclass(slots=True)
class Recurrence:
    days: list[str]

    def __post_init__(self):
        if not self.days:
            raise ValueError("Recurrence must include at least one day")
        ensure_unique_values(self.days, "weekday")


@dataclass(slots=True)
class SingleSchedule:
    dailyDoseMl: float
    startTime: str
    mode: str = "single"


@dataclass(slots=True)
class EveryHourSchedule:
    dailyDoseMl: float
    startTime: str
    mode: str = "every_hour"


@dataclass(slots=True)
class CustomPeriod:
    startTime: str
    endTime: str
    doses: int


@dataclass(slots=True)
class CustomPeriodsSchedule:
    dailyDoseMl: float
    periods: list[CustomPeriod]
    mode: str = "custom_periods"

    def __post_init__(self):
        if not self.periods:
            raise ValueError("Custom periods schedule requires at least one period")
        total_doses = sum(period.doses for period in self.periods)
        if total_doses > 24:
            raise ValueError("Custom periods schedule cannot exceed 24 doses in total")


@dataclass(slots=True)
class TimerDose:
    time: str
    quantityMl: float


@dataclass(slots=True)
class TimerSchedule:
    doses: list[TimerDose]
    mode: str = "timer"
    defaultDoseQuantityMl: float | None = None
    dailyDoseMl: float | None = None

    def __post_init__(self):
        if not self.doses:
            raise ValueError("Timer schedule requires at least one dose")
        if len(self.doses) > 24:
            raise ValueError("Timer schedule cannot include more than 24 doses")


def parse_schedule(data: dict) -> Any:
    mode = data.get("mode")
    if mode == "single":
        return SingleSchedule(dailyDoseMl=data["dailyDoseMl"], startTime=data["startTime"])
    elif mode == "every_hour":
        return EveryHourSchedule(dailyDoseMl=data["dailyDoseMl"], startTime=data["startTime"])
    elif mode == "custom_periods":
        periods = [CustomPeriod(**p) for p in data.get("periods", [])]
        return CustomPeriodsSchedule(dailyDoseMl=data["dailyDoseMl"], periods=periods)
    elif mode == "timer":
        doses = [TimerDose(**d) for d in data.get("doses", [])]
        return TimerSchedule(
            doses=doses,
            defaultDoseQuantityMl=data.get("defaultDoseQuantityMl"),
            dailyDoseMl=data.get("dailyDoseMl"),
        )
    raise ValueError(f"Unknown schedule mode: {mode}")
