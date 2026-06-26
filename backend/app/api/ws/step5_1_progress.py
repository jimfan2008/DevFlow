import json as _json
import logging
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()

_active_connections: Dict[str, List[WebSocket]] = {}


async def broadcast(project_id: str, message: dict):
    dead: List[WebSocket] = []
    for ws in _active_connections.get(project_id, []):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    if dead:
        _active_connections[project_id] = [
            ws for ws in _active_connections.get(project_id, [])
            if ws not in dead
        ]


@router.websocket("/step5_1/progress/{project_id}")
async def step5_1_progress_ws(websocket: WebSocket, project_id: str,
                               token: str = Query(...)):
    await websocket.accept()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = await verify_token(token, db)
        if not user:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close()
            return

        _active_connections.setdefault(project_id, []).append(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                payload = _json.loads(data)
                action = payload.get("action", "")

                if action == "subscribe":
                    await websocket.send_json({"type": "subscribed", "message": "已订阅步骤5_1实时状态"})

                    # Send current status on connect
                    try:
                        from app.services.workflow_engine import WorkflowEngine
                        engine = WorkflowEngine(project_id=project_id, db=db)
                        artifacts = engine.get_step5_artifacts() or {}
                        status = artifacts.get("status", "pending")
                        message = artifacts.get("message", "")
                        if status and status != "pending":
                            await websocket.send_json({"type": "progress", "message": f"当前状态: {message or status}"})
                    except Exception as e:
                        logger.error(f"Step5_1 WS: failed to send status: {e}")

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        finally:
            conns = _active_connections.get(project_id, [])
            if websocket in conns:
                conns.remove(websocket)
    except Exception as e:
        logger.error(f"Step5_1 WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()
