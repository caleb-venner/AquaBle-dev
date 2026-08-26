"""Sensor platform for AquaBle."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_DOSER, DEVICE_TYPE_LIGHT, DOMAIN
from .coordinator import AquaBleCoordinator
from .domain.doser.status import DoserStatus
from .entity import AquaBleEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AquaBle sensors."""
    coordinator: AquaBleCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    if coordinator.device_type == DEVICE_TYPE_DOSER:
        # Example: Create a sensor for each pump head's daily dose total
        for head_idx in range(1, 5):  # Assuming 4 heads
            entities.append(DoserDailyTotalSensor(coordinator, head_idx))

    elif coordinator.device_type == DEVICE_TYPE_LIGHT:
        # Example: Create a sensor for the current light mode
        entities.append(LightModeSensor(coordinator))

    async_add_entities(entities)


class DoserDailyTotalSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sensor tracking the daily dosed volume for a specific pump head."""

    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_daily_total"
        self._attr_name = f"Pump {head_idx} Daily Total"
        self._update_native_value()

    def _update_native_value(self) -> None:
        """Update the daily total from the DoserStatus dataclass."""
        data = self.coordinator.data
        if not isinstance(data, DoserStatus):
            self._attr_native_value = None
            return

        self._attr_native_value = next(
            (
                head.dosed_tenths_ml / 10
                for index, head in enumerate(data.heads, start=1)
                if index == self.head_idx
            ),
            None,
        )

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator updates."""
        self._update_native_value()
        super()._handle_coordinator_update()


class LightModeSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sensor tracking the current mode of the light (Auto/Manual)."""

    def __init__(self, coordinator: AquaBleCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_current_mode"
        self._attr_name = "Current Mode"
        self._update_native_value()

    def _update_native_value(self) -> None:
        """Update the current mode from the LightStatus dataclass."""
        # LightStatus currently does not expose an Auto/Manual mode field.
        self._attr_native_value = None

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator updates."""
        self._update_native_value()
        super()._handle_coordinator_update()
