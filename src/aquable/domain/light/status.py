from dataclasses import dataclass


@dataclass(slots=True)
class LightKeyframe:
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
    keyframes: list[LightKeyframe]
    time_markers: list[tuple[int, int]]
    tail: bytes
    raw_payload: bytes
