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
from .domain.light.status import LightSchedule, LightStatus
from .entity import AquaBleEntity

_LOGGER = logging.getLogger(__name__)

# Ordered channel labels for display, indexed by device channel index.
# Derived from DEVICE_REGISTRY color dicts (e.g. {"red": 0, "green": 1, ...}).
_CHANNEL_LABELS: dict[int, str] = {0: "Red", 1: "Green", 2: "Blue", 3: "White"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AquaBle sensors."""
    coordinator: AquaBleCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    if coordinator.device_type == DEVICE_TYPE_DOSER:
        for head_idx in range(1, 5):  # 4-head dosing pump
            entities.append(DoserDailyTotalSensor(coordinator, head_idx))
            entities.append(DoserTargetDoseSensor(coordinator, head_idx))
            entities.append(DoserLifetimeTotalSensor(coordinator, head_idx))
            entities.append(DoserModeSensor(coordinator, head_idx))
            entities.append(DoserScheduleTimeSensor(coordinator, head_idx))

    elif coordinator.device_type == DEVICE_TYPE_LIGHT:
        entities.append(LightScheduleCountSensor(coordinator))
        # Per-schedule sensors — created for up to 24 schedule slots.
        # Sensors for unused slots will show unavailable.
        for sched_idx in range(1, 25):
            entities.append(LightScheduleSunriseSensor(coordinator, sched_idx))
            entities.append(LightScheduleSunsetSensor(coordinator, sched_idx))
            entities.append(LightScheduleRampSensor(coordinator, sched_idx))
            # Per-channel brightness sensors for each schedule slot.
            for ch_idx in range(coordinator.num_channels):
                entities.append(LightScheduleChannelSensor(coordinator, sched_idx, ch_idx))

    async_add_entities(entities)


# ==============================================================================
# DOSER SENSORS
# ==============================================================================


class DoserDailyTotalSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Volume dosed today for a specific pump head (from the 0xFE status packet)."""

    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_daily_total"
        self._attr_name = f"Head {head_idx} Dosed Today"
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


class DoserTargetDoseSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Configured daily target dose for a specific pump head (from tail_targets in 0xFE packet)."""

    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
    _attr_icon = "mdi:water-check"

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_target_dose"
        self._attr_name = f"Head {head_idx} Target Dose"
        self._update_native_value()

    def _update_native_value(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, DoserStatus):
            self._attr_native_value = None
            return
        try:
            self._attr_native_value = float(data.tail_targets[self.head_idx - 1])
        except IndexError:
            self._attr_native_value = None

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()


class DoserLifetimeTotalSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Lifetime volume dispensed for a specific pump head (from the 0x1E status packet)."""

    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:chart-timeline-variant-shimmer"
    _attr_entity_registry_enabled_default = False  # Hidden by default to reduce clutter

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_lifetime_total"
        self._attr_name = f"Head {head_idx} Lifetime Total"
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
    """Current schedule mode of a pump head (daily / 24h / custom / timer / disabled)."""

    _attr_icon = "mdi:cog-outline"

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_mode"
        self._attr_name = f"Head {head_idx} Mode"
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
    """Scheduled daily dose time for a pump head."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: AquaBleCoordinator, head_idx: int) -> None:
        super().__init__(coordinator)
        self.head_idx = head_idx
        self._attr_unique_id = f"{coordinator.address}_head_{head_idx}_schedule_time"
        self._attr_name = f"Head {head_idx} Schedule Time"
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
# LIGHT SENSORS — SUMMARY
# ==============================================================================


class LightScheduleCountSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Number of active auto-program schedules stored on the light device."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: AquaBleCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_schedule_count"
        self._attr_name = "Active Schedules"
        self._update_native_value()

    def _update_native_value(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, LightStatus):
            self._attr_native_value = None
            return
        self._attr_native_value = len(data.schedules)

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()


# ==============================================================================
# LIGHT SENSORS — PER-SCHEDULE
# ==============================================================================


def _get_schedule(data: DoserStatus | LightStatus | None, sched_idx: int) -> LightSchedule | None:
    """Return schedule at 1-based index, or None if data is not a LightStatus or out of range."""
    if not isinstance(data, LightStatus):
        return None
    try:
        return data.schedules[sched_idx - 1]
    except IndexError:
        return None


class LightScheduleSunriseSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sunrise (dawn) time for a specific auto-program schedule."""

    _attr_icon = "mdi:weather-sunset-up"
    # Disabled by default for slots beyond the first two to keep the UI clean.
    # Users can enable them from the entity registry.
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AquaBleCoordinator, sched_idx: int) -> None:
        super().__init__(coordinator)
        self.sched_idx = sched_idx
        self._attr_unique_id = f"{coordinator.address}_schedule_{sched_idx}_sunrise"
        self._attr_name = f"Schedule {sched_idx} Sunrise"
        if sched_idx <= 2:
            self._attr_entity_registry_enabled_default = True
        self._update_native_value()

    def _update_native_value(self) -> None:
        sched = _get_schedule(self.coordinator.data, self.sched_idx)
        self._attr_native_value = sched.sunrise() if sched else None

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()


class LightScheduleSunsetSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Sunset (dusk) time for a specific auto-program schedule."""

    _attr_icon = "mdi:weather-sunset-down"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AquaBleCoordinator, sched_idx: int) -> None:
        super().__init__(coordinator)
        self.sched_idx = sched_idx
        self._attr_unique_id = f"{coordinator.address}_schedule_{sched_idx}_sunset"
        self._attr_name = f"Schedule {sched_idx} Sunset"
        if sched_idx <= 2:
            self._attr_entity_registry_enabled_default = True
        self._update_native_value()

    def _update_native_value(self) -> None:
        sched = _get_schedule(self.coordinator.data, self.sched_idx)
        self._attr_native_value = sched.sunset() if sched else None

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()


class LightScheduleRampSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Ramp-up/ramp-down duration in minutes for a specific auto-program schedule."""

    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:chart-bell-curve"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AquaBleCoordinator, sched_idx: int) -> None:
        super().__init__(coordinator)
        self.sched_idx = sched_idx
        self._attr_unique_id = f"{coordinator.address}_schedule_{sched_idx}_ramp"
        self._attr_name = f"Schedule {sched_idx} Ramp"
        if sched_idx <= 2:
            self._attr_entity_registry_enabled_default = True
        self._update_native_value()

    def _update_native_value(self) -> None:
        sched = _get_schedule(self.coordinator.data, self.sched_idx)
        self._attr_native_value = sched.ramp_up_minutes if sched else None

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()


class LightScheduleChannelSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Peak brightness for one channel of a specific auto-program schedule (0-100)."""

    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:brightness-percent"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AquaBleCoordinator, sched_idx: int, ch_idx: int) -> None:
        super().__init__(coordinator)
        self.sched_idx = sched_idx
        self.ch_idx = ch_idx
        ch_label = _CHANNEL_LABELS.get(ch_idx, f"Ch{ch_idx}")
        self._attr_unique_id = f"{coordinator.address}_schedule_{sched_idx}_ch{ch_idx}_brightness"
        self._attr_name = f"Schedule {sched_idx} {ch_label}"
        if sched_idx <= 2:
            self._attr_entity_registry_enabled_default = True
        self._update_native_value()

    def _update_native_value(self) -> None:
        sched = _get_schedule(self.coordinator.data, self.sched_idx)
        if sched is None:
            self._attr_native_value = None
            return
        try:
            self._attr_native_value = sched.channel_brightness[self.ch_idx]
        except IndexError:
            self._attr_native_value = None

    def _handle_coordinator_update(self) -> None:
        self._update_native_value()
        super()._handle_coordinator_update()
