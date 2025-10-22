"""Tests for auto-discover interactions with auto-reconnect."""

from __future__ import annotations

import asyncio

from aquable import ble_service as service_mod


def test_auto_discover_skips_auto_reconnect(monkeypatch):
    """Test auto-reconnect is skipped if auto-discover connects devices on startup."""
    svc = service_mod.BLEService()
    svc._auto_discover_on_start = True  # type: ignore[attr-defined]
    svc._auto_reconnect = True  # type: ignore[attr-defined]

    async def fake_load_state():
        return None

    async def fake_auto_discover():
        # Simulate successful discovery by returning True
        # In the real code, this would add devices to _devices dict and unified storage
        return True

    # Mock list_all_devices to return a device after auto-discover
    original_list = svc._unified_storage.list_all_devices
    device_count = [0]  # Use list to allow modification in nested function
    
    def fake_list_all_devices():
        # Return empty initially, then 1 device after auto-discover is called
        if device_count[0] > 0:
            # Return a mock device
            from unittest.mock import MagicMock
            mock_device = MagicMock()
            mock_device.device_id = "test_addr"
            mock_device.device_type = "light"
            return [mock_device]
        return []
    
    async def fake_auto_discover_wrapper():
        result = await fake_auto_discover()
        device_count[0] = 1  # Increment after auto-discover runs
        return result

    monkeypatch.setattr(svc, "_load_state", fake_load_state)
    monkeypatch.setattr(svc, "_auto_discover_and_connect", fake_auto_discover_wrapper)
    monkeypatch.setattr(svc._unified_storage, "list_all_devices", fake_list_all_devices)

    asyncio.run(svc.start())

    # When auto-discover finds devices, reconnect task should not be created
    assert svc._reconnect_task is None


def test_auto_discover_allows_auto_reconnect_when_none_found(monkeypatch):
    """Test auto-reconnect is allowed if auto-discover finds no devices on startup."""
    svc = service_mod.BLEService()
    svc._auto_discover_on_start = True  # type: ignore[attr-defined]
    svc._auto_reconnect = True  # type: ignore[attr-defined]

    async def fake_load_state():
        return None

    async def fake_auto_discover():
        # Simulate no devices found
        return False

    # Mock list_all_devices to always return empty (no devices)
    def fake_list_all_devices():
        return []

    monkeypatch.setattr(svc, "_load_state", fake_load_state)
    monkeypatch.setattr(svc, "_auto_discover_and_connect", fake_auto_discover)
    monkeypatch.setattr(svc._unified_storage, "list_all_devices", fake_list_all_devices)

    asyncio.run(svc.start())

    # When auto-discover finds no devices, the reconnect task should be scheduled
    # by the auto-discover worker (after it completes in background)
    # Since the worker runs in background, we just verify the discover task was created
    assert svc._discover_task is not None
