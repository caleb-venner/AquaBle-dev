"""Base entity for AquaBle."""

from __future__ import annotations

from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import match_device_model
from .const import DOMAIN
from .coordinator import AquaBleCoordinator


class AquaBleEntity(CoordinatorEntity[AquaBleCoordinator]):
    """Base entity for AquaBle devices."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AquaBleCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        # Resolve friendly model name from the BLE device name stored in config.
        device_name: str | None = None
        model_name: str | None = None
        entry = coordinator.config_entry
        if entry is not None:
            device_name = entry.data.get(CONF_NAME)
            match = match_device_model(device_name)
            if match:
                _, model_info = match
                model_name = model_info.name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=device_name or coordinator.address,
            manufacturer="Chihiros",
            model=model_name,
        )
