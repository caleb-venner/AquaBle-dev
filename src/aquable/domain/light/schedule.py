from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ManualProfile:
    levels: dict[str, int]
    mode: str = "manual"

@dataclass(slots=True)
class CustomKeyframe:
    time: str
    levels: dict[str, int]

@dataclass(slots=True)
class CustomProfile:
    points: list[CustomKeyframe]
    mode: str = "custom"

@dataclass(slots=True)
class AutoProgram:
    startTime: str
    endTime: str
    rampUpMinutes: int
    rampDownMinutes: int
    levels: dict[str, int]

@dataclass(slots=True)
class AutoProfile:
    programs: list[AutoProgram]
    mode: str = "auto"

def parse_profile(data: dict) -> Any:
    mode = data.get("mode")
    if mode == "manual":
        return ManualProfile(levels=data["levels"])
    elif mode == "custom":
        points = [CustomKeyframe(**p) for p in data.get("points", [])]
        return CustomProfile(points=points)
    elif mode == "auto":
        programs = [AutoProgram(**p) for p in data.get("programs", [])]
        return AutoProfile(programs=programs)
    raise ValueError(f"Unknown profile mode: {mode}")
