"""Test that the status capture wait respects environment override."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock

import pytest


@pytest.fixture()
def patched_wait_env(monkeypatch: pytest.MonkeyPatch):
    """Set a small AQUA_BLE_STATUS_WAIT and reload service module.

    Ensures the module-level STATUS_CAPTURE_WAIT_SECONDS constant is
    re-evaluated from the environment for the duration of the test.
    """
    monkeypatch.setenv("AQUA_BLE_STATUS_WAIT", "0.01")
    # Reload the service module so the constant is re-evaluated from env
    import aquable.service as service_mod

    importlib.reload(service_mod)
    return service_mod


def test_capture_wait_uses_env_override(monkeypatch: pytest.MonkeyPatch, patched_wait_env):
    """Verify the capture wait uses the env override instead of default.

    The test captures the value passed to asyncio.sleep during the
    doser status capture and asserts it is ≈0.01s as set by the fixture.
    """
    service_mod = patched_wait_env

    # Speed: ensure no real BLE operations happen.
    service = service_mod.service

    # Create a mock doser device
    mock_doser = AsyncMock()
    mock_doser.device_kind = "doser"
    mock_doser.status_serializer = "serialize_doser_status"
    mock_doser.address = "AA:BB"

    # Set up the device in the new structure
    service._devices["doser"] = {"AA:BB": mock_doser}

    # Provide a fake status object compatible with serializer expectations.
    # Minimal fake status object; we'll bypass real serialization by patching.
    class FakeStatus:
        def __init__(self):
            self.raw_payload = b"\x00"

    fake_status = FakeStatus()
    mock_doser.last_status = fake_status

    # Mock request_status (no-op) to avoid real BLE interaction
    async def fake_request_status():  # pragma: no cover
        return None

    mock_doser.request_status = AsyncMock(side_effect=fake_request_status)

    # Patch serializer to avoid depending on full pump dataclass shape
    from aquable import ble_service as ble_impl

    monkeypatch.setattr(
        ble_impl._utils,
        "serialize_doser_status",
        lambda s: {"ok": True},
    )

    # Patch the device's wait_for_status method to record the timeout
    import asyncio as _asyncio

    recorded = {}

    async def fake_wait_for_status(timeout=None):
        recorded["timeout"] = timeout

    mock_doser.wait_for_status = fake_wait_for_status

    # Run capture with persist=False so we don't need full serialization
    # path reload complexity
    # type: ignore[attr-defined]
    target_address = "AA:BB"
    persist_arg = False
    result = _asyncio.run(service._refresh_device_status(target_address, persist=persist_arg))
    assert result is not None
    # Confirm we used the env override value, not the default 1.5
    timeout_val = recorded.get("timeout", 0)
    assert 0.009 <= timeout_val <= 0.02, recorded
