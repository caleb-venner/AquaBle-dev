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

from .commands.generators import (
    generate_doser_status_sequence,
    generate_handshake_sequence,
)
from .commands.parsers import parse_doser_payload, parse_light_payload
from .config_flow import match_device_model
from .const import DEVICE_TYPE_DOSER, DOMAIN
from .domain.doser.status import DoserStatus
from .domain.light.status import LightStatus

_LOGGER = logging.getLogger(__name__)

# Standard Nordic UART Service (NUS)
UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # We write to this (RX on device)
UART_RX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # We read from this (TX on device)

# Time to wait after sending commands to collect all incoming notification packets.
# Doser sends 3 packets (0x0A ack, 0xFE status, 0x1E lifetime totals).
_NOTIFICATION_COLLECT_WINDOW = 3.5


def _process_doser_packets(packets: list[bytes]) -> DoserStatus | None:
    """Merge all doser notification packets into a single status object.

    Dosers send distinct packets per status request:
    - Mode 0xFE: head schedule data and daily dosed amounts.
    - Mode 0x1E: lifetime dose totals (one per head).

    Both are parsed and merged via DoserStatus.update_from().
    """
    final_status: DoserStatus | None = None
    for packet in packets:
        parsed = parse_doser_payload(packet)
        if parsed is None:
            continue
        if final_status is None:
            final_status = parsed
        else:
            final_status.update_from(parsed)
    return final_status


def _process_light_packets(packets: list[bytes], num_channels: int = 0) -> LightStatus | None:
    """Return the first valid light status parsed from a packet list.

    Lights respond with a single 0xFE status payload (plus an initial
    0x0A handshake ack which the parser discards automatically).

    Args:
        packets: Raw BLE notification bytes received during the collection window.
        num_channels: Number of brightness channels for this device model.
            When > 0, the body is decoded as 13-byte schedule blocks.
    """
    for packet in packets:
        parsed = parse_light_payload(packet, num_channels=num_channels)
        if parsed is not None:
            return parsed
    return None


class AquaBleCoordinator(DataUpdateCoordinator[DoserStatus | LightStatus]):
    """Coordinator to manage data updates from AquaBle devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        device_type: str,
        device_name: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{address}",
            update_interval=timedelta(minutes=5),
        )
        self.address = address
        self.device_type = device_type
        self._msg_id = (0, 0)

        # Resolve channel count from DEVICE_REGISTRY using the BLE advertisement name.
        # Used by parse_light_payload to decode schedule blocks correctly.
        self.num_channels: int = 0
        match = match_device_model(device_name)
        if match:
            _, model_info = match
            if model_info.colors:
                # Unique channel indices (some devices share an index between keys)
                self.num_channels = len(set(model_info.colors.values()))

    async def _async_update_data(self) -> Any:
        """Fetch data from the device via Bluetooth.

        Mirrors the standalone ble_client.execute_ble_commands() approach:
        1. Connect.
        2. Subscribe to notifications.
        3. Send the handshake command(s).
        4. Collect ALL incoming notification packets for a fixed window.
        5. Disconnect.
        6. Process the full packet list to build the merged status object.
        """
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

            # Collect all raw packets received during the window.
            received_packets: list[bytes] = []

            def notification_handler(sender: Any, data: bytearray) -> None:
                _LOGGER.debug(
                    "%s: Notification received (%d bytes): %s",
                    self.name,
                    len(data),
                    data.hex(),
                )
                received_packets.append(bytes(data))

            await client.start_notify(UART_RX_UUID, notification_handler)

            # Generate and send the status request sequence
            if self.device_type == DEVICE_TYPE_DOSER:
                self._msg_id, commands = generate_doser_status_sequence(self._msg_id)
            else:
                self._msg_id, commands = generate_handshake_sequence(self._msg_id)

            for cmd in commands:
                await client.write_gatt_char(UART_TX_UUID, cmd, response=False)
                await asyncio.sleep(0.3)

            # Wait the full collection window so all response packets arrive.
            _LOGGER.debug(
                "%s: Waiting %.1fs for notification window...",
                self.name,
                _NOTIFICATION_COLLECT_WINDOW,
            )
            await asyncio.sleep(_NOTIFICATION_COLLECT_WINDOW)

            try:
                await client.stop_notify(UART_RX_UUID)
            except Exception:
                pass

        except BleakError as err:
            raise UpdateFailed(f"Bluetooth error: {err}") from err
        except Exception as err:
            if isinstance(err, UpdateFailed):
                raise
            raise UpdateFailed(f"Unexpected error: {err}") from err
        finally:
            if client and client.is_connected:
                await client.disconnect()

        _LOGGER.debug(
            "%s: Captured %d notification packet(s) from %s",
            self.name,
            len(received_packets),
            self.address,
        )

        # Process the collected packets outside the BLE connection context.
        if self.device_type == DEVICE_TYPE_DOSER:
            status = _process_doser_packets(received_packets)
        else:
            status = _process_light_packets(received_packets, num_channels=self.num_channels)

        if status is None:
            raise UpdateFailed(
                f"No valid status parsed from {len(received_packets)} packet(s) "
                f"received from {self.address}"
            )

        return status

    def _disconnected(self, client: BleakClient) -> None:
        """Handle bleak disconnect callback."""
        _LOGGER.debug("%s disconnected", self.name)
