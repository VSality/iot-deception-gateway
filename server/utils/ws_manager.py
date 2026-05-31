from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    @property
    def has_clients(self) -> bool:
        return len(self.active_connections) > 0

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast_json(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                if connection.client_state != WebSocketState.CONNECTED:
                    dead.append(connection)
                    continue
                await connection.send_json(payload)
            except (WebSocketDisconnect, RuntimeError, ConnectionError):
                dead.append(connection)
        for ws in dead:
            self.disconnect(ws)
