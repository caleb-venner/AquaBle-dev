"""Device-agnostic API routes (scan, status, connect)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from ..device import get_device_from_address
from ..utils import cached_status_to_dict
from .exceptions import (  # device_not_reachable,
    bluetooth_adapter_not_found,
    bluetooth_disabled,
    bluetooth_permission_denied,
    bluetooth_unavailable,
    connection_timeout,
    device_not_found,
    unsupported_device_type,
)

router = APIRouter(prefix="/api", tags=["devices"])


@router.get("/status")
async def get_status(request: Request) -> Dict[str, Any]:
    """Return cached status for all devices."""
    service = request.app.state.service
    snapshot = service.get_status_snapshot()
    results = {}
    for address, cached in snapshot.items():
        results[address] = cached_status_to_dict(service, cached)
    return results


@router.get("/scan")
async def scan_devices(request: Request, timeout: float = 5.0) -> list[Dict[str, Any]]:
    """Scan for nearby supported devices."""
    service = request.app.state.service
    try:
        return await service.scan_devices(timeout=timeout)
    except FileNotFoundError as e:
        raise bluetooth_unavailable() from e
    except PermissionError as e:
        raise bluetooth_permission_denied() from e
    except Exception as e:
        # Catch BleakError and other Bluetooth-related errors
        error_msg = str(e).lower()
        if "bluetooth device is turned off" in error_msg or "not available" in error_msg:
            raise bluetooth_disabled() from e
        elif "adapter" in error_msg or "controller" in error_msg:
            raise bluetooth_adapter_not_found() from e
        # Re-raise as generic 503 for other scan errors
        raise HTTPException(
            status_code=503,
            detail=f"Bluetooth scan failed: {str(e)}",
        ) from e


@router.post("/devices/{address}/status")
async def refresh_status(request: Request, address: str) -> Dict[str, Any]:
    """Refresh status for a specific device by address."""
    service = request.app.state.service
    status = await service.request_status(address)
    return cached_status_to_dict(service, status)


@router.post("/devices/{address}/connect")
async def connect_device(request: Request, address: str) -> Dict[str, Any]:
    """Connect to a device and return its current status."""
    import asyncio
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"Connect request for address: {address}")
    service = request.app.state.service
    cached = service.get_status_snapshot().get(address)

    if cached:
        logger.info(f"Found cached device for {address}, type: {cached.device_type}")
        try:
            status = await asyncio.wait_for(
                service.connect_device(address, cached.device_type), timeout=60.0
            )
            logger.info(f"Successfully connected to {address}")
            return cached_status_to_dict(service, status)
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout for cached device {address}")
            raise connection_timeout() from None
        except HTTPException:
            # HTTPException already logged by service, re-raise without duplication
            raise
        except Exception as e:
            logger.error(f"Failed to connect to cached device {address}: {e}")
            raise

    logger.info(f"No cached device for {address}, attempting discovery")
    try:
        device = await get_device_from_address(address)
        logger.info(f"Discovered device at {address}")
    except Exception as exc:  # pragma: no cover - passthrough
        logger.error(f"Failed to get device from address {address}: {exc}")
        raise device_not_found(address) from exc

    kind = getattr(device, "device_kind", None)
    if not kind:
        logger.error(f"Device at {address} has no device_kind")
        raise unsupported_device_type()

    logger.info(f"Device kind: {kind}, connecting...")
    try:
        status = await asyncio.wait_for(service.connect_device(address, kind), timeout=60.0)
        logger.info(f"Successfully connected to {address}")
        return cached_status_to_dict(service, status)
    except asyncio.TimeoutError:
        logger.error(f"Connection timeout for device {address}")
        raise connection_timeout() from None
    except HTTPException:
        # HTTPException already logged by service, re-raise without duplication
        raise
    except Exception as e:
        logger.error(f"Failed to connect to device {address}: {e}")
        raise


@router.post("/devices/{address}/disconnect")
async def disconnect_device(request: Request, address: str) -> Dict[str, str]:
    """Disconnect a device currently registered at address."""
    service = request.app.state.service
    await service.disconnect_device(address)
    return {"detail": "disconnected"}
