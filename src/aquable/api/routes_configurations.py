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
"""

import json
import logging
from typing import Optional, Union

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from ..storage import DoserDevice, DoserStorage, LightDevice, LightStorage

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
    raise HTTPException(status_code=404, detail=f"Device not found: {address}")


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
    try:
        storage, device_type = get_device_storage(request, address)
        device = storage.get_device_with_status(address)

        if not device:
            raise HTTPException(
                status_code=404, detail=f"No configuration found for device {address}"
            )

        logger.info(f"Retrieved {device_type} configuration for {address}")
        return device
    except HTTPException:
        raise
    except (OSError, IOError) as e:
        logger.error(f"File I/O error retrieving device {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except ValueError as e:
        logger.error(f"Validation error retrieving device {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Configuration validation error: {str(e)}")


@router.put("/devices/{address}/configurations")
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
    try:
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
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating device {address}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Invalid device data: {str(e)}")
    except (OSError, IOError) as e:
        logger.error(f"File I/O error updating device {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")


@router.patch("/devices/{address}/configurations/naming")
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
    try:
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
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating naming for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Invalid naming data: {str(e)}")
    except (OSError, IOError) as e:
        logger.error(f"File I/O error updating naming for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")


@router.patch("/devices/{address}/configurations/settings")
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
    try:
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
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating settings for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Invalid settings data: {str(e)}")
    except (OSError, IOError) as e:
        logger.error(f"File I/O error updating settings for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")


# ============================================================================
# Import/Export Endpoints
# ============================================================================


@router.get("/devices/{address}/configurations/export")
async def export_device_configuration(request: Request, address: str):
    """Export device configuration as JSON.

    Returns the complete device configuration (naming, settings, configurations)
    as a JSON object that can be downloaded by the frontend and reimported later.

    Args:
        request: FastAPI request object
        address: MAC address of the device

    Returns:
        DoserDevice or LightDevice configuration as JSON

    Raises:
        404: Device not found
        500: Storage error
    """
    try:
        storage, device_type = get_device_storage(request, address)
        device = storage.get_device(address)

        if not device:
            raise HTTPException(status_code=404, detail=f"Device not found: {address}")

        logger.info(f"Exported {device_type} configuration for {address}")
        return device
    except HTTPException:
        raise
    except (OSError, IOError) as e:
        logger.error(f"File I/O error exporting device {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")


@router.post("/devices/{address}/configurations/import")
async def import_device_configuration(request: Request, address: str, file: UploadFile = File(...)):
    """Import device configuration from a JSON file.

    Accepts a JSON file containing a device configuration and imports it,
    replacing the current configuration. The file must be valid JSON and
    compatible with either DoserDevice or LightDevice models.

    Args:
        request: FastAPI request object
        address: MAC address of the device
        file: JSON file containing device configuration

    Returns:
        Imported DoserDevice or LightDevice configuration

    Raises:
        404: Device not found
        400: Invalid JSON or validation error
        500: File I/O or storage error
    """
    try:
        storage, device_type = get_device_storage(request, address)

        # Read and parse the uploaded file
        try:
            content = await file.read()
            device_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in uploaded file for {address}: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
        except Exception as e:
            logger.error(f"Error reading uploaded file for {address}: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

        # Ensure address matches
        device_data["id"] = address

        # Validate and create device model
        try:
            if device_type == "doser":
                device = DoserDevice(**device_data)
                doser_storage: DoserStorage = storage  # type: ignore
                doser_storage.upsert_device(device)
            else:  # light
                device = LightDevice(**device_data)
                light_storage: LightStorage = storage  # type: ignore
                light_storage.upsert_device(device)
        except ValueError as e:
            logger.error(
                f"Validation error importing configuration for {address}: {e}", exc_info=True
            )
            raise HTTPException(status_code=422, detail=f"Invalid configuration data: {str(e)}")

        logger.info(f"Imported {device_type} configuration for {address}")
        return device
    except HTTPException:
        raise
    except (OSError, IOError) as e:
        logger.error(f"File I/O error importing device {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
