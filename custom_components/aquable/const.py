"""Constants for the AquaBle integration."""

from dataclasses import dataclass

DOMAIN = "aquable"

# Configuration
CONF_DEVICE_TYPE = "device_type"

# Device types
DEVICE_TYPE_DOSER = "doser"
DEVICE_TYPE_LIGHT = "light"


@dataclass
class DeviceModelInfo:
    """Information about a supported device model."""

    name: str
    type: str  # 'doser' or 'light'
    colors: dict[str, int] | None = None


DEVICE_REGISTRY: dict[str, DeviceModelInfo] = {
    "DYDOS": DeviceModelInfo("Dosing Pump", DEVICE_TYPE_DOSER),
    "DYDOSE": DeviceModelInfo("Dosing Pump", DEVICE_TYPE_DOSER),
    "DYWPRO30": DeviceModelInfo(
        "WRGB II Pro", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYWPRO45": DeviceModelInfo(
        "WRGB II Pro", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYWPRO60": DeviceModelInfo(
        "WRGB II Pro", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYWPRO80": DeviceModelInfo(
        "WRGB II Pro", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYWPRO90": DeviceModelInfo(
        "WRGB II Pro", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYWPR120": DeviceModelInfo(
        "WRGB II Pro", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYNA2": DeviceModelInfo("A II", DEVICE_TYPE_LIGHT, {"white": 0}),
    "DYNA2N": DeviceModelInfo("A II", DEVICE_TYPE_LIGHT, {"white": 0}),
    "DYSILN": DeviceModelInfo("WRGB II Slim", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2}),
    "DYSSD": DeviceModelInfo("Z Light TINY", DEVICE_TYPE_LIGHT, {"white": 0, "warm": 1}),
    "DYZSD": DeviceModelInfo("Z Light TINY", DEVICE_TYPE_LIGHT, {"white": 0, "warm": 1}),
    "DYNCRGP": DeviceModelInfo("C II RGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2}),
    "DYNC2N": DeviceModelInfo("C II", DEVICE_TYPE_LIGHT, {"white": 0}),
    "DYDD": DeviceModelInfo("Tiny Terrarium Egg", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1}),
    "DYNWRGB": DeviceModelInfo("WRGB II", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2}),
    "DYNW30": DeviceModelInfo("WRGB II", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2}),
    "DYNW45": DeviceModelInfo("WRGB II", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2}),
    "DYNW60": DeviceModelInfo("WRGB II", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2}),
    "DYNW90": DeviceModelInfo("WRGB II", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2}),
    "DYNW12P": DeviceModelInfo("WRGB II", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2}),
    "DYU550": DeviceModelInfo(
        "Universal WRGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYU600": DeviceModelInfo(
        "Universal WRGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYU700": DeviceModelInfo(
        "Universal WRGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYU800": DeviceModelInfo(
        "Universal WRGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYU920": DeviceModelInfo(
        "Universal WRGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYU1000": DeviceModelInfo(
        "Universal WRGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYU1200": DeviceModelInfo(
        "Universal WRGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYU1500": DeviceModelInfo(
        "Universal WRGB", DEVICE_TYPE_LIGHT, {"red": 0, "green": 1, "blue": 2, "white": 3}
    ),
    "DYLED": DeviceModelInfo(
        "Commander 4", DEVICE_TYPE_LIGHT, {"white": 0, "red": 0, "green": 1, "blue": 2}
    ),
    "DYCOM": DeviceModelInfo(
        "Commander 1", DEVICE_TYPE_LIGHT, {"white": 0, "red": 0, "green": 1, "blue": 2}
    ),
}
