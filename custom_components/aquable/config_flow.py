"""Config flow for AquaBle integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DEVICE_TYPE, DOMAIN, DEVICE_REGISTRY

_LOGGER = logging.getLogger(__name__)

class AquaBleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AquaBle."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        # TODO: Implement matching logic using DEVICE_REGISTRY
        return self.async_abort(reason="not_supported")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to manually pick a discovered device."""
        # TODO: Implement manual selection flow
        return self.async_abort(reason="no_devices_found")
