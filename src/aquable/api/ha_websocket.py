"""
Home Assistant WebSocket Client

Provides real-time state updates for Home Assistant switch entities via WebSocket.
"""

import os
import asyncio
import logging
from typing import Optional, Callable, Dict, Any, Set
import json

import websockets

logger = logging.getLogger(__name__)


class HAWebSocketClient:
    """WebSocket client for Home Assistant real-time updates"""

    def __init__(self):
        self.token = os.environ.get("SUPERVISOR_TOKEN")
        self.ws_url = "ws://supervisor/core/websocket"
        self._ws: Optional[Any] = None
        self._msg_id = 1
        self._subscribed = False
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: Set[Callable[[str, Dict[str, Any]], None]] = set()

    @property
    def is_available(self) -> bool:
        """Check if Home Assistant WebSocket integration is available"""
        return self.token is not None

    def add_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Add a callback for state change events.

        Args:
            callback: Function called with (entity_id, state_data) when entity state changes
        """
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Remove a callback"""
        self._callbacks.discard(callback)

    async def connect(self):
        """Connect to Home Assistant WebSocket API"""
        if not self.is_available:
            logger.warning("Home Assistant WebSocket not available (no token)")
            return

        if self._running:
            logger.warning("WebSocket client already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Started Home Assistant WebSocket client")

    async def disconnect(self):
        """Disconnect from Home Assistant WebSocket API"""
        self._running = False
        
        if self._ws and not self._ws.closed:
            await self._ws.close()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Stopped Home Assistant WebSocket client")

    async def _run(self):
        """Main WebSocket connection loop with reconnection logic"""
        while self._running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self._running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

    async def _connect_and_listen(self):
        """Connect to WebSocket and listen for messages"""
        async with websockets.connect(self.ws_url) as ws:
            self._ws = ws
            self._subscribed = False
            self._msg_id = 1

            # Authenticate
            auth_msg = await ws.recv()
            auth_data = json.loads(auth_msg)
            
            if auth_data.get("type") != "auth_required":
                logger.error(f"Unexpected auth message: {auth_data}")
                return

            # Send authentication
            await ws.send(json.dumps({
                "type": "auth",
                "access_token": self.token
            }))

            # Wait for auth result
            auth_result = await ws.recv()
            auth_result_data = json.loads(auth_result)
            
            if auth_result_data.get("type") != "auth_ok":
                logger.error(f"Authentication failed: {auth_result_data}")
                return

            logger.info("WebSocket authenticated successfully")

            # Subscribe to state_changed events for switch entities
            await self._subscribe_state_changes()

            # Listen for messages
            while self._running:
                try:
                    message = await ws.recv()
                    data = json.loads(message)
                    await self._handle_message(data)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

    async def _subscribe_state_changes(self):
        """Subscribe to state_changed events"""
        if not self._ws:
            return

        subscribe_msg = {
            "id": self._msg_id,
            "type": "subscribe_events",
            "event_type": "state_changed"
        }
        
        await self._ws.send(json.dumps(subscribe_msg))
        self._msg_id += 1
        self._subscribed = True
        logger.info("Subscribed to state_changed events")

    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        msg_type = data.get("type")
        
        if msg_type == "event":
            event = data.get("event", {})
            event_type = event.get("event_type")
            
            if event_type == "state_changed":
                await self._handle_state_changed(event)
        elif msg_type == "result":
            # Subscription confirmation
            success = data.get("success", False)
            if success:
                logger.debug("Subscription confirmed")

    async def _handle_state_changed(self, event: Dict[str, Any]):
        """Handle state_changed event"""
        event_data = event.get("data", {})
        entity_id = event_data.get("entity_id", "")
        
        # Only process switch entities
        if not entity_id.startswith("switch."):
            return

        new_state = event_data.get("new_state", {})
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(entity_id, new_state)
            except Exception as e:
                logger.error(f"Error in callback: {e}")


# Global WebSocket client instance
_ws_client: Optional[HAWebSocketClient] = None


def get_ha_websocket_client() -> HAWebSocketClient:
    """Get the global Home Assistant WebSocket client instance"""
    global _ws_client
    if _ws_client is None:
        _ws_client = HAWebSocketClient()
    return _ws_client


async def start_ha_websocket():
    """Start the Home Assistant WebSocket client"""
    client = get_ha_websocket_client()
    await client.connect()


async def stop_ha_websocket():
    """Stop the Home Assistant WebSocket client"""
    global _ws_client
    if _ws_client:
        await _ws_client.disconnect()
        _ws_client = None
