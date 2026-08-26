"""The AquaBle integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_TYPE, DOMAIN
from .coordinator import AquaBleCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AquaBle from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    address = entry.data[CONF_ADDRESS]
    device_type = entry.data[CONF_DEVICE_TYPE]
    
    _LOGGER.debug("Setting up AquaBle device: %s (%s)", address, device_type)

    coordinator = AquaBleCoordinator(hass, address, device_type)

    # Perform the first fetch to ensure the device is online and we get its state
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Register our custom configuration services (Actions)
    await async_setup_services(hass)
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
