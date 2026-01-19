"""WebSocket endpoint for real-time updates."""

import asyncio
import json
from datetime import datetime
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.clickhouse.client import get_clickhouse_client

logger = get_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._broadcast_task = None

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(
            "WebSocket connected",
            connections=len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection."""
        self.active_connections.discard(websocket)
        logger.info(
            "WebSocket disconnected",
            connections=len(self.active_connections),
        )

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message, default=str)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.active_connections.discard(connection)

    async def start_broadcast_loop(self, interval: float = 5.0) -> None:
        """Start the background broadcast loop."""
        logger.info("Starting WebSocket broadcast loop", interval=interval)

        while True:
            try:
                if self.active_connections:
                    # Get real-time metrics
                    clickhouse = await get_clickhouse_client()
                    metrics = await clickhouse.get_realtime_metrics()

                    await self.broadcast({
                        "type": "metrics",
                        "data": metrics,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except Exception as e:
                logger.error("Broadcast error", error=str(e))

            await asyncio.sleep(interval)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time event updates.

    Clients receive periodic updates with current metrics.
    """
    await manager.connect(websocket)

    try:
        # Send initial data
        clickhouse = await get_clickhouse_client()
        metrics = await clickhouse.get_realtime_metrics()

        await websocket.send_json({
            "type": "initial",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (ping/pong, or commands)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )

                # Handle commands
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                    elif message.get("type") == "subscribe":
                        # Handle subscription to specific event types
                        await websocket.send_json({
                            "type": "subscribed",
                            "channels": message.get("channels", []),
                        })
                except json.JSONDecodeError:
                    pass

            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_json({
                        "type": "keepalive",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket) -> None:
    """
    WebSocket endpoint specifically for metrics streaming.

    Sends metrics updates at a configurable interval.
    """
    await manager.connect(websocket)

    try:
        interval = 5.0  # Default interval

        # Handle initial configuration
        try:
            config = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=5.0,
            )
            interval = min(max(config.get("interval", 5.0), 1.0), 60.0)
        except (asyncio.TimeoutError, Exception):
            pass

        # Stream metrics
        while True:
            try:
                clickhouse = await get_clickhouse_client()
                metrics = await clickhouse.get_realtime_metrics()

                await websocket.send_json({
                    "type": "metrics",
                    "data": metrics,
                    "interval": interval,
                })

            except Exception as e:
                logger.error("Error sending metrics", error=str(e))
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to retrieve metrics",
                })

            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info("Metrics WebSocket disconnected")
    except Exception as e:
        logger.error("Metrics WebSocket error", error=str(e))
    finally:
        manager.disconnect(websocket)
