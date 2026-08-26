"""DataUpdateCoordinator for AquaBle devices."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .commands.generators import generate_handshake_sequence
from .commands.parsers import parse_doser_payload, parse_light_payload
from .const import DEVICE_TYPE_DOSER, DOMAIN
from .domain.doser.status import DoserStatus
from .domain.light.status import LightStatus

_LOGGER = logging.getLogger(__name__)

# Standard Nordic UART Service (NUS)
UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # We write to this (RX on device)
UART_RX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # We read from this (TX on device)


class AquaBleCoordinator(DataUpdateCoordinator[DoserStatus | LightStatus]):
    """Coordinator to manage data updates from AquaBle devices."""

    def __init__(self, hass: HomeAssistant, address: str, device_type: str) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{address}",
            update_interval=timedelta(seconds=60),
        )
        self.address = address
        self.device_type = device_type
        self._msg_id = (0, 0)

    async def _async_update_data(self) -> Any:
        """Fetch data from the device via Bluetooth."""
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if not ble_device:
            raise UpdateFailed(f"Could not find device {self.address}")

        client: BleakClient | None = None
        try:
            client = await establish_connection(
                BleakClient,
                ble_device,
                self.name,
                self._disconnected,
                max_attempts=3,
                use_services_cache=True,
            )
            if not client or not client.is_connected:
                raise UpdateFailed("Failed to connect to device")

            # Prepare to capture the notification
            response_future = asyncio.get_running_loop().create_future()

            # Simple notification handler. In a robust setup with fragmented payloads,
            # we might accumulate bytes. Chihiros statuses often fit in one MTU or are sent rapidly.
            def notification_handler(sender, data: bytearray):
                if not response_future.done():
                    response_future.set_result(data)

            await client.start_notify(UART_RX_UUID, notification_handler)

            # Generate and send the handshake command
            self._msg_id, commands = generate_handshake_sequence(self._msg_id)
            for cmd in commands:
                await client.write_gatt_char(UART_TX_UUID, cmd, response=False)

            # Wait for response (with timeout)
            try:
                payload = await asyncio.wait_for(response_future, timeout=5.0)
            except asyncio.TimeoutError:
                raise UpdateFailed("Timeout waiting for response from device")
            finally:
                await client.stop_notify(UART_RX_UUID)

            # Parse the response using our functional parsers
            if self.device_type == DEVICE_TYPE_DOSER:
                status = parse_doser_payload(bytes(payload))
            else:
                status = parse_light_payload(bytes(payload))

            if not status:
                raise UpdateFailed("Failed to parse status payload")

            return status

        except BleakError as err:
            raise UpdateFailed(f"Bluetooth error: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}")
        finally:
            if client and client.is_connected:
                await client.disconnect()

    def _disconnected(self, client: BleakClient) -> None:
        """Handle bleak disconnect callback."""
        _LOGGER.debug(f"{self.name} disconnected")
