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
from .domain.light.status import LightStatus
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
        # Create sensors for each pump head
        for head_idx in range(1, 5):  # Assuming 4 heads
            entities.append(DoserDailyTotalSensor(coordinator, head_idx))
            entities.append(DoserLifetimeTotalSensor(coordinator, head_idx))
            entities.append(DoserModeSensor(coordinator, head_idx))
            entities.append(DoserScheduleTimeSensor(coordinator, head_idx))

    elif coordinator.device_type == DEVICE_TYPE_LIGHT:
        entities.append(LightScheduleCountSensor(coordinator))

    async_add_entities(entities)


# ==============================================================================
# DOSER SENSORS
# ==============================================================================


class DoserDailyTotalSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sensor tracking the daily dosed volume for a specific pump head."""

    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_daily_total"
        self._attr_name = f"Pump {head_idx} Daily Total"
        self._attr_icon = "mdi:water-pump"
        self._update_native_value()

    def _update_native_value(self) -> None:
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
        self._update_native_value()
        super()._handle_coordinator_update()


class DoserLifetimeTotalSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sensor tracking the lifetime dosed volume for a specific pump head."""

    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_registry_enabled_default = False  # Hide by default to reduce UI clutter

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_lifetime_total"
        self._attr_name = f"Pump {head_idx} Lifetime Total"
        self._attr_icon = "mdi:chart-timeline-variant-shimmer"
        self._update_native_value()

    def _update_native_value(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, DoserStatus) or not data.lifetime_totals_tenths_ml:
            self._attr_native_value = None
            return

        try:
            self._attr_native_value = data.lifetime_totals_tenths_ml[self.head_idx - 1] / 10
        except IndexError:
            self._attr_native_value = None

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()


class DoserModeSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sensor tracking the current configuration mode of a pump head."""

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_mode"
        self._attr_name = f"Pump {head_idx} Mode"
        self._attr_icon = "mdi:cog-outline"
        self._update_native_value()

    def _update_native_value(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, DoserStatus):
            self._attr_native_value = None
            return

        self._attr_native_value = next(
            (
                head.mode_label().capitalize()
                for index, head in enumerate(data.heads, start=1)
                if index == self.head_idx
            ),
            None,
        )

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()


class DoserScheduleTimeSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sensor tracking the scheduled time of a pump head."""

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_schedule_time"
        self._attr_name = f"Pump {head_idx} Scheduled Time"
        self._attr_icon = "mdi:clock-outline"
        self._update_native_value()

    def _update_native_value(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, DoserStatus):
            self._attr_native_value = None
            return

        self._attr_native_value = next(
            (
                f"{head.hour:02d}:{head.minute:02d}"
                for index, head in enumerate(data.heads, start=1)
                if index == self.head_idx
            ),
            None,
        )

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()


# ==============================================================================
# LIGHT SENSORS
# ==============================================================================


class LightScheduleCountSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sensor tracking the number of active schedule keyframes on the light."""

    def __init__(self, coordinator: AquaBleCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_schedule_count"
        self._attr_name = "Active Schedules"
        self._attr_icon = "mdi:calendar-clock"
        self._update_native_value()

    def _update_native_value(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, LightStatus):
            self._attr_native_value = None
            return

        self._attr_native_value = len(data.keyframes)

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()
