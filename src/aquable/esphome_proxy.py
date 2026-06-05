"""ESPHome Bluetooth proxy support for AquaBle.

When an ESPHome Bluetooth proxy host is configured (AQUA_BLE_ESPHOME_HOST),
this module connects to its API, subscribes to BLE advertisement streaming,
and provides ESPHomeClient instances so GATT connections are routed through
the proxy instead of the local BlueZ stack.

This is the correct path for Home Assistant setups that use an ESPHome
Bluetooth proxy rather than a USB Bluetooth adapter directly on the host.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from aioesphomeapi import BluetoothLEAdvertisement
from aioesphomeapi.client import APIClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak_esphome.backend.client import ESPHomeClientData
from bleak_esphome.backend.device import ESPHomeBluetoothDevice

logger = logging.getLogger("aquable.esphome_proxy")


def _int_to_mac(address: int) -> str:
    """Convert a 48-bit integer BLE address to a colon-separated MAC string."""
    return ":".join(f"{b:02X}" for b in address.to_bytes(6, "big"))


def _adv_to_ble_device(adv: BluetoothLEAdvertisement, source: str) -> BLEDevice:
    """Build a bleak BLEDevice from an ESPHome advertisement.

    The ``details`` dict must include ``address_type`` and ``source`` because
    ESPHomeClient reads them when establishing the GATT connection.
    """
    mac = _int_to_mac(adv.address)
    return BLEDevice(
        mac,
        adv.name or mac,
        details={"address_type": adv.address_type, "source": source},
        rssi=adv.rssi,
    )


def _adv_to_advertisement_data(adv: BluetoothLEAdvertisement) -> AdvertisementData:
    """Build bleak AdvertisementData from an ESPHome advertisement."""
    return AdvertisementData(
        local_name=adv.name or None,
        manufacturer_data={k: bytes(v) for k, v in adv.manufacturer_data.items()},
        service_data={k: bytes(v) for k, v in adv.service_data.items()},
        service_uuids=list(adv.service_uuids),
        platform_data=(),
        tx_power=None,
        rssi=adv.rssi,
    )


class ESPHomeProxyManager:
    """Manages a connection to one ESPHome Bluetooth proxy.

    On ``start()``:
    - Connects to the ESPHome device API (port 6053)
    - Subscribes to BLE advertisement streaming
    - Maintains a live cache of (BLEDevice, AdvertisementData) keyed by address
    - Builds an ESPHomeClientData instance usable by ESPHomeClient

    On ``stop()``:
    - Unsubscribes, disconnects, and clears the cache
    """

    def __init__(self, host: str, password: str = "", noise_psk: str = "") -> None:
        self._host = host
        self._password = password or None
        self._noise_psk = noise_psk or None
        self._api_client: APIClient | None = None
        self._bluetooth_device: ESPHomeBluetoothDevice | None = None
        self._client_data: ESPHomeClientData | None = None
        # address.upper() -> (BLEDevice, AdvertisementData)
        self._device_cache: dict[str, tuple[BLEDevice, AdvertisementData]] = {}
        self._unsub_adv: Callable[[], None] | None = None
        self._unsub_conn: Callable[[], None] | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def client_data(self) -> ESPHomeClientData | None:
        return self._client_data

    async def start(self) -> None:
        """Connect to the ESPHome proxy API and begin advertisement streaming."""
        host = self._host
        port = 6053
        if ":" in host:
            try:
                host, port_str = host.rsplit(":", 1)
                port = int(port_str)
            except (ValueError, TypeError):
                # Fall back to default if parsing fails
                host = self._host
                port = 6053

        logger.info("Connecting to ESPHome Bluetooth proxy at %s:%d", host, port)
        api = APIClient(
            address=host,
            port=port,
            password=self._password,
            noise_psk=self._noise_psk,
            client_info="AquaBle",
        )
        try:
            await api.connect(login=True)
        except Exception as exc:
            logger.error("Failed to connect to ESPHome proxy at %s: %s", self._host, exc)
            raise

        try:
            device_info = await api.device_info()
        except Exception as exc:
            logger.error("Failed to get device info from ESPHome proxy: %s", exc)
            try:
                await api.disconnect()
            except Exception:
                pass
            raise

        source = device_info.bluetooth_mac_address or device_info.mac_address
        logger.info("Connected to ESPHome proxy: %s (BT MAC: %s)", device_info.name, source)

        bluetooth_device = ESPHomeBluetoothDevice(
            name=device_info.name,
            mac_address=source,
            available=True,
        )

        # Subscribe to connection-free-slot updates so ESPHomeClient knows when
        # it can open a new GATT connection.
        self._unsub_conn = api.subscribe_bluetooth_connections_free(
            bluetooth_device.async_update_ble_connection_limits
        )

        # Subscribe to scanner state (required by some firmware before advertisements start)
        try:
            self._unsub_state = api.subscribe_bluetooth_scanner_state(
                lambda state: logger.debug("Scanner state update: %s", state)
            )
        except Exception:
            self._unsub_state = None

        # Subscribe to BLE advertisements to keep the device cache fresh.
        self._unsub_adv = api.subscribe_bluetooth_le_advertisements(self._on_advertisement)
        
        try:
            self._unsub_raw_adv = api.subscribe_bluetooth_le_raw_advertisements(self._on_raw_advertisements)
        except Exception as e:
            logger.debug("Raw advertisements not supported by this ESPHome proxy: %s", e)

        try:
            from aioesphomeapi import BluetoothScannerMode
            api.bluetooth_scanner_set_mode(BluetoothScannerMode.ACTIVE)
            logger.info("ESPHome Bluetooth scanner set to ACTIVE mode")
        except Exception as e:
            logger.warning("Failed to set Bluetooth scanner mode to ACTIVE. It might not be supported or is already active: %s", e)

        if api.api_version is None:
            raise RuntimeError("ESPHome API version unavailable after connect")

        import contextlib
        class DummyScanner:
            @contextlib.contextmanager
            def connecting(self):
                yield

        self._client_data = ESPHomeClientData(
            bluetooth_device=bluetooth_device,
            client=api,
            device_info=device_info,
            api_version=api.api_version,
            title=device_info.name,
            scanner=DummyScanner(),
            disconnect_callbacks=set(),
        )
        self._api_client = api
        self._bluetooth_device = bluetooth_device
        self._running = True
        logger.info("ESPHome proxy ready; BLE advertisement streaming active")

    async def stop(self) -> None:
        """Unsubscribe, disconnect, and clean up."""
        self._running = False
        for unsub in (self._unsub_adv, getattr(self, '_unsub_raw_adv', None), self._unsub_conn):
            if unsub is not None:
                try:
                    unsub()
                except Exception:
                    pass
        self._unsub_adv = None
        self._unsub_raw_adv = None
        self._unsub_conn = None
        if self._api_client is not None:
            try:
                await self._api_client.disconnect()
            except Exception:
                pass
            self._api_client = None
        self._client_data = None
        self._bluetooth_device = None
        self._device_cache.clear()
        logger.info("ESPHome proxy disconnected")

    def _on_advertisement(self, adv: BluetoothLEAdvertisement) -> None:
        """Update the device cache from each incoming advertisement."""
        ble_device = _adv_to_ble_device(adv, self._bluetooth_device.mac_address)
        adv_data = _adv_to_advertisement_data(adv)
        logger.debug("Received advertisement from ESPHome: %s (%s) RSSI: %d", ble_device.address, adv.name or "No Name", adv.rssi)
        self._device_cache[ble_device.address.upper()] = (ble_device, adv_data)

    def _on_raw_advertisements(self, response: Any) -> None:
        """Process modern ESPHome raw advertisements."""
        logger.debug("RAW ADV BATCH: %d advs", len(response.advertisements))
        try:
            from bleak.backends.device import BLEDevice
            from bleak.backends.scanner import AdvertisementData
            from bluetooth_data_tools import parse_advertisement_data
            
            for raw_adv in response.advertisements:
                address = _int_to_mac(raw_adv.address)
                parsed = parse_advertisement_data([raw_adv.data])
                
                ble_device = BLEDevice(
                    address=address,
                    name=parsed.local_name or address,
                    details={"address_type": raw_adv.address_type, "source": self._bluetooth_device.mac_address},
                    rssi=raw_adv.rssi,
                )
                
                adv_data = AdvertisementData(
                    local_name=parsed.local_name,
                    manufacturer_data=parsed.manufacturer_data or {},
                    service_data=parsed.service_data or {},
                    service_uuids=parsed.service_uuids or [],
                    tx_power=parsed.tx_power or 0,
                    rssi=raw_adv.rssi,
                    platform_data=(),
                )
                
                logger.debug("Received raw adv from ESPHome: %s (%s) RSSI: %d", ble_device.address, parsed.local_name or "No Name", adv_data.rssi)
                self._device_cache[address.upper()] = (ble_device, adv_data)
        except Exception as e:
            logger.error("Error processing raw advertisement: %s", e)

    def get_ble_device(self, address: str) -> tuple[BLEDevice, AdvertisementData] | None:
        """Return a cached (BLEDevice, AdvertisementData) by MAC address."""
        return self._device_cache.get(address.upper())

    def get_all_devices(self) -> list[tuple[BLEDevice, AdvertisementData]]:
        """Return all cached devices seen since start."""
        return list(self._device_cache.values())


# ---------------------------------------------------------------------------
# Module-level singleton — set by BLEService on startup
# ---------------------------------------------------------------------------

_proxy_manager: ESPHomeProxyManager | None = None


def get_proxy_manager() -> ESPHomeProxyManager | None:
    return _proxy_manager


def set_proxy_manager(manager: ESPHomeProxyManager | None) -> None:
    global _proxy_manager
    _proxy_manager = manager
