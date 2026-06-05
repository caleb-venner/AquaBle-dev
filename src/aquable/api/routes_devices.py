"""Device-agnostic API routes (scan, status, connect)."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..core import discovery, dispatcher
from ..domain import storage
from .routes_commands import get_config_dir

router = APIRouter(prefix="/api", tags=["devices"])

@router.get("/status")
async def get_status(request: Request) -> dict[str, Any]:
    """Return cached status for all devices from disk."""
    config_dir = get_config_dir(request)
    
    results = {}
    device_files = storage.list_device_files(config_dir)
    
    import json
    import time
    from datetime import datetime
    
    for device_file in device_files:
        try:
            device_id = device_file.stem.replace("_", ":")
            # We must return the DeviceStatus envelope, not the raw payload
            data = json.loads(device_file.read_text(encoding="utf-8"))
            
            last_updated_str = data.get("last_updated")
            updated_at = 0
            if last_updated_str:
                try:
                    updated_at = int(datetime.fromisoformat(last_updated_str).timestamp())
                except Exception:
                    pass
                    
            device_type = data.get("device_type", "light")
            
            # Assume connected if we heard from it in the last 15 minutes (or whatever heuristic)
            # Actually, the proxy continuously streams advertisements, so we'll just return true for now
            current_time = int(time.time())
            connected = (current_time - updated_at) < 900 
            
            results[device_id] = {
                "address": device_id,
                "device_type": device_type,
                "connected": connected,
                "updated_at": updated_at
            }
        except Exception:
            pass
            
    return results


@router.get("/scan")
async def scan_devices(request: Request, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Scan for nearby supported devices."""
    try:
        return await discovery.discover_devices(timeout=timeout)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bluetooth scan failed: {str(e)}") from e


@router.post("/devices/{address}/status")
async def refresh_status(request: Request, address: str, device_type: str) -> dict[str, Any]:
    """Refresh status for a specific device by address.
    
    Note: device_type ('doser' or 'light') is required as a query param.
    """
    config_dir = get_config_dir(request)
    
    if device_type not in ("doser", "light"):
        raise HTTPException(status_code=400, detail="device_type must be 'doser' or 'light'")
    
    try:
        _, status_dataclass = await dispatcher.request_status_and_update(
            config_dir=config_dir, 
            device_id=address, 
            device_type=device_type, 
            msg_id=(0,0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not status_dataclass:
        raise HTTPException(status_code=404, detail="Failed to parse status from device")
        
    import dataclasses
    
    def _convert_bytes(obj):
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()
        elif isinstance(obj, dict):
            return {k: _convert_bytes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_convert_bytes(v) for v in obj]
        return obj

    return _convert_bytes(dataclasses.asdict(status_dataclass))


@router.post("/devices/{address}/connect")
async def connect_device(request: Request, address: str, device_type: str) -> dict[str, Any]:
    """Connect to a device and return its current status. 
    
    In the functional model, connecting and refreshing status is exactly the same operation.
    """
    return await refresh_status(request, address, device_type)
