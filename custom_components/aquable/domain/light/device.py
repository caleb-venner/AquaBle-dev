from dataclasses import dataclass
from typing import Any

from ..validation import ensure_unique_values
from .configuration import ChannelDef, LightConfiguration
from .schedule import AutoProfile, CustomProfile, ManualProfile


def _validate_levels_for_channels(levels: dict[str, int], channel_map: dict[str, ChannelDef]) -> None:
    expected = set(channel_map)
    provided = set(levels)
    missing = expected - provided
    if missing:
        raise ValueError(f"Missing levels for channels: {sorted(missing)}")
    extra = provided - expected
    if extra:
        raise ValueError(f"Unexpected channels: {sorted(extra)}")

    for key, val in levels.items():
        cdef = channel_map[key]
        if val < cdef.min or val > cdef.max:
            raise ValueError(f"Level {val} out of range {cdef.min}-{cdef.max}")
        if (val - cdef.min) % cdef.step != 0:
            raise ValueError(f"Level {val} must align with step {cdef.step}")

def _validate_profile_for_channels(profile: Any, channel_map: dict[str, ChannelDef]) -> None:
    if isinstance(profile, ManualProfile):
        _validate_levels_for_channels(profile.levels, channel_map)
    elif isinstance(profile, CustomProfile):
        for p in profile.points:
            _validate_levels_for_channels(p.levels, channel_map)
    elif isinstance(profile, AutoProfile):
        for p in profile.programs:
            _validate_levels_for_channels(p.levels, channel_map)

@dataclass(slots=True)
class LightDevice:
    id: str
    channels: list[ChannelDef]
    configurations: list[LightConfiguration]
    name: str | None = None
    autoReconnect: bool = False
    activeConfigurationId: str | None = None
    model_code: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None

    def __post_init__(self):
        if not self.channels:
            raise ValueError("Light device must define at least one channel")
        keys = [c.key for c in self.channels]
        ensure_unique_values(keys, "channel key")
        cmap = {c.key: c for c in self.channels}

        if not self.configurations:
            raise ValueError("Light device must have at least one configuration")

        cids = [c.id for c in self.configurations]
        ensure_unique_values(cids, "configuration id")

        for config in self.configurations:
            for rev in config.revisions:
                _validate_profile_for_channels(rev.profile, cmap)

        if self.activeConfigurationId is None:
            self.activeConfigurationId = self.configurations[0].id
        elif self.activeConfigurationId not in cids:
            raise ValueError("Active configuration id does not match any configuration")

    def get_configuration(self, configuration_id: str) -> LightConfiguration:
        for c in self.configurations:
            if c.id == configuration_id:
                return c
        raise KeyError(configuration_id)

    def get_active_configuration(self) -> LightConfiguration:
        if self.activeConfigurationId is None:
            raise ValueError("No active configuration set")
        return self.get_configuration(self.activeConfigurationId)

    @classmethod
    def from_dict(cls, data: dict) -> 'LightDevice':
        data = data.copy()
        if "channels" in data:
            data["channels"] = [ChannelDef(**c) if isinstance(c, dict) else c for c in data["channels"]]
        if "configurations" in data:
            data["configurations"] = [LightConfiguration.from_dict(c) if isinstance(c, dict) else c for c in data["configurations"]]
        return cls(**data)
