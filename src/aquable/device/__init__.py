"""Module defining Chihiros devices."""

import inspect
import sys
from typing import Type

from bleak import BleakScanner

from ..errors import DeviceNotFoundError
from .base_device import BaseDevice
from .doser import Doser
from .light import LightDevice
from .models import (
    AII,
    CII,
    CIIRGB,
    WRGBII,
    Commander1,
    Commander4,
    TinyTerrariumEgg,
    UniversalWRGB,
    WRGBIIPro,
    WRGBIISlim,
    ZLightTiny,
)

CODE2MODEL = {}
for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj) and issubclass(obj, BaseDevice):
        for model_code in obj._model_codes:
            CODE2MODEL[model_code] = obj


def get_model_class_from_name(
    device_name: str,
) -> Type[BaseDevice]:
    """Get device class name from device name."""
    model_class = CODE2MODEL.get(device_name[:-12])
    if model_class is None:
        raise DeviceNotFoundError(device_name, details={"reason": "Device model code not found"})
    return model_class


async def get_device_from_address(device_address: str) -> BaseDevice:
    """Get BLEDevice object from mac address."""
    ble_dev = await BleakScanner.find_device_by_address(device_address)
    if ble_dev and ble_dev.name is not None:
        model_class = get_model_class_from_name(ble_dev.name)
        dev: BaseDevice = model_class(ble_dev)
        return dev

    raise DeviceNotFoundError(device_address)


__all__ = [
    "ZLightTiny",
    "TinyTerrariumEgg",
    "AII",
    "Commander1",
    "Commander4",
    "Doser",
    "WRGBII",
    "WRGBIIPro",
    "WRGBIISlim",
    "CII",
    "CIIRGB",
    "UniversalWRGB",
    "BaseDevice",
    "LightDevice",
    "CODE2MODEL",
    "get_device_from_address",
    "get_model_class_from_name",
]
