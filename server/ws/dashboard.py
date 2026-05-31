import asyncio
import os

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from utils.ws_events import ip_state_event, log_event
from utils.ws_manager import ConnectionManager

manager = ConnectionManager()

_DEMO_MESSAGES = [
    ("INFO", "Traffic analyzer idle — no anomalies in last interval"),
    ("WARNING", "Elevated request rate from 192.168.1.88 (monitoring)"),
    ("ALERT", "Honeypot path probe blocked — client moved to shadow plane"),
]

_demo_task: asyncio.Task | None = None


def _demo_logs_enabled() -> bool:
    return os.getenv("ENABLE_WS_DEMO_LOGS", "0").lower() in ("1", "true", "yes")


async def _demo_log_loop() -> None:
    index = 0
    while True:
        await asyncio.sleep(5)
        if not manager.has_clients:
            continue
        level, message = _DEMO_MESSAGES[index % len(_DEMO_MESSAGES)]
        index += 1
        await manager.broadcast_json(log_event(level, message))


async def _dashboard_websocket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json(ip_state_event())
        await websocket.send_json(
            log_event("INFO", "Dashboard WebSocket connected")
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


def register_dashboard_websocket(app: FastAPI) -> None:
    @app.websocket("/ws/dashboard")
    async def dashboard_ws_endpoint(websocket: WebSocket) -> None:
        await _dashboard_websocket(websocket)

    @app.on_event("startup")
    async def _start_demo_log_task() -> None:
        global _demo_task
        if not _demo_logs_enabled():
            return
        _demo_task = asyncio.create_task(_demo_log_loop())

    @app.on_event("shutdown")
    async def _stop_demo_log_task() -> None:
        global _demo_task
        if _demo_task is not None:
            _demo_task.cancel()
            try:
                await _demo_task
            except asyncio.CancelledError:
                pass
            _demo_task = None
