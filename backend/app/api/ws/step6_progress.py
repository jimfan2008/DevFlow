import json as _json
import logging
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()

_active_connections: Dict[str, List[WebSocket]] = {}


async def broadcast(project_id: str, message: dict):
    conns = _active_connections.get(project_id, [])
    logger.info(f"[STEP6_BROADCAST] project={project_id} connections={len(conns)} msg_type={message.get('type','?')}")
    dead: List[WebSocket] = []
    for ws in conns:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    if dead:
        _active_connections[project_id] = [
            ws for ws in conns if ws not in dead
        ]


@router.websocket("/step6/progress/{project_id}")
async def step6_progress_ws(websocket: WebSocket, project_id: str,
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
        logger.info(f"[STEP6_WS] client connected: project={project_id} total={len(_active_connections.get(project_id, []))}")
        # Send current step status so client doesn't miss early broadcasts
        try:
            from sqlalchemy import text as _text
            row = db.execute(
                _text("SELECT status, output_artifacts FROM workflow_steps WHERE project_id=:pid AND step_number=6"),
                {"pid": project_id}
            ).fetchone()
            if row:
                status = row[0]
                arts = _json.loads(row[1]) if row[1] else {}
                await websocket.send_json({"type": "progress", "message": f"📋 当前状态: {status}"})
                if arts.get("message"):
                    await websocket.send_json({"type": "progress", "message": arts["message"]})
        except Exception as e:
            logger.error(f"Step6 WS init status error: {e}")
        try:
            while True:
                data = await websocket.receive_text()
                payload = _json.loads(data)
                action = payload.get("action", "")
                if action == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        finally:
            conns = _active_connections.get(project_id, [])
            if websocket in conns:
                conns.remove(websocket)
    except Exception as e:
        logger.error(f"Step6 WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()
