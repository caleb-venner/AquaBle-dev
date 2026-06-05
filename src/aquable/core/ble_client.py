"""Low-level BLE execution wrapper.

Handles raw Bluetooth connections and UART byte transfers.
Completely unaware of domain logic, Chihiros protocols, or what the bytes mean.
"""

import asyncio
import logging

from bleak import BleakClient

logger = logging.getLogger(__name__)

UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

async def execute_ble_commands(
    address: str,
    payloads: list[bytearray],
    wait_for_status: bool = False,
    timeout_seconds: float = 2.5,
    max_retries: int = 3,
) -> list[bytearray]:
    """Connect to a BLE device, send byte payloads, and capture responses.

    Args:
        address: MAC address of the device
        payloads: List of bytearrays to write to the RX characteristic
        wait_for_status: If True, stays connected to collect notifications
        timeout_seconds: Time to wait for notifications after sending payloads
        max_retries: Number of connection/execution attempts

    Returns:
        List of raw bytearray notifications received from the TX characteristic
    """
    for attempt in range(1, max_retries + 1):
        received_packets = []
        
        def notification_handler(*args):
            data = args[-1]
            logger.debug(f"Notification from {address}: {data.hex()}")
            received_packets.append(bytearray(data))

        logger.debug(f"Connecting to {address} (Attempt {attempt}/{max_retries})...")
        
        from ..esphome_proxy import get_proxy_manager
        proxy = get_proxy_manager()
        
        if proxy and proxy.is_running and proxy.client_data:
            from bleak_esphome.backend.client import ESPHomeClient
            device_info = proxy.get_ble_device(address)
            if device_info:
                ble_device, _ = device_info
                client = ESPHomeClient(ble_device, client_data=proxy.client_data)
            else:
                logger.warning(f"Device {address} not yet seen by proxy. Connection may fail without address type.")
                client = ESPHomeClient(address, client_data=proxy.client_data)
        else:
            client = BleakClient(address)

        try:
            if type(client).__name__ == "ESPHomeClient":
                await client.connect(pair=False)
            else:
                await client.connect()
            logger.debug(f"[{address}] Connected.")
            
            tx_char = client.services.get_characteristic(UART_TX_CHAR_UUID) or UART_TX_CHAR_UUID
            rx_char = client.services.get_characteristic(UART_RX_CHAR_UUID) or UART_RX_CHAR_UUID

            await client.start_notify(tx_char, notification_handler)

            for i, payload in enumerate(payloads):
                logger.debug(f"[{address}] Writing payload {i+1}/{len(payloads)}: {payload.hex()}")
                await client.write_gatt_char(rx_char, payload, response=False)
                await asyncio.sleep(0.1)

            if wait_for_status:
                logger.debug(f"[{address}] Waiting {timeout_seconds}s for responses...")
                await asyncio.sleep(timeout_seconds)

            await client.stop_notify(tx_char)
            logger.debug(f"[{address}] Disconnected. Captured {len(received_packets)} packets.")
            return received_packets
            
        except Exception as e:
            logger.error(f"[{address}] BLE execution failed on attempt {attempt}/{max_retries}: {e}")
            if attempt == max_retries:
                raise
            await asyncio.sleep(1.0)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
                
    return []
