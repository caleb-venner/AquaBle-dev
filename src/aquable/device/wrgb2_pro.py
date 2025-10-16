"""WRGB II Pro device Model."""

from .light_device import LightDevice


class WRGBIIPro(LightDevice):
    """Chihiros WRGB II Pro device Class."""

    _model_name = "WRGB II Pro"
    _model_codes = [
        "DYWPRO30",
        "DYWPRO45",
        "DYWPRO60",
        "DYWPRO80",
        "DYWPRO90",
        "DYWPR120",
    ]
    _colors: dict[str, int] = {
        "red": 0,
        "green": 1,
        "blue": 2,
        "white": 3,
    }
