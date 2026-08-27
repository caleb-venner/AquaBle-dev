"""Lovelace card resource registration for AquaBle custom dashboard cards.

The card JS must be registered as a Lovelace resource rather than loaded via
frontend.add_extra_js_url. add_extra_js_url injects the module into the
index page's <script type="module">, which runs at page load — before HA
lazily installs @webcomponents/scoped-custom-element-registry on first
Lovelace render. Installing that polyfill swaps window.customElements for a
fresh registry, silently dropping any element defined beforehand, so HA then
reports "custom element doesn't exist" until the user refreshes. Lovelace
resources are loaded during Lovelace init (after the swap), so the card
survives a cold load.

Falls back to add_extra_js_url when the Lovelace resource store is
unavailable (e.g. YAML-mode dashboards), where the timing issue doesn't apply.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Key under hass.data[DOMAIN] holding the registered resource's id.
_RESOURCE_ID_KEY = "card_resource_id"
# issue_id (scoped to DOMAIN) and translation_key for the "card installed —
# hard-refresh to load it" repair issue.
_CARD_INSTALLED_ISSUE = "card_installed"


def _get_lovelace_resources(hass: HomeAssistant) -> Any:
    """The Lovelace resource collection, or None if unavailable (YAML mode)."""
    return getattr(hass.data.get("lovelace"), "resources", None)


def _record_resource_id(hass: HomeAssistant, resource_id: str) -> None:
    """Remember the resource's id so a later full uninstall can delete it."""
    ids = hass.data.setdefault(DOMAIN, {}).setdefault(_RESOURCE_ID_KEY, set())
    if isinstance(ids, set):
        ids.add(resource_id)
    else:
        hass.data[DOMAIN][_RESOURCE_ID_KEY] = {ids, resource_id}


def _create_refresh_issue(hass: HomeAssistant) -> None:
    """Raise a repair issue telling the user to hard-refresh for the new card."""
    async_create_issue(
        hass,
        DOMAIN,
        _CARD_INSTALLED_ISSUE,
        is_fixable=False,
        severity=IssueSeverity.WARNING,
        translation_key=_CARD_INSTALLED_ISSUE,
    )


async def async_register_card_resource(
    hass: HomeAssistant,
    base_url: str,
    card_url: str,
) -> None:
    """Register the card JS as a Lovelace resource (preferred).

    base_url is the stable, hash-independent prefix used to recognise a
    resource left over from a previous version so it can be cache-busted in
    place; card_url is the current, content-hashed URL. Falls back to
    add_extra_js_url if the Lovelace resource store is not available.
    """
    installed = False
    try:
        resources = _get_lovelace_resources(hass)
        if resources is None or not hasattr(resources, "async_create_item"):
            frontend.add_extra_js_url(hass, card_url)
            return

        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        stale = None
        for item in resources.async_items():
            url = item.get("url", "")
            if url == card_url:
                # Already current — record the id so a later uninstall can delete it.
                _record_resource_id(hass, item["id"])
                return
            if url.startswith(base_url) and Path(url).name == Path(card_url).name:
                stale = item
                break

        if stale is not None:
            # Cache-bust in place
            await resources.async_update_item(stale["id"], {"url": card_url})
            _record_resource_id(hass, stale["id"])
        else:
            item = await resources.async_create_item(
                {"res_type": "module", "url": card_url}
            )
            _record_resource_id(hass, item["id"])
            installed = True
    except Exception:
        _LOGGER.debug(
            "Could not register card as a Lovelace resource; falling back to add_extra_js_url",
            exc_info=True,
        )
        frontend.add_extra_js_url(hass, card_url)
        return

    if installed:
        try:
            _create_refresh_issue(hass)
        except Exception:
            _LOGGER.debug("Could not create card refresh repair issue", exc_info=True)


async def async_unregister_card_resources(
    hass: HomeAssistant,
    card_urls: list[str],
) -> None:
    """Remove all registered Lovelace resources (on full uninstall)."""
    resource_ids = hass.data.get(DOMAIN, {}).get(_RESOURCE_ID_KEY, set())
    if not isinstance(resource_ids, set):
        resource_ids = {resource_ids} if resource_ids else set()

    for url in card_urls:
        try:
            frontend.remove_extra_js_url(hass, url)
        except Exception:
            pass

    resources = _get_lovelace_resources(hass)
    if resources is not None and hasattr(resources, "async_delete_item"):
        for res_id in list(resource_ids):
            try:
                await resources.async_delete_item(res_id)
            except Exception:
                _LOGGER.debug(
                    "Could not remove Lovelace resource %s", res_id, exc_info=True
                )
    hass.data.get(DOMAIN, {}).pop(_RESOURCE_ID_KEY, None)
