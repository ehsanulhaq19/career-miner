"""WebSocket connection manager for broadcasting messages to channels."""

import json
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and broadcasts messages to channels."""

    def __init__(self) -> None:
        """Initialize the connection manager with empty channel subscriptions."""
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(
        self,
        websocket: WebSocket,
        channel: str,
    ) -> None:
        """
        Accept a WebSocket connection and add it to the specified channel.
        """
        await websocket.accept()
        self._channels[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """
        Remove a WebSocket connection from the specified channel.
        """
        self._channels[channel].discard(websocket)
        if not self._channels[channel]:
            del self._channels[channel]

    async def send_to_channel(
        self,
        channel: str,
        message_type: str,
        data: dict,
    ) -> None:
        """
        Send a JSON message to all connections in the specified channel.
        Message format: {"type": message_type, "data": data}
        """
        message = json.dumps({"type": message_type, "data": data})
        disconnected = set()
        for connection in self._channels.get(channel, set()):
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self._channels[channel].discard(conn)

    async def broadcast_to_channel_prefix(
        self,
        channel_prefix: str,
        message_type: str,
        data: dict,
    ) -> None:
        """
        Send a JSON message to all channels that start with the given prefix.
        Used for broadcasting to /ws/scrap_job/* channels.
        """
        message = json.dumps({"type": message_type, "data": data})
        disconnected: list[tuple[str, WebSocket]] = []
        for channel, connections in list(self._channels.items()):
            if channel.startswith(channel_prefix):
                for connection in connections:
                    try:
                        await connection.send_text(message)
                    except Exception:
                        disconnected.append((channel, connection))
        for channel, conn in disconnected:
            self._channels[channel].discard(conn)


connection_manager = ConnectionManager()
