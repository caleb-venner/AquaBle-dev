"""
Home Assistant API Routes

Provides REST endpoints for Home Assistant entity control and configuration.
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from .ha_client import get_ha_client
from ..storage.ha_config import get_ha_storage, HAEntity, EntityType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ha", tags=["home-assistant"])


# ============================================================================
# Request/Response Models
# ============================================================================

class EntityActionRequest(BaseModel):
    """Request to toggle switch or execute script"""
    entity_id: str = Field(..., description="Entity ID to act on")


class AddEntityRequest(BaseModel):
    """Request to add entity to configuration"""
    entity_id: str = Field(..., description="Entity ID")
    label: str = Field(..., description="User-friendly label")
    type: EntityType = Field(..., description="Entity type (switch or script)")


class StatusResponse(BaseModel):
    """Home Assistant integration status"""
    available: bool = Field(..., description="Whether HA integration is available")
    message: str = Field(..., description="Status message")


# ============================================================================
# Status Endpoints
# ============================================================================

@router.get("/status", response_model=StatusResponse)
async def get_ha_status():
    """
    Check if Home Assistant integration is available.

    Returns status indicating whether SUPERVISOR_TOKEN is present.
    """
    client = get_ha_client()
    
    if client.is_available:
        return StatusResponse(
            available=True,
            message="Home Assistant integration available"
        )
    else:
        return StatusResponse(
            available=False,
            message="SUPERVISOR_TOKEN not found (not running as add-on)"
        )


# ============================================================================
# Entity State Endpoints
# ============================================================================

@router.get("/entity/{entity_id:path}")
async def get_entity_state(entity_id: str) -> Dict[str, Any]:
    """
    Get the current state of a Home Assistant entity.

    Args:
        entity_id: Entity ID (e.g., switch.aquarium_pump)

    Returns:
        Entity state and attributes

    Raises:
        503: Home Assistant integration not available
        404: Entity not found
    """
    client = get_ha_client()
    
    if not client.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Home Assistant integration not available"
        )

    state = await client.get_state(entity_id)
    
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity not found: {entity_id}"
        )

    return state


# ============================================================================
# Entity Control Endpoints
# ============================================================================

@router.post("/switch/toggle")
async def toggle_switch(request: EntityActionRequest) -> Dict[str, Any]:
    """
    Toggle a Home Assistant switch entity.

    Args:
        request: Entity action request with entity_id

    Returns:
        Success message and updated state

    Raises:
        503: Home Assistant integration not available
        400: Invalid entity ID or operation failed
    """
    client = get_ha_client()
    
    if not client.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Home Assistant integration not available"
        )

    success = await client.toggle_switch(request.entity_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to toggle switch: {request.entity_id}"
        )

    # Fetch updated state
    state = await client.get_state(request.entity_id)
    
    return {
        "success": True,
        "message": f"Toggled switch: {request.entity_id}",
        "state": state
    }


@router.post("/script/execute")
async def execute_script(request: EntityActionRequest) -> Dict[str, Any]:
    """
    Execute a Home Assistant script entity.

    Args:
        request: Entity action request with entity_id

    Returns:
        Success message

    Raises:
        503: Home Assistant integration not available
        400: Invalid entity ID or operation failed
    """
    client = get_ha_client()
    
    if not client.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Home Assistant integration not available"
        )

    success = await client.execute_script(request.entity_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to execute script: {request.entity_id}"
        )

    return {
        "success": True,
        "message": f"Executed script: {request.entity_id}"
    }


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/config", response_model=List[HAEntity])
async def get_ha_config():
    """
    Get list of configured Home Assistant entities.

    Returns:
        List of configured entities with their labels and types
    """
    storage = get_ha_storage()
    return storage.list_entities()


@router.post("/config/entity", status_code=status.HTTP_201_CREATED)
async def add_entity(request: AddEntityRequest) -> Dict[str, Any]:
    """
    Add a Home Assistant entity to the configuration.

    Args:
        request: Entity configuration (entity_id, label, type)

    Returns:
        Success message

    Raises:
        400: Entity already exists or invalid request
    """
    storage = get_ha_storage()
    
    success = storage.add_entity(
        entity_id=request.entity_id,
        label=request.label,
        entity_type=request.type
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add entity (may already exist): {request.entity_id}"
        )

    return {
        "success": True,
        "message": f"Added entity: {request.entity_id}"
    }


@router.delete("/config/entity/{entity_id:path}")
async def remove_entity(entity_id: str) -> Dict[str, Any]:
    """
    Remove a Home Assistant entity from the configuration.

    Args:
        entity_id: Entity ID to remove

    Returns:
        Success message

    Raises:
        404: Entity not found in configuration
    """
    storage = get_ha_storage()
    
    success = storage.remove_entity(entity_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity not found in configuration: {entity_id}"
        )

    return {
        "success": True,
        "message": f"Removed entity: {entity_id}"
    }
