"""Config flow for AquaBle integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DEVICE_TYPE, DEVICE_REGISTRY, DOMAIN, DeviceModelInfo

_LOGGER = logging.getLogger(__name__)


def match_device_model(device_name: str | None) -> tuple[str, DeviceModelInfo] | None:
    """Find the best matching model from the registry for a given device name."""
    if not device_name:
        return None
    normalized_name = device_name.strip().upper()
    compact_name = re.sub(r"[^A-Z0-9]", "", normalized_name)

    # Prefer longest model codes first so prefixes do not collide.
    for model_code in sorted(DEVICE_REGISTRY.keys(), key=len, reverse=True):
        if normalized_name.startswith(model_code) or model_code in normalized_name:
            return model_code, DEVICE_REGISTRY[model_code]
        if compact_name.startswith(model_code) or model_code in compact_name:
            return model_code, DEVICE_REGISTRY[model_code]

    return None


class AquaBleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AquaBle."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device_name: str | None = None
        self._discovered_model_info: DeviceModelInfo | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        match = match_device_model(discovery_info.name)
        if not match:
            return self.async_abort(reason="not_supported")

        _, model_info = match

        self._discovery_info = discovery_info
        self._discovered_device_name = discovery_info.name
        self._discovered_model_info = model_info

        self.context["title_placeholders"] = {"name": self._discovered_device_name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_device_name or self._discovery_info.address,
                data={
                    CONF_ADDRESS: self._discovery_info.address,
                    CONF_NAME: self._discovered_device_name,
                    CONF_DEVICE_TYPE: self._discovered_model_info.type,
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovered_device_name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to manually pick a discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery_info = self._discovered_devices[address]

            match = match_device_model(discovery_info.name)
            model_info = match[1] if match else None
            device_type = model_info.type if model_info else "light"

            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=discovery_info.name or address,
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: discovery_info.name,
                    CONF_DEVICE_TYPE: device_type,
                },
            )

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue

            if match_device_model(discovery_info.name):
                self._discovered_devices[address] = discovery_info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        # Create a dictionary of address -> friendly name for the dropdown
        device_options = {
            address: f"{info.name} ({address})"
            for address, info in self._discovered_devices.items()
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(device_options),
                }
            ),
        )
