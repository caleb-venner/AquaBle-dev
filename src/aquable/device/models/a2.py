"""A2 device Model."""

from ..light import LightDevice


class AII(LightDevice):
    """Chihiros A II device Class."""

    _model_name = "A II"
    _model_codes = ["DYNA2", "DYNA2N"]
    _colors: dict[str, int] = {
        "white": 0,
    }
