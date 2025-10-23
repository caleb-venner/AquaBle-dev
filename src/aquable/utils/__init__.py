"""Utility package for general-purpose helpers.

Provides environment configuration, time/timezone utilities, and serializers.
"""

from .env import get_config_dir, get_env_bool, get_env_float, get_env_int
from .serializers import cached_status_to_dict, serialize_doser_status, serialize_light_status
from .time import get_system_timezone, now_iso

__all__ = [
    # Environment utilities
    "get_config_dir",
    "get_env_bool",
    "get_env_float",
    "get_env_int",
    # Time utilities
    "now_iso",
    "get_system_timezone",
    # Serializers
    "cached_status_to_dict",
    "serialize_doser_status",
    "serialize_light_status",
]
