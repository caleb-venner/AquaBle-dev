"""API routes for device configuration management.

These endpoints provide CRUD operations for saved device configurations,
allowing the frontend to view, edit, and manage device configurations
independently of active device connections.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..domain import storage
from ..domain.doser import DoserDevice
from ..domain.light import LightDevice
from .routes_commands import get_config_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["configurations"])


class DeviceNamingUpdate(BaseModel):
    """Request model for updating device naming fields only."""
    name: str | None = Field(None, description="Device display name")
    headNames: dict[int, str] | None = Field(None, description="Head display names (doser only)")


class DeviceSettingsUpdate(BaseModel):
    """Request model for updating device settings/configurations."""
    configurations: list | None = Field(None, description="Device configurations")
    activeConfigurationId: str | None = Field(None, description="Active configuration ID")
    autoReconnect: bool | None = Field(None, description="Auto-reconnect setting")


@router.get("/devices/{address}/configurations")
async def get_device_configurations(request: Request, address: str) -> dict[str, Any]:
    """Get device configuration by address (detects device type automatically)."""
    config_dir = get_config_dir(request)
    device_file = storage._get_device_file_path(config_dir, address)
    
    if not device_file.exists():
        return {"id": address, "configurations": []}
        
    try:
        data = json.loads(device_file.read_text(encoding="utf-8"))
        device_data = data.get("device_data")
        
        # If no config yet, create a default one
        if not device_data:
            device_data = {"id": address, "configurations": []}
            
        # The frontend expects the live status payload to be attached to the configuration object
        if "last_status" in data:
            last_status_data = dict(data["last_status"])
            
            raw_payload = last_status_data.pop("raw_payload", None)
            raw_payloads = last_status_data.pop("raw_payloads", [])
            
            if raw_payload and raw_payload not in raw_payloads:
                raw_payloads.insert(0, raw_payload)
                
            device_data["last_status"] = {
                "parsed": last_status_data,
                "raw_payloads": raw_payloads
            }
        if "last_updated" in data:
            import time
            from datetime import datetime
            try:
                # Convert ISO string to unix timestamp for frontend
                device_data["updatedAt"] = data["last_updated"]
                if "last_status" in device_data:
                    device_data["last_status"]["updated_at"] = int(datetime.fromisoformat(data["last_updated"]).timestamp())
            except Exception:
                pass
                
        return device_data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail="Device file corrupted") from e


@router.put("/devices/{address}/configurations")
async def put_device_configurations(request: Request, address: str, device_data: dict[str, Any]) -> dict[str, Any]:
    """Replace entire device configuration."""
    config_dir = get_config_dir(request)
    device_data["id"] = address
    
    try:
        # Simplistic heuristic to determine type: lights define "channels"
        if "channels" in device_data:
            device = LightDevice.from_dict(device_data)
            device_type = "light"
        else:
            device = DoserDevice.from_dict(device_data)
            device_type = "doser"
            
        storage.save_device(config_dir, device, device_type)
        
        import dataclasses
        return dataclasses.asdict(device)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/devices/{address}/configurations/naming")
async def patch_device_naming(request: Request, address: str, naming_update: DeviceNamingUpdate) -> dict[str, Any]:
    """Update device naming fields only (name, head names)."""
    config_dir = get_config_dir(request)
    device_file = storage._get_device_file_path(config_dir, address)
    
    if not device_file.exists():
        raise HTTPException(status_code=404, detail=f"Device not found: {address}")
        
    try:
        data = json.loads(device_file.read_text(encoding="utf-8"))
        device_data = data.get("device_data")
        device_type = data.get("device_type")
        
        if not device_data:
            device_data = {"id": address, "configurations": []}
            
        if naming_update.name is not None:
            device_data["name"] = naming_update.name
            
        if naming_update.headNames is not None and device_type == "doser":
            # the dict keys must be integers
            device_data["headNames"] = {int(k): v for k, v in naming_update.headNames.items()}
            
        # If device is incomplete, bypass full model parsing and save directly
        if not device_data.get("configurations") or (device_type == "light" and not device_data.get("channels")):
            data["device_data"] = device_data
            from ..core.system_time import now_iso
            data["last_updated"] = now_iso()
            
            tmp_file = device_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            tmp_file.replace(device_file)
            
            return device_data
            
        # Re-parse to enforce all invariants
        if device_type == "doser":
            device = DoserDevice.from_dict(device_data)
        elif device_type == "light":
            device = LightDevice.from_dict(device_data)
        else:
            raise ValueError(f"Unknown device type {device_type}")
            
        storage.save_device(config_dir, device, device_type)
        
        import dataclasses
        return dataclasses.asdict(device)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/devices/{address}/configurations/settings")
async def patch_device_settings(request: Request, address: str, settings_update: DeviceSettingsUpdate) -> dict[str, Any]:
    """Update device settings/configurations independently from naming."""
    config_dir = get_config_dir(request)
    device_file = storage._get_device_file_path(config_dir, address)
    
    if not device_file.exists():
        raise HTTPException(status_code=404, detail=f"Device not found: {address}")
        
    try:
        data = json.loads(device_file.read_text(encoding="utf-8"))
        device_data = data.get("device_data")
        device_type = data.get("device_type")
        
        if not device_data:
            raise HTTPException(status_code=404, detail="Device data missing")
            
        if settings_update.configurations is not None:
            device_data["configurations"] = settings_update.configurations
        if settings_update.activeConfigurationId is not None:
            device_data["activeConfigurationId"] = settings_update.activeConfigurationId
        if settings_update.autoReconnect is not None:
            device_data["autoReconnect"] = settings_update.autoReconnect
            
        # If device is incomplete, bypass full model parsing and save directly
        if not device_data.get("configurations") or (device_type == "light" and not device_data.get("channels")):
            data["device_data"] = device_data
            from ..core.system_time import now_iso
            data["last_updated"] = now_iso()
            
            tmp_file = device_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            tmp_file.replace(device_file)
            
            return device_data

        if device_type == "doser":
            device = DoserDevice.from_dict(device_data)
        elif device_type == "light":
            device = LightDevice.from_dict(device_data)
        else:
            raise ValueError(f"Unknown device type {device_type}")
            
        storage.save_device(config_dir, device, device_type)
        
        import dataclasses
        return dataclasses.asdict(device)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
