"""
API routes for device configuration management.

These endpoints provide CRUD operations for saved device configurations,
allowing the frontend to view, edit, and manage device configurations
independently of active device connections.

Exception Handling Pattern:
- OSError/IOError: File system errors (500 status)
- ValueError: Validation errors from Pydantic models (422 status for user input, 500 for storage)
- KeyError: Missing device/configuration (404 status)
- Avoid broad 'except Exception' - catch specific exceptions for better debugging

Error handling is provided by the @handle_storage_errors decorator, which automatically
catches and formats exceptions consistently across all endpoints.
"""

import json
import logging
from typing import Optional, Union

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from ..storage import DoserDevice, DoserStorage, LightDevice, LightStorage
from .exceptions import (
    device_not_found,
    handle_storage_errors,
    invalid_device_data,
    model_code_mismatch,
    storage_error,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["configurations"])


def get_doser_storage(request: Request) -> DoserStorage:
    """Get DoserStorage instance from the app state.

    This dependency function accesses the BLEService from the FastAPI app
    state, eliminating circular dependencies and the service locator pattern.

    Args:
        request: FastAPI request object containing app state

    Returns:
        DoserStorage instance from the service
    """
    return request.app.state.service._doser_storage


def get_light_storage(request: Request) -> LightStorage:
    """Get LightStorage instance from the app state.

    This dependency function accesses the BLEService from the FastAPI app
    state, eliminating circular dependencies and the service locator pattern.

    Args:
        request: FastAPI request object containing app state

    Returns:
        LightStorage instance from the service
    """
    return request.app.state.service._light_storage


# ============================================================================
# Unified Endpoints Helper & Models
# ============================================================================


def get_device_storage(
    request: Request, address: str
) -> tuple[Union[DoserStorage, LightStorage], str]:
    """Detect device type from storage and return appropriate storage instance.

    Args:
        request: FastAPI request object containing app state
        address: MAC address of the device

    Returns:
        Tuple of (storage_instance, device_type) where device_type is 'doser' or 'light'

    Raises:
        HTTPException 404: If device not found in either storage
        HTTPException 500: If device files are corrupted/invalid
    """
    doser_storage = request.app.state.service._doser_storage
    light_storage = request.app.state.service._light_storage

    # Try to detect device type by calling get_device on both storages
    # This is more reliable than checking the file directly since storage handles
    # file path construction and format conversion
    doser_device = doser_storage.get_device(address)
    if doser_device:
        return doser_storage, "doser"

    light_device = light_storage.get_device(address)
    if light_device:
        return light_storage, "light"

    # If device not found in either storage, raise 404
    raise device_not_found(address)


class DeviceNamingUpdate(BaseModel):
    """Request model for updating device naming fields only.

    This model allows updating device name and head names independently
    from configuration changes, without affecting other device fields.
    """

    name: Optional[str] = Field(None, description="Device display name")
    headNames: Optional[dict[int, str]] = Field(None, description="Head display names (doser only)")


class DeviceSettingsUpdate(BaseModel):
    """Request model for updating device settings/configurations.

    This model encapsulates configuration changes for either doser or light devices.
    The frontend sends updates specific to the device type that was detected.
    """

    # Doser-specific settings
    configurations: Optional[list] = Field(None, description="Doser configurations")
    activeConfigurationId: Optional[str] = Field(None, description="Active configuration ID")
    autoReconnect: Optional[bool] = Field(None, description="Auto-reconnect setting")

    # Light-specific settings (if added in future)


# ============================================================================
# Unified Endpoints (v2 API - simplified device management)
# ============================================================================


@router.get("/devices/{address}/configurations")
@handle_storage_errors
async def get_device_configurations(request: Request, address: str):
    """Get device configuration by address (detects device type automatically).

    This unified endpoint works for both doser and light devices,
    automatically detecting the device type from storage.

    Args:
        request: FastAPI request object
        address: MAC address of the device

    Returns:
        DoserDevice or LightDevice configuration with last_status included

    Raises:
        404: Device not found
        500: Device file corrupted or storage error
    """
    storage, device_type = get_device_storage(request, address)
    device = storage.get_device_with_status(address)

    if not device:
        raise HTTPException(
            status_code=404, detail=f"No configuration found for device {address}"
        )

    logger.info(f"Retrieved {device_type} configuration for {address}")
    return device


@router.put("/devices/{address}/configurations")
@handle_storage_errors
async def put_device_configurations(request: Request, address: str, device_data: dict):
    """Replace entire device configuration (detects device type automatically).

    This unified endpoint replaces the full configuration for a device,
    automatically detecting the device type from storage.

    Args:
        request: FastAPI request object
        address: MAC address of the device
        device_data: Complete device configuration object

    Returns:
        Updated DoserDevice or LightDevice configuration

    Raises:
        404: Device not found
        400: Invalid device data
        500: Storage error
    """
    storage, device_type = get_device_storage(request, address)

    # Ensure address matches
    device_data["id"] = address

    # Validate and create device model
    if device_type == "doser":
        device = DoserDevice(**device_data)
        doser_storage: DoserStorage = storage  # type: ignore
        doser_storage.upsert_device(device)
    else:  # light
        device = LightDevice(**device_data)
        light_storage: LightStorage = storage  # type: ignore
        light_storage.upsert_device(device)

    logger.info(f"Updated {device_type} configuration for {address}")
    return device


