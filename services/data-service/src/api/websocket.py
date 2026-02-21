"""WebSocket endpoint for live telemetry."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.config import settings
from src.utils import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manage WebSocket connections for live telemetry.
    
    Features:
    - Device-specific subscription management
    - Connection limiting
    - Heartbeat/ping support
    - Broadcast capability
    """
    
    def __init__(self):
        """Initialize connection manager."""
        # Map of device_id -> set of WebSocket connections
        self._device_connections: Dict[str, Set[WebSocket]] = {}
        # Map of WebSocket -> device_id for reverse lookup
        self._connection_devices: Dict[WebSocket, str] = {}
        # Track total connections
        self._total_connections = 0
        
        logger.info("ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, device_id: str) -> bool:
        """
        Accept and track a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            device_id: Device to subscribe to
            
        Returns:
            True if connected, False if limit reached
        """
        # Check connection limit
        if self._total_connections >= settings.ws_max_connections:
            logger.warning(
                "Max WebSocket connections reached",
                max_connections=settings.ws_max_connections,
            )
            return False
        
        # Accept connection
        await websocket.accept()
        
        # Track connection
        if device_id not in self._device_connections:
            self._device_connections[device_id] = set()
        
        self._device_connections[device_id].add(websocket)
        self._connection_devices[websocket] = device_id
        self._total_connections += 1
        
        logger.info(
            "WebSocket connected",
            device_id=device_id,
            total_connections=self._total_connections,
        )
        
        return True
    
    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove and clean up a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        device_id = self._connection_devices.get(websocket)
        
        if device_id:
            # Remove from device connections
            if device_id in self._device_connections:
                self._device_connections[device_id].discard(websocket)
                
                # Clean up empty device entry
                if not self._device_connections[device_id]:
                    del self._device_connections[device_id]
            
            # Remove from connection mapping
            del self._connection_devices[websocket]
            self._total_connections -= 1
            
            logger.info(
                "WebSocket disconnected",
                device_id=device_id,
                total_connections=self._total_connections,
            )
    
    async def send_telemetry(
        self,
        device_id: str,
        telemetry_data: Dict,
    ) -> None:
        """
        Send telemetry data to all subscribers of a device.
        
        Args:
            device_id: Device identifier
            telemetry_data: Telemetry data to send
        """
        if device_id not in self._device_connections:
            return
        
        # Prepare message
        message = {
            "type": "telemetry",
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": telemetry_data,
        }
        
        # Send to all subscribers
        disconnected = []
        for websocket in self._device_connections[device_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send to WebSocket",
                    device_id=device_id,
                    error=str(e),
                )
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def send_heartbeat(self, websocket: WebSocket) -> None:
        """
        Send heartbeat message to a WebSocket.
        
        Args:
            websocket: WebSocket connection
        """
        try:
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.warning(
                "Failed to send heartbeat",
                error=str(e),
            )
    
    def get_subscriber_count(self, device_id: str) -> int:
        """
        Get number of subscribers for a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Number of subscribers
        """
        return len(self._device_connections.get(device_id, set()))
    
    @property
    def total_connections(self) -> int:
        """Get total number of active connections."""
        return self._total_connections


# Global connection manager instance
connection_manager = ConnectionManager()


def create_websocket_router() -> APIRouter:
    """
    Create WebSocket router.
    
    Returns:
        Configured API router
    """
    router = APIRouter()
    
    @router.websocket("/ws/telemetry/{device_id}")
    async def telemetry_websocket(websocket: WebSocket, device_id: str):
        """
        WebSocket endpoint for live telemetry.
        
        Args:
            websocket: WebSocket connection
            device_id: Device to subscribe to
        """
        # Connect
        connected = await connection_manager.connect(websocket, device_id)
        
        if not connected:
            await websocket.close(code=1008, reason="Max connections reached")
            return
        
        try:
            # Send initial connection confirmation
            await websocket.send_json({
                "type": "connected",
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            # Keep connection alive and handle messages
            while True:
                try:
                    # Wait for message with timeout (for heartbeat)
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=settings.ws_heartbeat_interval,
                    )
                    
                    # Handle client messages
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "ping":
                            await websocket.send_json({
                                "type": "pong",
                                "timestamp": datetime.utcnow().isoformat(),
                            })
                        elif msg_type == "subscribe":
                            # Client can request subscription confirmation
                            await websocket.send_json({
                                "type": "subscribed",
                                "device_id": device_id,
                            })
                        else:
                            logger.debug(
                                "Unknown WebSocket message type",
                                type=msg_type,
                                device_id=device_id,
                            )
                            
                    except json.JSONDecodeError:
                        logger.warning(
                            "Invalid JSON received on WebSocket",
                            device_id=device_id,
                        )
                        
                except asyncio.TimeoutError:
                    # Send heartbeat
                    await connection_manager.send_heartbeat(websocket)
                    
        except WebSocketDisconnect:
            logger.info(
                "WebSocket disconnected",
                device_id=device_id,
            )
        except Exception as e:
            logger.error(
                "WebSocket error",
                device_id=device_id,
                error=str(e),
            )
        finally:
            connection_manager.disconnect(websocket)
    
    @router.get("/ws/stats")
    async def websocket_stats():
        """
        Get WebSocket connection statistics.
        
        Returns:
            Connection statistics
        """
        return {
            "total_connections": connection_manager.total_connections,
            "device_subscriptions": {
                device_id: connection_manager.get_subscriber_count(device_id)
                for device_id in connection_manager._device_connections.keys()
            },
            "max_connections": settings.ws_max_connections,
        }
    
    return router


async def broadcast_telemetry(
    device_id: str,
    telemetry_data: Dict,
) -> None:
    """
    Broadcast telemetry to all subscribers.
    
    This function can be called from the telemetry service
    to broadcast new telemetry data to connected WebSockets.
    
    Args:
        device_id: Device identifier
        telemetry_data: Telemetry data to broadcast
    """
    await connection_manager.send_telemetry(device_id, telemetry_data)
