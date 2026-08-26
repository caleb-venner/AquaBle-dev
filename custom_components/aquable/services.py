"""Custom services (actions) for configuring AquaBle devices."""

from __future__ import annotations

import asyncio
import datetime
import logging

import voluptuous as vol
from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .commands import generators
from .const import DOMAIN
from .coordinator import UART_TX_UUID, AquaBleCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_DOSER_SCHEDULE = "doser_set_daily_dose_sequence"
SERVICE_DOSER_MANUAL = "doser_manual_dose"
SERVICE_SET_LIGHT_MANUAL = "light_set_manual_mode"
SERVICE_SET_LIGHT_AUTO = "light_set_auto_schedule"
SERVICE_ENABLE_LIGHT_AUTO = "light_set_mode"
SERVICE_CLEAR_LIGHT_SCHEDULES = "light_clear_schedules"

DOSER_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("head_index"): vol.All(vol.Coerce(int), vol.Range(min=1, max=4)),
        vol.Required("volume_ml"): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
        vol.Required("hour"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Required("minute"): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
        vol.Optional("weekdays"): cv.ensure_list,
    }
)

DOSER_MANUAL_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("head_index"): vol.All(vol.Coerce(int), vol.Range(min=1, max=4)),
        vol.Required("volume_ml"): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
    }
)

LIGHT_MANUAL_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Optional("white", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("red", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("green", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("blue", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)

LIGHT_AUTO_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("sunrise_hour"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Required("sunrise_minute"): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
        vol.Required("sunset_hour"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Required("sunset_minute"): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
        vol.Optional("ramp_up_minutes", default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=180)
        ),
        vol.Optional("white", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("red", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("green", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("blue", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)

LIGHT_MODE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("mode"): vol.In(["auto", "manual", "off"]),
    }
)

LIGHT_CLEAR_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
    }
)


async def _async_execute_commands(
    hass: HomeAssistant, address: str, commands: list[bytearray]
) -> None:
    """Helper to connect to a device and push a list of commands sequentially."""
    ble_device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if not ble_device:
        raise HomeAssistantError(f"Device {address} not found or not in range.")

    _LOGGER.debug("Connecting to %s to write %d commands", address, len(commands))

    client: BleakClient | None = None
    try:
        client = await establish_connection(
            BleakClient,
            ble_device,
            address,
            max_attempts=3,
            use_services_cache=True,
        )
        if not client or not client.is_connected:
            raise HomeAssistantError(f"Failed to connect to device {address}")

        for i, cmd in enumerate(commands):
            _LOGGER.debug("Writing command %d/%d: %s", i + 1, len(commands), cmd.hex())
            await client.write_gatt_char(UART_TX_UUID, cmd, response=False)
            await asyncio.sleep(0.1)

        _LOGGER.info("Successfully pushed configuration to %s", address)

    except BleakError as err:
        raise HomeAssistantError(f"Bluetooth error writing to {address}: {err}")
    finally:
        if client and client.is_connected:
            await client.disconnect()


def _get_coordinator(hass: HomeAssistant, device_id: str) -> AquaBleCoordinator:
    """Resolve a HA device_id to its AquaBleCoordinator."""
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if not device:
        raise HomeAssistantError(f"Device {device_id} not found in registry")

    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            mac_address = identifier[1]
            for coord in hass.data[DOMAIN].values():
                if coord.address == mac_address:
                    return coord

    raise HomeAssistantError(f"Active coordinator not found for device {device_id}")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register custom services for AquaBle."""

    if hass.data.get(f"{DOMAIN}_services_registered"):
        return
    hass.data[f"{DOMAIN}_services_registered"] = True

    async def handle_set_doser_schedule(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call.data["device_id"])
        volume_tenths_ml = int(call.data["volume_ml"] * 10)

        _, commands = generators.generate_doser_set_daily_dose_sequence(
            start_msg_id=(0, 0),
            head_index=call.data["head_index"],
            volume_tenths_ml=volume_tenths_ml,
            hour=call.data["hour"],
            minute=call.data["minute"],
            weekdays=call.data.get("weekdays"),
        )
        await _async_execute_commands(hass, coord.address, commands)
        await coord.async_request_refresh()

    async def handle_doser_manual_dose(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call.data["device_id"])
        volume_tenths_ml = int(call.data["volume_ml"] * 10)

        _, commands = generators.generate_doser_manual_dose_sequence(
            start_msg_id=(0, 0),
            head_index=call.data["head_index"],
            volume_tenths_ml=volume_tenths_ml,
        )
        await _async_execute_commands(hass, coord.address, commands)
        await coord.async_request_refresh()

    async def handle_light_manual_mode(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call.data["device_id"])
        # Map kwargs to channel indices based on domain models (White:0, Red:0, Green:1, Blue:2 depending on light)
        # Using a unified map for WRGB for now:
        colors = {
            0: call.data["red"] or call.data["white"],
            1: call.data["green"],
            2: call.data["blue"],
            3: call.data["white"],
        }
        _, commands = generators.generate_light_set_brightness_sequence((0, 0), colors)
        await _async_execute_commands(hass, coord.address, commands)
        await coord.async_request_refresh()

    async def handle_light_auto_schedule(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call.data["device_id"])
        sunrise = datetime.time(call.data["sunrise_hour"], call.data["sunrise_minute"])
        sunset = datetime.time(call.data["sunset_hour"], call.data["sunset_minute"])
        brightness = (
            call.data["red"] or call.data["white"],
            call.data["green"],
            call.data["blue"],
            call.data["white"],
        )
        ramp_up_minutes = call.data["ramp_up_minutes"]

        _, commands = generators.generate_light_add_auto_setting_sequence(
            (0, 0), sunrise, sunset, brightness, ramp_up_minutes
        )
        await _async_execute_commands(hass, coord.address, commands)
        await coord.async_request_refresh()

    async def handle_light_set_mode(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call.data["device_id"])
        mode = call.data["mode"]
        if mode == "auto":
            _, commands = generators.generate_light_enable_auto_mode_sequence((0, 0))
        elif mode == "off":
            _, commands = generators.generate_light_set_brightness_sequence(
                (0, 0), {0: 0, 1: 0, 2: 0, 3: 0}
            )
        else:  # Manual
            # We don't have a specific "enable manual" command other than setting a color,
            # so we just let light_set_manual_mode handle actual manual setting.
            return

        await _async_execute_commands(hass, coord.address, commands)
        await coord.async_request_refresh()

    async def handle_light_clear_schedules(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call.data["device_id"])
        _, commands = generators.generate_light_clear_schedules_sequence((0, 0))
        await _async_execute_commands(hass, coord.address, commands)
        await coord.async_request_refresh()

    # Register all services
    hass.services.async_register(
        DOMAIN, SERVICE_SET_DOSER_SCHEDULE, handle_set_doser_schedule, schema=DOSER_SCHEDULE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DOSER_MANUAL, handle_doser_manual_dose, schema=DOSER_MANUAL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_LIGHT_MANUAL, handle_light_manual_mode, schema=LIGHT_MANUAL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_LIGHT_AUTO, handle_light_auto_schedule, schema=LIGHT_AUTO_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ENABLE_LIGHT_AUTO, handle_light_set_mode, schema=LIGHT_MODE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_LIGHT_SCHEDULES,
        handle_light_clear_schedules,
        schema=LIGHT_CLEAR_SCHEMA,
    )
