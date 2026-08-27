"""The AquaBle integration."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .card_resources import (
    async_register_card_resource,
    async_unregister_card_resources,
)
from .const import CONF_DEVICE_TYPE, DOMAIN
from .coordinator import AquaBleCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

_FRONTEND_DIR = Path(__file__).parent / "frontend"


def _compute_frontend_hash(files: list[Path]) -> str:
    """Short content hash for cache busting. Order-independent."""
    h = hashlib.sha256()
    for f in sorted(files):
        if f.is_file():
            h.update(f.read_bytes())
    return h.hexdigest()[:8]


_FRONTEND_HASH = (
    _compute_frontend_hash(list(_FRONTEND_DIR.glob("*.js")))
    if _FRONTEND_DIR.exists()
    else "0"
)
_CARD_BASE_URL = f"/{DOMAIN}_panel/"
_PANEL_URL = f"/{DOMAIN}_panel/{_FRONTEND_HASH}"
_CARD_JS_URL = f"{_PANEL_URL}/aquable-light-card.js"
_DOSER_CARD_JS_URL = f"{_PANEL_URL}/aquable-doser-card.js"
_ALL_CARD_URLS = [_CARD_JS_URL, _DOSER_CARD_JS_URL]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the Lovelace card resource once per HA session."""
    if _FRONTEND_DIR.exists():
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    _PANEL_URL,
                    str(_FRONTEND_DIR),
                    cache_headers=False,
                )
            ]
        )
    for card_url in _ALL_CARD_URLS:
        await async_register_card_resource(hass, _CARD_BASE_URL, card_url)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AquaBle from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    address = entry.data[CONF_ADDRESS]
    device_type = entry.data[CONF_DEVICE_TYPE]
    device_name: str | None = entry.data.get(CONF_NAME)

    _LOGGER.debug("Setting up AquaBle device: %s (%s)", address, device_type)

    coordinator = AquaBleCoordinator(
        hass, address, device_type, device_name=device_name, entry=entry
    )

    # Perform the first fetch to ensure the device is online and we get its state
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register our custom configuration services (Actions)
    await async_setup_services(hass)

    # Idempotent: re-establish card resources whenever an entry is added
    for card_url in _ALL_CARD_URLS:
        await async_register_card_resource(hass, _CARD_BASE_URL, card_url)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry.

    When the last entry is removed, clean up the card Lovelace resources.
    """
    remaining = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if not remaining:
        await async_unregister_card_resources(hass, _ALL_CARD_URLS)
