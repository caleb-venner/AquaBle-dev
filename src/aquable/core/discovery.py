"""Device discovery and model identification.

Replaces the OOP `get_model_class_from_name` with a simple functional
registry that maps advertised BLE names to device configurations.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Import proxy manager from legacy code for now, until we refactor it
from ..esphome_proxy import get_proxy_manager

logger = logging.getLogger(__name__)

@dataclass
class DeviceModelInfo:
    """Information about a supported device model."""
    name: str
    type: str  # 'doser' or 'light'
    colors: dict[str, int] | None = None

# Pure functional registry of all known device models and their prefixes
DEVICE_REGISTRY: dict[str, DeviceModelInfo] = {
    "DYDOS": DeviceModelInfo("Dosing Pump", "doser"),
    "DYDOSE": DeviceModelInfo("Dosing Pump", "doser"),
    "DYWPRO30": DeviceModelInfo("WRGB II Pro", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYWPRO45": DeviceModelInfo("WRGB II Pro", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYWPRO60": DeviceModelInfo("WRGB II Pro", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYWPRO80": DeviceModelInfo("WRGB II Pro", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYWPRO90": DeviceModelInfo("WRGB II Pro", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYWPR120": DeviceModelInfo("WRGB II Pro", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYNA2": DeviceModelInfo("A II", "light", {"white": 0}),
    "DYNA2N": DeviceModelInfo("A II", "light", {"white": 0}),
    "DYSILN": DeviceModelInfo("WRGB II Slim", "light", {"red": 0, "green": 1, "blue": 2}),
    "DYSSD": DeviceModelInfo("Z Light TINY", "light", {"white": 0, "warm": 1}),
    "DYZSD": DeviceModelInfo("Z Light TINY", "light", {"white": 0, "warm": 1}),
    "DYNCRGP": DeviceModelInfo("C II RGB", "light", {"red": 0, "green": 1, "blue": 2}),
    "DYNC2N": DeviceModelInfo("C II", "light", {"white": 0}),
    "DYDD": DeviceModelInfo("Tiny Terrarium Egg", "light", {"red": 0, "green": 1}),
    "DYNWRGB": DeviceModelInfo("WRGB II", "light", {"red": 0, "green": 1, "blue": 2}),
    "DYNW30": DeviceModelInfo("WRGB II", "light", {"red": 0, "green": 1, "blue": 2}),
    "DYNW45": DeviceModelInfo("WRGB II", "light", {"red": 0, "green": 1, "blue": 2}),
    "DYNW60": DeviceModelInfo("WRGB II", "light", {"red": 0, "green": 1, "blue": 2}),
    "DYNW90": DeviceModelInfo("WRGB II", "light", {"red": 0, "green": 1, "blue": 2}),
    "DYNW12P": DeviceModelInfo("WRGB II", "light", {"red": 0, "green": 1, "blue": 2}),
    "DYU550": DeviceModelInfo("Universal WRGB", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYU600": DeviceModelInfo("Universal WRGB", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYU700": DeviceModelInfo("Universal WRGB", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYU800": DeviceModelInfo("Universal WRGB", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYU920": DeviceModelInfo("Universal WRGB", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYU1000": DeviceModelInfo("Universal WRGB", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYU1200": DeviceModelInfo("Universal WRGB", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYU1500": DeviceModelInfo("Universal WRGB", "light", {"red": 0, "green": 1, "blue": 2, "white": 3}),
    "DYLED": DeviceModelInfo("Commander 4", "light", {"white": 0, "red": 0, "green": 1, "blue": 2}),
    "DYCOM": DeviceModelInfo("Commander 1", "light", {"white": 0, "red": 0, "green": 1, "blue": 2}),
}


def get_ble_device_name(ble_device: BLEDevice, adv_data: AdvertisementData | None = None) -> str | None:
    """Return the best-available device name from Bleak BLEDevice and AdvertisementData."""
    candidates: list[str | None] = [getattr(ble_device, "name", None)]

    if adv_data:
        candidates.append(getattr(adv_data, "local_name", None))

    metadata = getattr(ble_device, "metadata", None)
    if isinstance(metadata, dict):
        candidates.extend([
            metadata.get("local_name"),
            metadata.get("name"),
            metadata.get("alias"),
            metadata.get("device_name"),
        ])

    details = getattr(ble_device, "details", None)
    if isinstance(details, dict):
        candidates.extend([
            details.get("Name"),
            details.get("Alias"),
            details.get("local_name"),
        ])
        props = details.get("props")
        if isinstance(props, dict):
            candidates.extend([
                props.get("Name"),
                props.get("Alias"),
                props.get("LocalName"),
            ])

    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = candidate.strip()
            if normalized:
                return normalized
    return None


def match_device_model(device_name: str) -> tuple[str, DeviceModelInfo] | None:
    """Find the best matching model from the registry for a given device name."""
    normalized_name = device_name.strip().upper()
    compact_name = re.sub(r"[^A-Z0-9]", "", normalized_name)

    # Prefer longest model codes first so prefixes do not collide.
    for model_code in sorted(DEVICE_REGISTRY.keys(), key=len, reverse=True):
        if normalized_name.startswith(model_code) or model_code in normalized_name:
            return model_code, DEVICE_REGISTRY[model_code]
        if compact_name.startswith(model_code) or model_code in compact_name:
            return model_code, DEVICE_REGISTRY[model_code]
            
    return None


async def discover_devices(
    timeout: float = 5.0, 
    use_local: bool = True, 
    use_esphome: bool = True
) -> list[dict[str, Any]]:
    """Scan for devices using local Bluetooth and/or ESPHome Proxies.
    
    Returns a list of dictionaries with normalized device information.
    """
    discovered_devices = {}
    
    def process_device(device: BLEDevice, adv_data: AdvertisementData | None, source: str):
        name = get_ble_device_name(device, adv_data)
        if not name:
            return
            
        match = match_device_model(name)
        if not match:
            return
            
        model_code, model_info = match
        address = device.address.upper()
        
        if address not in discovered_devices:
            discovered_devices[address] = {
                "id": address,
                "address": address,
                "name": name,
                "model_code": model_code,
                "model_name": model_info.name,
                "product": model_info.name,
                "type": model_info.type,
                "device_type": model_info.type,
                "colors": model_info.colors,
                "rssi": adv_data.rssi if adv_data else None,
                "source": source,
            }
            logger.info(f"Discovered supported device: {address} ({name}) via {source}")

    if use_esphome:
        proxy = get_proxy_manager()
        if proxy and proxy.is_running:
            all_devices = proxy.get_all_devices()
            logger.info(f"Scanning ESPHome live cache ({len(all_devices)} devices active)")
            
            for dev, adv in all_devices:
                logger.info(f"Found on Proxy: {dev.address} name='{dev.name}' adv_name='{adv.local_name if adv else None}'")
                process_device(dev, adv, "esphome")
                
    if use_local:
        try:
            try:
                scanned = await BleakScanner.discover(timeout=timeout, return_adv=True)
                for dev, adv in scanned.values():
                    process_device(dev, adv, "local")
            except TypeError:
                scanned = await BleakScanner.discover(timeout=timeout)
                for dev in scanned:
                    process_device(dev, None, "local")
        except Exception as e:
            logger.warning(f"Local Bluetooth scan failed: {e}")
            
    return list(discovered_devices.values())
