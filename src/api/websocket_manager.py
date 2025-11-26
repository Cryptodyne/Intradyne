"""
WebSocket Connection Manager
Handles multiple concurrent WebSocket connections with channel/room support.
"""

import asyncio
import json
import time
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Advanced WebSocket connection manager with channel subscriptions.
    Supports broadcasting to all clients, specific channels, or individual users.
    """
    
    def __init__(self, heartbeat_interval: int = 30, max_connections: int = 1000):
        # Active connections: websocket -> metadata
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Channel subscriptions: channel_name -> set of websockets
        self.channels: Dict[str, Set[WebSocket]] = defaultdict(set)
        
        # User connections: user_id -> websocket
        self.user_connections: Dict[str, WebSocket] = {}
        
        self.heartbeat_interval = heartbeat_interval
        self.max_connections = max_connections
        self._heartbeat_task = None
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None):
        """Accept new WebSocket connection with metadata."""
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1008, reason="Max connections reached")
            logger.warning(f"Connection rejected: Max connections ({self.max_connections}) reached")
            return False
        
        await websocket.accept()
        
        # Store connection metadata
        self.active_connections[websocket] = {
            "client_id": client_id,
            "connected_at": time.time(),
            "last_ping": time.time(),
            "channels": set(),
            "message_count": 0
        }
        
        if client_id:
            self.user_connections[client_id] = websocket
        
        logger.info(f"Client connected: {client_id or 'anonymous'} (Total: {len(self.active_connections)})")
        
        # Start heartbeat task if not running
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        return True
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection and cleanup subscriptions."""
        if websocket not in self.active_connections:
            return
        
        metadata = self.active_connections[websocket]
        client_id = metadata.get("client_id")
        
        # Remove from channels
        for channel in metadata["channels"]:
            if channel in self.channels:
                self.channels[channel].discard(websocket)
                if not self.channels[channel]:
                    del self.channels[channel]
        
        # Remove from user connections
        if client_id and client_id in self.user_connections:
            del self.user_connections[client_id]
        
        # Remove connection
        del self.active_connections[websocket]
        
        logger.info(f"Client disconnected: {client_id or 'anonymous'} (Total: {len(self.active_connections)})")
    
    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe connection to a channel."""
        if websocket in self.active_connections:
            self.channels[channel].add(websocket)
            self.active_connections[websocket]["channels"].add(channel)
            logger.debug(f"Client subscribed to channel: {channel}")
            return True
        return False
    
    async def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe connection from a channel."""
        if websocket in self.active_connections:
            self.channels[channel].discard(websocket)
            self.active_connections[websocket]["channels"].discard(channel)
            if not self.channels[channel]:
                del self.channels[channel]
            logger.debug(f"Client unsubscribed from channel: {channel}")
            return True
        return False
    
    async def send_personal(self, websocket: WebSocket, data: Dict[str, Any]):
        """Send message to specific connection."""
        try:
            await websocket.send_json(data)
            if websocket in self.active_connections:
                self.active_connections[websocket]["message_count"] += 1
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def send_to_user(self, user_id: str, data: Dict[str, Any]):
        """Send message to specific user by ID."""
        if user_id in self.user_connections:
            await self.send_personal(self.user_connections[user_id], data)
    
    async def broadcast_all(self, data: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected = []
        
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.send_json(data)
                self.active_connections[websocket]["message_count"] += 1
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.append(websocket)
        
        # Cleanup failed connections
        for ws in disconnected:
            self.disconnect(ws)
        
        if disconnected:
            logger.warning(f"Cleaned up {len(disconnected)} failed connections")
    
    async def broadcast_channel(self, channel: str, data: Dict[str, Any]):
        """Broadcast message to all subscribers of a channel."""
        if channel not in self.channels:
            return
        
        disconnected = []
        subscribers = list(self.channels[channel])
        
        for websocket in subscribers:
            try:
                await websocket.send_json(data)
                if websocket in self.active_connections:
                    self.active_connections[websocket]["message_count"] += 1
            except Exception as e:
                logger.error(f"Channel broadcast error: {e}")
                disconnected.append(websocket)
        
        # Cleanup failed connections
        for ws in disconnected:
            self.disconnect(ws)
    
    async def _heartbeat_loop(self):
        """Send periodic ping to maintain connections."""
        while self.active_connections:
            await asyncio.sleep(self.heartbeat_interval)
            
            current_time = time.time()
            disconnected = []
            
            for websocket, metadata in list(self.active_connections.items()):
                # Check for stale connections (no response in 60s)
                if current_time - metadata["last_ping"] > 60:
                    logger.warning(f"Stale connection detected: {metadata.get('client_id')}")
                    disconnected.append(websocket)
                    continue
                
                # Send ping
                try:
                    await websocket.send_json({"type": "ping", "timestamp": current_time})
                    metadata["last_ping"] = current_time
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
                    disconnected.append(websocket)
            
            # Cleanup stale connections
            for ws in disconnected:
                self.disconnect(ws)
        
        # Reset task when no connections
        self._heartbeat_task = None
    
    def update_ping(self, websocket: WebSocket):
        """Update last ping time for connection (called on pong)."""
        if websocket in self.active_connections:
            self.active_connections[websocket]["last_ping"] = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_messages = sum(
            meta["message_count"] 
            for meta in self.active_connections.values()
        )
        
        return {
            "total_connections": len(self.active_connections),
            "total_channels": len(self.channels),
            "total_messages_sent": total_messages,
            "channels": {
                channel: len(subscribers) 
                for channel, subscribers in self.channels.items()
            },
            "uptime_seconds": time.time() - min(
                (meta["connected_at"] for meta in self.active_connections.values()),
                default=time.time()
            )
        }


# Global connection manager instance
manager = ConnectionManager()
