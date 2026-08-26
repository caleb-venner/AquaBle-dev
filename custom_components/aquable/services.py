"""Custom services (actions) for configuring AquaBle devices."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import AquaBleCoordinator, UART_TX_UUID
from .commands.generators import generate_doser_set_daily_dose_sequence

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_DOSER_SCHEDULE = "doser_set_daily_dose_sequence"

# Schema matches our pure generator: generate_doser_set_daily_dose_sequence
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


async def _async_execute_commands(hass: HomeAssistant, address: str, commands: list[bytearray]) -> None:
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
            # Small buffer to prevent overwhelming the ESPHome proxy or device UART
            await asyncio.sleep(0.1)

        _LOGGER.info("Successfully pushed configuration to %s", address)

    except BleakError as err:
        raise HomeAssistantError(f"Bluetooth error writing to {address}: {err}")
    finally:
        if client and client.is_connected:
            await client.disconnect()


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register custom services for AquaBle."""
    
    if hass.data.get(f"{DOMAIN}_services_registered"):
        return
    hass.data[f"{DOMAIN}_services_registered"] = True

    async def handle_set_doser_schedule(call: ServiceCall) -> None:
        """Handle the service call to set a doser schedule."""
        device_id = call.data["device_id"]
        
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(device_id)
        if not device:
            raise HomeAssistantError(f"Device {device_id} not found in registry")

        coordinator: AquaBleCoordinator | None = None
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                mac_address = identifier[1]
                for coord in hass.data[DOMAIN].values():
                    if coord.address == mac_address:
                        coordinator = coord
                        break
                
        if not coordinator:
            raise HomeAssistantError(f"Active coordinator not found for device {device_id}")

        # 1. Extract and convert arguments
        head_index = call.data["head_index"]
        volume_tenths_ml = int(call.data["volume_ml"] * 10)
        hour = call.data["hour"]
        minute = call.data["minute"]
        weekdays = call.data.get("weekdays")

        # 2. Call the pure functional generator to get the exact bytes
        # We start with msg_id (0, 0) as it's a fresh stateless connection
        _, commands = generate_doser_set_daily_dose_sequence(
            start_msg_id=(0, 0),
            head_index=head_index,
            volume_tenths_ml=volume_tenths_ml,
            hour=hour,
            minute=minute,
            weekdays=weekdays,
        )

        # 3. Connect and execute
        await _async_execute_commands(hass, coordinator.address, commands)
        
        # 4. Trigger an immediate poll so the Dashboard updates to reflect the new schedule
        await coordinator.async_request_refresh()


    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DOSER_SCHEDULE,
        handle_set_doser_schedule,
        schema=DOSER_SCHEDULE_SCHEMA,
    )
