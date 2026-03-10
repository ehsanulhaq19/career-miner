"""WebSocket API endpoints."""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.security import verify_token
from app.modules.websocket.manager import connection_manager

router = APIRouter()

SCRAP_JOB_CHANNEL_PREFIX = "/ws/scrap_job/"


@router.websocket("/ws/scrap_job/{user_id}")
async def scrap_job_websocket(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...),
) -> None:
    """
    WebSocket endpoint for scrap job updates.
    Clients connect to receive real-time scrap job status updates.
    Requires valid JWT token in query parameter.
    """
    try:
        payload = verify_token(token)
        token_user_id = payload.get("sub")
        if token_user_id is None or int(token_user_id) != user_id:
            await websocket.close(code=4001)
            return
    except (JWTError, ValueError):
        await websocket.close(code=4001)
        return

    channel = f"{SCRAP_JOB_CHANNEL_PREFIX}{user_id}"
    await connection_manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, channel)
