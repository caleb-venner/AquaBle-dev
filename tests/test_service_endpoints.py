"""Tests for the FastAPI endpoints and service helpers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aquable.ble_service import CachedStatus
from aquable.service import app, service


def _cached(device_type: str = "doser") -> CachedStatus:
    """Return a populated CachedStatus for use in tests."""
    return CachedStatus(
        address="AA:BB:CC:DD:EE:FF",
        device_type=device_type,
        connected=True,
        updated_at=123.456,
    )


async def _noop() -> None:
    """Asynchronous placeholder used when patching service lifecycle."""
    return None


@pytest.fixture()
def test_client(monkeypatch: pytest.MonkeyPatch):
    """Provide a TestClient with lifespan while disabling BLE side-effects."""
    # Prevent automatic reconnects and device discovery
    service._auto_reconnect = False  # type: ignore[attr-defined]
    # Note: _attempt_reconnect and _load_state methods no longer exist in the refactored BLEService
    with TestClient(app) as client:
        yield client


def test_removed_legacy_routes_return_404(test_client: TestClient) -> None:
    """Previously archived legacy routes should now be absent (404)."""
    assert test_client.get("/ui").status_code == 404
    assert test_client.get("/debug").status_code == 404
    # Ensure nested paths also 404
    assert test_client.get("/ui/anything").status_code == 404
    assert test_client.get("/debug/anything").status_code == 404