@router.patch("/devices/{address}/configurations/naming")
@handle_storage_errors
async def patch_device_naming(request: Request, address: str, naming_update: DeviceNamingUpdate):
    """Update device naming fields only (name, head names).

    This PATCH endpoint allows updating device naming without affecting
    other configuration fields. Useful for renaming devices without
    triggering configuration version bumps.

    Args:
        request: FastAPI request object
        address: MAC address of the device
        naming_update: Naming fields to update

    Returns:
        Updated DoserDevice or LightDevice configuration

    Raises:
        404: Device not found
        400: Invalid update data
        500: Storage error
    """
    storage, device_type = get_device_storage(request, address)
    device = storage.get_device(address)

    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {address}")

    # Apply name update
    if naming_update.name is not None:
        device.name = naming_update.name

    # Apply head names update (doser only)
    if naming_update.headNames is not None:
        if device_type == "doser" and isinstance(device, DoserDevice):
            device.headNames = naming_update.headNames
        else:
            logger.warning(f"Attempted to set headNames on light device {address}, ignoring")

    # Save to storage - cast appropriately
    if device_type == "doser":
        doser_storage: DoserStorage = storage  # type: ignore
        doser_storage.upsert_device(device)  # type: ignore
    else:
        light_storage: LightStorage = storage  # type: ignore
        light_storage.upsert_device(device)  # type: ignore

    logger.info(f"Updated naming for {device_type} {address}")
    return device


@router.patch("/devices/{address}/configurations/settings")
@handle_storage_errors
async def patch_device_settings(
    request: Request, address: str, settings_update: DeviceSettingsUpdate
):
    """Update device settings/configurations (configurations, autoReconnect, etc).

    This PATCH endpoint allows updating configuration-related fields
    independently from naming updates. Useful for configuration changes
    without affecting device identification.

    Args:
        request: FastAPI request object
        address: MAC address of the device
        settings_update: Settings/configuration fields to update

    Returns:
        Updated DoserDevice or LightDevice configuration

    Raises:
        404: Device not found
        400: Invalid settings data
        500: Storage error
    """
    storage, device_type = get_device_storage(request, address)
    device = storage.get_device(address)

    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {address}")

    # Apply settings updates (device-type specific)
    if settings_update.autoReconnect is not None:
        device.autoReconnect = settings_update.autoReconnect

    # Doser-specific settings
    if device_type == "doser" and isinstance(device, DoserDevice):
        if settings_update.configurations is not None:
            device.configurations = settings_update.configurations
        if settings_update.activeConfigurationId is not None:
            device.activeConfigurationId = settings_update.activeConfigurationId

    # Save to storage - cast appropriately
    if device_type == "doser":
        doser_storage: DoserStorage = storage  # type: ignore
        doser_storage.upsert_device(device)  # type: ignore
    else:
        light_storage: LightStorage = storage  # type: ignore
        light_storage.upsert_device(device)  # type: ignore

    logger.info(f"Updated settings for {device_type} {address}")
    return device


# ============================================================================
# Import/Export Endpoints
# ============================================================================


@router.get("/devices/{address}/configurations/export")
@handle_storage_errors
async def export_device_configuration(request: Request, address: str):
    """Export device configuration as JSON.

    Returns the complete device configuration (naming, settings, configurations)
    as a JSON object that can be downloaded by the frontend and reimported later.
    Includes device model_code for model-based import matching.

    Args:
        request: FastAPI request object
        address: MAC address of the device

    Returns:
        DoserDevice or LightDevice configuration as JSON with model_code

    Raises:
        404: Device not found
        500: Storage error
    """
    storage, device_type = get_device_storage(request, address)
    device = storage.get_device(address)

    if not device:
        raise device_not_found(address)

    logger.info(f"Exported {device_type} configuration for {address}")
    return device


@router.post("/devices/{address}/configurations/import")
@handle_storage_errors
async def import_device_configuration(request: Request, address: str, file: UploadFile = File(...)):
    """Import device configuration from a JSON file.

    Accepts a JSON file containing a device configuration and imports it to the
    specified address. The file must be valid JSON and compatible with either
    DoserDevice or LightDevice models.

    Model code matching:
    - If imported config has model_code and local device has model_code,
      must match or import is rejected (prevents cross-device imports)
    - If model_code is missing from either, import proceeds

    Args:
        request: FastAPI request object
        address: MAC address of the target device
        file: JSON file containing device configuration

    Returns:
        Imported DoserDevice or LightDevice configuration

    Raises:
        404: Device not found
        400: Invalid JSON or validation error
        409: Model code mismatch
        500: File I/O or storage error
    """
    storage, device_type = get_device_storage(request, address)

    # Read and parse the uploaded file
    try:
        content = await file.read()
        raw_data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in uploaded file for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Error reading uploaded file for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Extract config from export wrapper if present
    if "config" in raw_data and "address" in raw_data:
        # This is an exported file with wrapper structure
        device_data = raw_data["config"]
    else:
        # This is a raw device configuration
        device_data = raw_data

    # Get current device to check model code
    current_device = storage.get_device(address)
    if not current_device:
        raise device_not_found(address)

    # Validate model code match if both have model_code
    imported_model_code = device_data.get("model_code")
    current_model_code = current_device.model_code

    if imported_model_code and current_model_code and imported_model_code != current_model_code:
        logger.error(
            f"Model code mismatch for {address}: "
            f"imported={imported_model_code}, current={current_model_code}"
        )
        raise model_code_mismatch(imported_model_code, current_model_code)

    # Ensure address matches
    device_data["id"] = address

    # Validate and create device model
    if device_type == "doser":
        device = DoserDevice(**device_data)
        doser_storage: DoserStorage = storage  # type: ignore
        doser_storage.upsert_device(device)
    else:  # light
        device = LightDevice(**device_data)
        light_storage: LightStorage = storage  # type: ignore
        light_storage.upsert_device(device)

    logger.info(f"Imported {device_type} configuration for {address}")
    return device
