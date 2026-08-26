from dataclasses import dataclass, field


@dataclass(slots=True)
class LightSchedule:
    """A single auto-program schedule decoded from a device status payload.

    Corresponds to one entry added via create_add_auto_setting_command.
    """

    sunrise_hour: int
    sunrise_minute: int
    sunset_hour: int
    sunset_minute: int
    ramp_up_minutes: int
    weekday_mask: int
    # Brightness per channel, in device channel index order (e.g. R, G, B, W).
    # Length matches the number of channels the device supports.
    channel_brightness: list[int]

    def sunrise(self) -> str:
        return f"{self.sunrise_hour:02d}:{self.sunrise_minute:02d}"

    def sunset(self) -> str:
        return f"{self.sunset_hour:02d}:{self.sunset_minute:02d}"

    def weekdays(self) -> list[str]:
        """Decode the weekday bitmask into a list of day names."""
        _BITS = [
            (1 << 6, "monday"),
            (1 << 5, "tuesday"),
            (1 << 4, "wednesday"),
            (1 << 3, "thursday"),
            (1 << 2, "friday"),
            (1 << 1, "saturday"),
            (1 << 0, "sunday"),
        ]
        return [name for bit, name in _BITS if self.weekday_mask & bit]


@dataclass(slots=True)
class LightKeyframe:
    """Raw (hour, minute, value) triple, kept for backward compatibility and debugging."""

    hour: int
    minute: int
    value: int

    def as_time(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"


@dataclass(slots=True)
class LightStatus:
    message_id: tuple[int, int] | None
    response_mode: int | None
    weekday: int | None
    hour: int | None
    minute: int | None
    # Parsed auto-schedules. Populated when the payload encodes schedule blocks.
    schedules: list[LightSchedule] = field(default_factory=list)
    # Raw keyframes kept for devices/payloads that do not follow the schedule block layout.
    keyframes: list[LightKeyframe] = field(default_factory=list)
    time_markers: list[tuple[int, int]] = field(default_factory=list)
    tail: bytes = b""
    raw_payload: bytes = b""
