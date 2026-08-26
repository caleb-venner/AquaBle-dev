from dataclasses import dataclass
from typing import Any

from .schedule import parse_profile


@dataclass(slots=True)
class ChannelDef:
    key: str
    label: str
    min: int
    max: int
    step: int
    color: str | None = None


@dataclass(slots=True)
class LightProfileRevision:
    revision: int
    savedAt: str
    profile: Any
    note: str | None = None
    savedBy: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "LightProfileRevision":
        data = data.copy()
        if "profile" in data and isinstance(data["profile"], dict):
            data["profile"] = parse_profile(data["profile"])
        return cls(**data)


@dataclass(slots=True)
class LightConfiguration:
    id: str
    name: str
    revisions: list[LightProfileRevision]
    createdAt: str
    updatedAt: str
    description: str | None = None

    def __post_init__(self):
        if not self.revisions:
            raise ValueError("Light configuration must include at least one revision")
        self.revisions.sort(key=lambda rev: rev.revision)
        revision_numbers = [rev.revision for rev in self.revisions]
        if len(set(revision_numbers)) != len(revision_numbers):
            raise ValueError("Configuration revisions must be unique")

    def latest_revision(self) -> LightProfileRevision:
        return self.revisions[-1]

    @classmethod
    def from_dict(cls, data: dict) -> "LightConfiguration":
        data = data.copy()
        if "revisions" in data:
            data["revisions"] = [
                LightProfileRevision.from_dict(r) if isinstance(r, dict) else r
                for r in data["revisions"]
            ]
        return cls(**data)
