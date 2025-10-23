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

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from ..storage import (
    DoserDevice,
    DoserMetadata,
    DoserStorage,
    LightDevice,
    LightMetadata,
    LightStorage,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/configurations", tags=["configurations"])


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
# Metadata Endpoints (Name-only storage)
# ============================================================================


@router.get("/dosers/{address}/metadata", response_model=DoserMetadata)
async def get_doser_metadata(
    address: str,
    storage: DoserStorage = Depends(get_doser_storage),
):
    """
    Get device metadata (names only) for a doser.

    This endpoint returns lightweight device information including
    device name and head names without full configuration data.
    Returns an empty metadata object if no metadata exists yet.
    """
    try:
        metadata = storage.get_device_metadata(address)
        if metadata is None:
            # Return empty metadata for devices without existing metadata
            metadata = DoserMetadata(id=address)
        return metadata
    except Exception as e:
        logger.error(f"Error retrieving doser metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metadata: {str(e)}")


@router.put("/dosers/{address}/metadata", response_model=DoserMetadata)
async def update_doser_metadata(
    address: str,
    metadata: DoserMetadata,
    storage: DoserStorage = Depends(get_doser_storage),
):
    """
    Update or create device metadata (names only) for a doser.

    This endpoint allows setting device name and head names without
    creating full device configurations. Use this for server-side
    name storage before sending any device commands.
    """
    if metadata.id != address:
        raise HTTPException(
            status_code=400,
            detail=f"Address mismatch: URL has {address}, body has {metadata.id}",
        )

    try:
        updated_metadata = storage.upsert_device_metadata(metadata)
        logger.info(f"Updated metadata for doser {address}")
        return updated_metadata
    except Exception as e:
        logger.error(f"Error updating doser metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(e)}")


@router.get("/lights/{address}/metadata", response_model=LightMetadata)
async def get_light_metadata(
    address: str,
    storage: LightStorage = Depends(get_light_storage),
):
    """
    Get light metadata by device address.

    Args:
        address: The MAC address of the light device

    Returns:
        The light metadata, or empty metadata if not found yet
    """
    try:
        metadata = storage.get_light_metadata(address)
        if metadata is None:
            # Return empty metadata for devices without existing metadata
            metadata = LightMetadata(id=address)
        else:
            logger.info(f"Retrieved metadata for light {address}")
        return metadata
    except Exception as e:
        logger.error(f"Error getting light metadata for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metadata: {str(e)}")


@router.put("/lights/{address}/metadata", response_model=LightMetadata)
async def update_light_metadata(
    address: str,
    metadata: LightMetadata,
    storage: LightStorage = Depends(get_light_storage),
):
    """
    Update or create light metadata (name only, no schedules).

    This endpoint allows updating just the display name and basic metadata
    for a light device without creating or modifying any light schedules.

    Args:
        address: The MAC address of the light device
        metadata: Light metadata containing name and basic info

    Returns:
        The updated metadata
    """
    try:
        # Ensure the address matches
        metadata.id = address

        updated_metadata = storage.upsert_light_metadata(metadata)
        logger.info(f"Updated metadata for light {address}: {updated_metadata.name}")
        return updated_metadata
    except Exception as e:
        logger.error(f"Error updating light metadata for {address}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(e)}")


# ============================================================================
# Doser Configuration Endpoints
# ============================================================================


@router.get("/dosers", response_model=List[DoserDevice])
async def list_doser_configurations(
    storage: DoserStorage = Depends(get_doser_storage),
):
    """
    Get all saved doser configurations.

    Returns a list of all doser configurations stored in the system.
    These configurations persist across device connections and can be
    used to quickly restore or sync settings to devices.
    """
    try:
        devices = storage.list_devices()
        logger.info(f"Retrieved {len(devices)} doser configurations")
        return devices
    except (OSError, IOError) as e:
        logger.error(f"File I/O error listing doser configurations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except ValueError as e:
        logger.error(f"Validation error listing doser configurations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Configuration validation error: {str(e)}")


@router.get("/dosers/{address}", response_model=DoserDevice)
async def get_doser_configuration(address: str, storage: DoserStorage = Depends(get_doser_storage)):
    """
    Get a specific doser configuration by device address.

    Args:
        address: The MAC address of the doser device

    Returns:
        The doser configuration if found

    Raises:
        404: If no configuration exists for this address
    """
    device = storage.get_device(address)
    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"No configuration found for doser {address}",
        )
    logger.info(f"Retrieved configuration for doser {address}")
    return device


@router.put("/dosers/{address}", response_model=DoserDevice)
async def update_doser_configuration(
    address: str,
    device: DoserDevice,
    storage: DoserStorage = Depends(get_doser_storage),
):
    """
    Update or create a doser configuration.

    Args:
        address: The MAC address of the doser device
        device: The complete device configuration to save

    Returns:
        The updated configuration

    Note:
        The address in the URL must match the id in the device object.
    """
    if device.id != address:
        raise HTTPException(
            status_code=400,
            detail=f"Address mismatch: URL has {address}, body has {device.id}",
        )

    try:
        storage.upsert_device(device)
        logger.info(f"Updated configuration for doser {address}")
        return device
    except (OSError, IOError) as e:
        logger.error(f"File I/O error updating doser configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except ValueError as e:
        logger.error(f"Validation error updating doser configuration: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Invalid configuration: {str(e)}")


@router.delete("/dosers/{address}", status_code=204)
async def delete_doser_configuration(
    address: str, storage: DoserStorage = Depends(get_doser_storage)
):
    """
    Delete a doser configuration.

    Args:
        address: The MAC address of the doser device

    Returns:
        204 No Content on success

    Raises:
        404: If no configuration exists for this address
    """
    if not storage.get_device(address):
        raise HTTPException(
            status_code=404,
            detail=f"No configuration found for doser {address}",
        )

    try:
        storage.delete_device(address)
        logger.info(f"Deleted configuration for doser {address}")
        return None
    except (OSError, IOError) as e:
        logger.error(f"File I/O error deleting doser configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")


# ============================================================================
# Light Configuration Endpoints
# ============================================================================


@router.get("/lights", response_model=List[LightDevice])
async def list_light_configurations(
    storage: LightStorage = Depends(get_light_storage),
):
    """
    Get all saved light configurations.

    Returns a list of all light configurations stored in the system.
    These configurations persist across device connections and can be
    used to quickly restore or sync settings to devices.
    """
    try:
        devices = storage.list_devices()
        logger.info(f"Retrieved {len(devices)} light configurations")
        return devices
    except Exception as e:
        logger.error(f"Error listing light configurations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list configurations: {str(e)}")


@router.get("/lights/{address}", response_model=LightDevice)
async def get_light_configuration(address: str, storage: LightStorage = Depends(get_light_storage)):
    """
    Get a specific light profile by device address.

    Args:
        address: The MAC address of the light device

    Returns:
        The light profile if found

    Raises:
        404: If no profile exists for this address
    """
    device = storage.get_device(address)
    if not device:
        raise HTTPException(status_code=404, detail=f"No profile found for light {address}")
    logger.info(f"Retrieved profile for light {address}")
    return device


@router.put("/lights/{address}", response_model=LightDevice)
async def update_light_configuration(
    address: str,
    device: LightDevice,
    storage: LightStorage = Depends(get_light_storage),
):
    """
    Update or create a light profile.

    Args:
        address: The MAC address of the light device
        device: The complete device profile to save

    Returns:
        The updated profile

    Note:
        The address in the URL must match the id in the device object.
    """
    if device.id != address:
        raise HTTPException(
            status_code=400,
            detail=f"Address mismatch: URL has {address}, body has {device.id}",
        )

    try:
        storage.upsert_device(device)
        logger.info(f"Updated profile for light {address}")
        return device
    except Exception as e:
        logger.error(f"Error updating light profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


@router.delete("/lights/{address}", status_code=204)
async def delete_light_configuration(
    address: str, storage: LightStorage = Depends(get_light_storage)
):
    """
    Delete a light profile.

    Args:
        address: The MAC address of the light device

    Returns:
        204 No Content on success

    Raises:
        404: If no profile exists for this address
    """
    if not storage.get_device(address):
        raise HTTPException(status_code=404, detail=f"No profile found for light {address}")

    try:
        storage.delete_device(address)
        logger.info(f"Deleted profile for light {address}")
        return None
    except Exception as e:
        logger.error(f"Error deleting light profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete profile: {str(e)}")
