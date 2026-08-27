"""Sensor platform for AquaBle."""

from __future__ import annotations

import datetime
import logging
from typing import Any

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
        entities.append(LightActiveSchedulesSensor(coordinator))
        entities.append(LightHardwareSyncSensor(coordinator))
        for ch_idx in range(coordinator.num_channels):
            entities.append(LightLiveChannelSensor(coordinator, ch_idx))

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
# LIGHT SENSORS
# ==============================================================================


class LightActiveSchedulesSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Number of active auto-program schedules configured on the light device."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: AquaBleCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_active_schedules"
        self._attr_name = "Active Schedules"
        self._update_state()

    def _update_state(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, LightStatus):
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return
        self._attr_native_value = len(data.schedules)
        self._attr_extra_state_attributes = {
            "schedules": [
                {
                    "slot": idx + 1,
                    "sunrise": sched.sunrise(),
                    "sunset": sched.sunset(),
                    "ramp_up_minutes": sched.ramp_up_minutes,
                    "weekdays": sched.weekdays(),
                    "channel_brightness": sched.channel_brightness,
                }
                for idx, sched in enumerate(data.schedules)
            ]
        }

    def _handle_coordinator_update(self) -> None:
        self._update_state()
        super()._handle_coordinator_update()


class LightHardwareSyncSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Reports whether device clock and hardware curve are verified and synchronised."""

    _attr_icon = "mdi:sync"

    def __init__(self, coordinator: AquaBleCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_hardware_sync"
        self._attr_name = "Hardware Sync"
        self._update_state()

    def _update_state(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, LightStatus) or data.hour is None:
            self._attr_native_value = "unavailable"
            self._attr_extra_state_attributes = {}
            return

        self._attr_native_value = "synced"
        self._attr_extra_state_attributes: dict[str, Any] = {
            "device_time": (
                f"{data.hour:02d}:{data.minute:02d}"
                if data.minute is not None
                else None
            ),
            "device_weekday": data.weekday,
            "response_mode": (
                f"0x{data.response_mode:02X}"
                if data.response_mode is not None
                else None
            ),
        }

    def _handle_coordinator_update(self) -> None:
        self._update_state()
        super()._handle_coordinator_update()


def _calculate_channel_brightness(
    schedules: list[LightSchedule],
    ch_idx: int,
    now: datetime.datetime,
) -> int:
    """Interpolate real-time brightness (0-100%) for a given channel based on active schedules."""
    max_brightness = 0
    now_minutes = now.hour * 60 + now.minute + now.second / 60.0
    # Python weekday(): Monday is 0, Sunday is 6.
    # Chihiros weekday mask: Monday is bit 6 (0x40), Sunday is bit 0 (0x01).
    day_bit = 1 << (6 - now.weekday())

    for sched in schedules:
        if not (sched.weekday_mask & day_bit):
            continue

        sunrise_minutes = sched.sunrise_hour * 60 + sched.sunrise_minute
        sunset_minutes = sched.sunset_hour * 60 + sched.sunset_minute

        if sunset_minutes <= sunrise_minutes:
            continue

        if now_minutes < sunrise_minutes or now_minutes >= sunset_minutes:
            continue

        peak = (
            sched.channel_brightness[ch_idx]
            if ch_idx < len(sched.channel_brightness)
            else 0
        )
        if peak <= 0:
            continue

        ramp = sched.ramp_up_minutes
        if ramp > 0 and now_minutes < (sunrise_minutes + ramp):
            fraction = (now_minutes - sunrise_minutes) / ramp
            brightness = int(round(peak * fraction))
        elif ramp > 0 and now_minutes > (sunset_minutes - ramp):
            fraction = (sunset_minutes - now_minutes) / ramp
            brightness = int(round(peak * fraction))
        else:
            brightness = peak

        if brightness > max_brightness:
            max_brightness = brightness

    return min(100, max(0, max_brightness))


class LightLiveChannelSensor(AquaBleEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Calculated live brightness for a specific channel based on active schedules."""

    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:brightness-percent"

    def __init__(self, coordinator: AquaBleCoordinator, ch_idx: int) -> None:
        super().__init__(coordinator)
        self.ch_idx = ch_idx
        ch_label = _CHANNEL_LABELS.get(ch_idx, f"Channel {ch_idx}")
        self._attr_unique_id = f"{coordinator.address}_channel_{ch_idx}_live_brightness"
        self._attr_name = f"{ch_label} Brightness"
        self._update_state()

    def _update_state(self) -> None:
        data = self.coordinator.data
        if not isinstance(data, LightStatus):
            self._attr_native_value = None
            return
        now = datetime.datetime.now()
        self._attr_native_value = _calculate_channel_brightness(
            data.schedules, self.ch_idx, now
        )

    def _handle_coordinator_update(self) -> None:
        self._update_state()
        super()._handle_coordinator_update()
