from dataclasses import dataclass

from ..validation import ensure_unique_values
from .configuration import DeviceConfiguration


@dataclass(slots=True)
class DoserMetadata:
    id: str
    name: str | None = None
    headNames: dict[int, str] | None = None
    autoReconnect: bool = False
    createdAt: str | None = None
    updatedAt: str | None = None

@dataclass(slots=True)
class DoserDevice:
    id: str
    configurations: list[DeviceConfiguration]
    name: str | None = None
    headNames: dict[int, str] | None = None
    autoReconnect: bool = False
    activeConfigurationId: str | None = None
    model_code: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None

    def __post_init__(self):
        if not self.configurations:
            raise ValueError("A doser device must have at least one configuration")
        ids = [config.id for config in self.configurations]
        ensure_unique_values(ids, "configuration id")
        if self.activeConfigurationId is None:
            self.activeConfigurationId = self.configurations[0].id
        elif self.activeConfigurationId not in ids:
            raise ValueError("Active configuration id does not match any configuration")

    def get_configuration(self, configuration_id: str) -> DeviceConfiguration:
        for config in self.configurations:
            if config.id == configuration_id:
                return config
        raise KeyError(configuration_id)

    def get_active_configuration(self) -> DeviceConfiguration:
        if self.activeConfigurationId is None:
            raise ValueError("Device does not have an active configuration set")
        return self.get_configuration(self.activeConfigurationId)

    @classmethod
    def from_dict(cls, data: dict) -> 'DoserDevice':
        data = data.copy()
        if "configurations" in data:
            data["configurations"] = [DeviceConfiguration.from_dict(c) if isinstance(c, dict) else c for c in data["configurations"]]
        if "headNames" in data and isinstance(data["headNames"], dict):
            data["headNames"] = {int(k): v for k, v in data["headNames"].items()}
        return cls(**data)
