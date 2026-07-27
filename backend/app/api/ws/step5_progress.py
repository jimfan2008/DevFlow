"""Step5 WebSocket handler — splits into step5_1 (config) then step5_2 (setup)."""
import json as _json
import os
import logging
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws.auth import verify_token
from app.services.workflow_engine import WorkflowEngine

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


@router.websocket("/step5/progress/{project_id}")
async def step5_progress_ws(websocket: WebSocket, project_id: str,
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

                if action == "execute":
                    await _run_step5_chain(websocket, project_id, db)

                elif action == "subscribe":
                    await websocket.send_json({"type": "subscribed", "message": "已订阅实时状态"})
                    # Send current status
                    try:
                        engine = WorkflowEngine(project_id=project_id, db=db)
                        artifacts = engine.get_step5_artifacts() or {}
                        status = artifacts.get("status", "pending")
                        message = artifacts.get("message", "")
                        if status and status != "pending":
                            await websocket.send_json({"type": "progress", "message": f"当前状态: {message or status}"})
                    except Exception as e:
                        logger.error(f"Step5 WS: failed to send status: {e}")

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        finally:
            conns = _active_connections.get(project_id, [])
            if websocket in conns:
                conns.remove(websocket)
    except Exception as e:
        logger.error(f"Step5 WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()


async def _run_step5_chain(websocket: WebSocket, project_id: str, db):
    """Execute step5_1 (config generation) then step5_2 (environment setup)."""
    logger.info(f"[STEP5] _run_step5_chain 开始: project_id={project_id}")

    if websocket not in _active_connections.get(project_id, []):
        _active_connections.setdefault(project_id, []).append(websocket)

    try:
        engine = WorkflowEngine(project_id=project_id, db=db)

        # Check if fully completed
        existing = engine.get_step5_artifacts() or {}
        if existing.get("qa_passed") and existing.get("setup_doc_path"):
            await websocket.send_json({"type": "progress", "message": "♻️ 环境搭建已通过检验"})
            await websocket.send_json({"type": "done", "message": "✅ 开发环境已建立完毕（续跑）"})
            return

        # Check if step5_1 already passed — skip to step5_2
        skip_to_5_2 = existing.get("qa_passed") and existing.get("doc_path") and not existing.get("setup_doc_path")

        from app.models.user import User
        mock_user = db.query(User).first()
        if not mock_user:
            await websocket.send_json({"type": "error", "message": "❌ 无可用用户"})
            return

        if not skip_to_5_2:
            # ── Phase 1: step5_1 — Generate env config file ──
            await websocket.send_json({"type": "progress", "message": "📋 阶段1/2：后富生成环境配置文件..."})

            from app.api.ws.step5_1_progress import (
                _active_connections as conns_51,
            )
            forwarder_51 = _Forwarder(websocket)
            conns_51.setdefault(project_id, []).append(forwarder_51)

            try:
                from app.api.workflow.step5_1 import execute_step5_1_async

                resp = await execute_step5_1_async(project_id=project_id, db=db, current_user=mock_user)
                if hasattr(resp, 'code') and resp.code != 0:
                    await websocket.send_json({"type": "error", "message": f"❌ 步骤5_1启动失败: {resp.message}"})
                    return
            except Exception as e:
                logger.error(f"[STEP5] step5_1 execute failed: {e}", exc_info=True)
                await websocket.send_json({"type": "error", "message": f"❌ 步骤5_1启动失败: {str(e)[:200]}"})
                return
            finally:
                conns_51.get(project_id, []).remove(forwarder_51)

            # Wait for step5_1 to complete (poll status)
            await _wait_for_step(project_id, db, websocket, phase="config generation")

            # Check if step5_1 passed
            engine2 = WorkflowEngine(project_id=project_id, db=db)
            artifacts = engine2.get_step5_artifacts() or {}
            if not artifacts.get("qa_passed") or not artifacts.get("doc_path"):
                await websocket.send_json({"type": "error", "message": "❌ 环境配置文件未通过检验，无法进入阶段2"})
                return
        else:
            await websocket.send_json({"type": "progress", "message": "♻️ 步骤5_1已通过检验，跳过直接进入阶段2..."})

        # ── Phase 2: step5_2 — Execute environment setup ──
        # Set step5 to in_progress directly (bypass advance_step supervision check
        # because step5 is a sub-step chain — step4 completion is not required)
        from datetime import datetime, timezone
        from sqlalchemy import text as _sa_text
        db.execute(
            _sa_text("UPDATE workflow_steps SET status='in_progress', started_at=:now WHERE project_id=:pid AND step_number=5"),
            {"now": datetime.now(timezone.utc).isoformat(), "pid": project_id}
        )
        db.commit()
        logger.info(f"[STEP5] 已直接设置 step5 状态为 in_progress")

        await websocket.send_json({"type": "progress", "message": "📋 阶段2/2：后富执行环境搭建..."})

        from app.api.ws.step5_2_progress import (
            _active_connections as conns_52,
        )
        forwarder_52 = _Forwarder(websocket)
        conns_52.setdefault(project_id, []).append(forwarder_52)

        try:
            from app.api.workflow.step5_2 import execute_step5_2_async

            resp = await execute_step5_2_async(project_id=project_id, db=db, current_user=mock_user, resume=True)
            if hasattr(resp, 'code') and resp.code != 0:
                await websocket.send_json({"type": "error", "message": f"❌ 步骤5_2启动失败: {resp.message}"})
                return
        except Exception as e:
            logger.error(f"[STEP5] step5_2 execute failed: {e}", exc_info=True)
            await websocket.send_json({"type": "error", "message": f"❌ 步骤5_2启动失败: {str(e)[:200]}"})
            return
        finally:
            conns_52.get(project_id, []).remove(forwarder_52)

        # Wait for step5_2 to complete
        await _wait_for_step(project_id, db, websocket, phase="environment setup")

        # Final check
        engine3 = WorkflowEngine(project_id=project_id, db=db)
        final = engine3.get_step5_artifacts() or {}
        if final.get("qa_passed"):
            # ── Auto-start step6 ──
            await websocket.send_json({"type": "progress", "message": "🚀 环境搭建通过检验，自动启动步骤6（制订TDD计划）..."})
            try:
                import json as _json_step6

                # Set step6 to in_progress
                db.execute(
                    _sa_text("UPDATE workflow_steps SET status='in_progress', started_at=:now, output_artifacts=:arts WHERE project_id=:pid AND step_number=6"),
                    {"now": datetime.now(timezone.utc).isoformat(), "arts": _json_step6.dumps({"status": "generating", "message": "📋 海梅正在制订TDD测试用例编写计划..."}), "pid": project_id}
                )
                db.execute(
                    _sa_text("UPDATE projects SET current_step=6 WHERE id=:pid"),
                    {"pid": project_id}
                )
                db.commit()

                # Forward step6 WS messages to client
                from app.api.ws.step6_progress import _active_connections as conns_6
                forwarder_6 = _Forwarder(websocket)
                conns_6.setdefault(project_id, []).append(forwarder_6)

                try:
                    from app.api.workflow.step6 import execute_step6_async
                    if mock_user:
                        resp = await execute_step6_async(project_id=project_id, db=db, current_user=mock_user)
                        if hasattr(resp, 'code') and resp.code != 0:
                            await websocket.send_json({"type": "progress", "message": f"⚠️ 步骤6启动异常: {resp.message}"})
                except Exception as e6:
                    logger.error(f"[STEP5] step6 auto-start failed: {e6}", exc_info=True)
                    await websocket.send_json({"type": "progress", "message": f"⚠️ 步骤6自动启动失败: {str(e6)[:200]}"})
                finally:
                    conns_6.get(project_id, []).remove(forwarder_6)

                await websocket.send_json({"type": "auto_next", "step": 6, "message": "✅ 步骤5完成，已自动启动步骤6"})
            except Exception as e_auto:
                logger.error(f"[STEP5] step6 auto-start error: {e_auto}", exc_info=True)
                await websocket.send_json({"type": "done", "message": "✅ 开发环境已建立完毕（步骤6自动启动失败，请手动执行）"})
        else:
            await websocket.send_json({"type": "error", "message": "❌ 环境搭建未通过检验"})

    except Exception as e:
        logger.error(f"[STEP5] _run_step5_chain 异常: {e}", exc_info=True)
        await websocket.send_json({"type": "error", "message": f"❌ 步骤5失败: {str(e)[:200]}"})


async def _wait_for_step(project_id: str, db, websocket: WebSocket, phase: str, timeout: int = 1800):
    """Poll step status until completed or timed out."""
    import asyncio
    import time
    start = time.time()
    while time.time() - start < timeout:
        await asyncio.sleep(5)
        try:
            from app.database import SessionLocal
            poll_db = SessionLocal()
            try:
                engine = WorkflowEngine(project_id=project_id, db=poll_db)
                artifacts = engine.get_step5_artifacts() or {}
                status = artifacts.get("status", "")
                if status == "done":
                    return True
                if status == "error":
                    msg = artifacts.get("message", "未知错误")
                    await websocket.send_json({"type": "error", "message": f"❌ {phase}失败: {msg}"})
                    return False
                if status == "generating":
                    msg = artifacts.get("message", "")
                    if msg:
                        await websocket.send_json({"type": "progress", "message": msg})
            finally:
                poll_db.close()
        except Exception as e:
            logger.error(f"[STEP5] poll error: {e}")
    await websocket.send_json({"type": "error", "message": f"❌ {phase}超时"})
    return False


class _Forwarder:
    """Minimal WS-like object that forwards send_json to the real client WS."""
    def __init__(self, target_ws: WebSocket):
        self._target = target_ws

    async def send_json(self, msg: dict):
        try:
            await self._target.send_json(msg)
        except Exception:
            pass
