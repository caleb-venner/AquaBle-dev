"""Base entity for AquaBle."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AquaBleCoordinator


class AquaBleEntity(CoordinatorEntity[AquaBleCoordinator]):
    """Base entity for AquaBle devices."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AquaBleCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name="AquaBle Device",
            manufacturer="Chihiros",
        )
        # TODO: Assign proper model from DEVICE_REGISTRY based on config entry
