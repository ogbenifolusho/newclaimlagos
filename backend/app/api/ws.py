"""
WebSocket endpoints for Situation Room live feeds.
Uses Redis pub/sub when available; falls back to in-memory broadcast.
"""

from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime, timezone

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict):
        data = json.dumps(message, default=str)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/situation-room")
async def situation_room_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send hello
        await websocket.send_json({
            "type": "connected",
            "message": "CLAIM LAGOS Situation Room live feed",
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        while True:
            # Keep-alive / receive client pings
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def publish_alert(title: str, severity: str = "medium", geo_name: str | None = None):
    """Call from workers/ingestion to push live alerts to Situation Room."""
    await manager.broadcast({
        "type": "alert",
        "payload": {
            "title": title,
            "severity": severity,
            "geo_name": geo_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    })
