"""
Home Assistant API Client

Provides access to Home Assistant supervisor API for entity control.
Requires SUPERVISOR_TOKEN environment variable (automatically provided in add-on mode).
"""

import os
import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class HAClient:
    """Client for interacting with Home Assistant Supervisor API"""

    def __init__(self):
        self.token = os.environ.get("SUPERVISOR_TOKEN")
        self.base_url = "http://supervisor/core/api"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_available(self) -> bool:
        """Check if Home Assistant integration is available"""
        return self.token is not None

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        if not self.token:
            raise ValueError("SUPERVISOR_TOKEN not available")
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of an entity.

        Args:
            entity_id: Entity ID (e.g., "switch.aquarium_pump")

        Returns:
            Dict with state and attributes, or None if unavailable/error
        """
        if not self.is_available:
            logger.warning("Home Assistant integration not available")
            return None

        try:
            client = await self._get_client()
            url = f"{self.base_url}/states/{entity_id}"
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Entity not found: {entity_id}")
            else:
                logger.error(f"Error getting state for {entity_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting state for {entity_id}: {e}")
            return None

    async def toggle_switch(self, entity_id: str) -> bool:
        """
        Toggle a switch entity.

        Args:
            entity_id: Switch entity ID (e.g., "switch.aquarium_pump")

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Home Assistant integration not available")
            return False

        if not entity_id.startswith("switch."):
            logger.error(f"Invalid switch entity: {entity_id}")
            return False

        try:
            client = await self._get_client()
            url = f"{self.base_url}/services/switch/toggle"
            data = {"entity_id": entity_id}
            response = await client.post(url, headers=self._get_headers(), json=data)
            response.raise_for_status()
            logger.info(f"Toggled switch: {entity_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Error toggling switch {entity_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error toggling switch {entity_id}: {e}")
            return False

    async def execute_script(self, entity_id: str) -> bool:
        """
        Execute a script entity.

        Args:
            entity_id: Script entity ID (e.g., "script.water_change_routine")

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available:
            logger.warning("Home Assistant integration not available")
            return False

        if not entity_id.startswith("script."):
            logger.error(f"Invalid script entity: {entity_id}")
            return False

        try:
            # Extract script name from entity_id (e.g., "script.water_change" -> "water_change")
            script_name = entity_id.split(".", 1)[1]
            
            client = await self._get_client()
            url = f"{self.base_url}/services/script/{script_name}"
            response = await client.post(url, headers=self._get_headers(), json={})
            response.raise_for_status()
            logger.info(f"Executed script: {entity_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Error executing script {entity_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error executing script {entity_id}: {e}")
            return False


# Global client instance
_ha_client: Optional[HAClient] = None


def get_ha_client() -> HAClient:
    """Get the global Home Assistant client instance"""
    global _ha_client
    if _ha_client is None:
        _ha_client = HAClient()
    return _ha_client


async def close_ha_client():
    """Close the global Home Assistant client"""
    global _ha_client
    if _ha_client:
        await _ha_client.close()
        _ha_client = None
