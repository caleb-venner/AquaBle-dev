"""Environment variable utilities."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """Get configuration directory.

    Returns:
        Path to configuration directory, creating it if needed.

    Priority:
        1. AQUA_BLE_CONFIG_DIR environment variable
        2. /config/aquable (Home Assistant add-on)
        3. ~/.aqua-ble (local development)
    """
    # Check for explicit override
    config_dir_override = os.getenv("AQUA_BLE_CONFIG_DIR")
    if config_dir_override:
        config_dir = Path(config_dir_override)
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    # Check if running in Home Assistant add-on (has /config directory)
    ha_config = Path("/config/aquable")
    if Path("/config").exists() and os.getenv("SUPERVISOR_TOKEN"):
        ha_config.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using Home Assistant config directory: {ha_config}")
        return ha_config

    # Default to user home directory for local development
    default_config = Path.home() / ".aqua-ble"
    default_config.mkdir(parents=True, exist_ok=True)
    return default_config


def get_env_bool(name: str, default: bool) -> bool:
    """Get boolean environment variable.

    Args:
        name: Environment variable name
        default: Default value if not found

    Returns:
        Boolean value from environment or default
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    s = raw.strip()
    if s == "":
        return default

    lowered = s.lower()
    if lowered in ("1", "true", "yes", "on"):
        return True
    if lowered in ("0", "false", "no", "off"):
        return False

    try:
        return bool(int(s))
    except ValueError:
        return default


def get_env_float(name: str, default: float) -> float:
    """Get float environment variable.

    Args:
        name: Environment variable name
        default: Default value if not found or invalid

    Returns:
        Float value from environment or default
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        return float(raw)
    except ValueError:
        logger.warning(f"Invalid float value for {name}: '{raw}'. Using default: {default}")
        return default


def get_env_int(name: str, default: int) -> int:
    """Get integer environment variable.

    Args:
        name: Environment variable name
        default: Default value if not found or invalid

    Returns:
        Integer value from environment or default
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        return int(raw)
    except ValueError:
        logger.warning(f"Invalid integer value for {name}: '{raw}'. Using default: {default}")
        return default
