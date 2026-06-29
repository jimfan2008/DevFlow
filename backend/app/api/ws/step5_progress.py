import json as _json
import os
import re as _re
import glob
import logging
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws.auth import verify_token
from app.services.workflow_engine import WorkflowEngine
from app.services.gateway_client import GatewayClient
from app.models.project import Project
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_active_connections: Dict[str, List[WebSocket]] = {}

ENV_SETUP_DIMENSIONS = [
    {"key": "environment_availability", "label": "环境可用性", "description": "开发环境是否可正常运行"},
    {"key": "config_correctness", "label": "配置正确性", "description": "配置文件是否完整、正确"},
    {"key": "dependency_completeness", "label": "依赖完整性", "description": "依赖包、工具链是否齐全"},
]


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
                logger.info(f"Step5 WS received: {data}")
                payload = _json.loads(data)
                action = payload.get("action", "")
                logger.info(f"Step5 action: {action}")

                if action == "execute":
                    logger.info(f"Step5: Starting _run_step5 for project {project_id}")
                    should_close = await _run_step5(websocket, project_id, db)
                    logger.info(f"Step5: _run_step5 completed for project {project_id}")
                    if should_close:
                        break

                elif action == "subscribe":
                    logger.info(f"Step5: Subscribed for project {project_id}")
                    await websocket.send_json({"type": "subscribed", "message": "已订阅实时状态"})

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


async def _run_step5(websocket: WebSocket, project_id: str, db) -> bool:
    """执行步骤5"""

    # Register this WS for broadcasts (dedup)
    if websocket not in _active_connections.get(project_id, []):
        _active_connections.setdefault(project_id, []).append(websocket)

    try:
        engine = WorkflowEngine(project_id=project_id, db=db)
        engine.advance_step(5)

        # Gather context from previous steps
        step3 = engine.get_step3_artifacts() or {}
        requirement = (step3.get("doc_content") or step3.get("content") or
                       step3.get("requirement") or step3.get("srs") or "")
        step4 = engine.get_step4_artifacts() or {}
        step2 = engine.get_step2_artifacts() or {}
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        # Use aggregated design_doc from step4 orchestrator (new: step4_N_result keys, old: sub_flow_results)
        design_summary = step4.get("design_doc") or ""
        if not design_summary:
            subs = step4.get("sub_flow_results") or []
            parts = []
            for doc in subs:
                label = doc.get("label", "")
                content = doc.get("content", "")
                if content:
                    parts.append(f"\n=== {label} ===\n{content}\n")
            design_summary = "\n".join(parts)

        # Resolve project info
        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            await websocket.send_json({"type": "error", "message": "Project not found"})
            return True
        slug = proj.slug or project_id.replace("-", "")
        docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        proj_name = proj.name
        proj_desc = proj.description or ""

        engine.save_step5_artifacts({"status": "generating", "message": "🔧 后富正在建立开发环境..."})
        await websocket.send_json({"type": "progress", "message": "🔧 后富正在建立开发环境..."})

        # Check for existing artifacts (resume case)
        existing = engine.get_step5_artifacts() or {}
        if existing.get("qa_passed") and existing.get("doc_path") and os.path.exists(existing["doc_path"]):
            engine.save_step5_artifacts({**existing, "status": "done", "message": "♻️ 续跑：环境配置已通过检验"})
            engine.complete_step(5)
            engine.pass_qa(5)
            await websocket.send_json({"type": "done", "message": "✅ 开发环境已建立完毕（续跑）"})
            return True

        # 发一条提示词给 houfu，不循环不收斂
        gen_path = os.path.join(docs_dir, f"{slug}_env_V1.md")
        await websocket.send_json({"type": "progress", "message": "📤 正在向后富（HouFu）Agent发送开发环境搭建请求..."})

        prompt = (
            "你是资深CI/CD工程师后富（HouFu），负责建立软件开发环境。\n\n"
            f"=== 需求文档 ===\n{requirement}\n\n"
            f"=== 设计文档 ===\n{design_summary}\n\n"
            "读取本项目的需求文档和设计文档，建立本项目的开发环境。\n"
            f"请将部署配置保存到：{gen_path}\n"
            "要求：代码仓库初始化、框架搭建、依赖配置、数据库初始化、CI/CD流水线配置\n"
            "不要输出推理过程。"
        )

        houfu = GatewayClient(profile_name="houfu", timeout=1200)
        chunks = []
        try:
            async for chunk in houfu.chat_isolated(
                messages=[{"role": "user", "content": prompt}],
                project_id=project_id, project_name=proj_name,
                project_description=proj_desc, core_goal=core_goal,
                agent_name="后富（HouFu）CI/CD工程师",
                stream=True, max_tokens=64000,
            ):
                if chunk.strip():
                    chunks.append(chunk)
                    await websocket.send_json({"type": "progress", "content": chunk})

        except Exception as e:
            logger.error(f"Step5 houfu调用失败: {e}", exc_info=True)
            await websocket.send_json({"type": "error", "message": f"❌ 后富执行失败，已通知海梅处理: {str(e)[:100]}"})
            engine.reset_step(5)
            return True

        content = "".join(chunks).strip()
        with open(gen_path, "w", encoding="utf-8") as f:
            f.write(content)

        engine.save_step5_artifacts({
            "env_info": content, "doc_path": gen_path,
            "status": "done", "message": "✅ 开发环境已建立完毕",
        })
        engine.complete_step(5)
        engine.pass_qa(5)
        await websocket.send_json({"type": "done", "message": "✅ 开发环境已建立完毕"})
        return True

    except Exception as e:
        logger.error(f"Step5 execution error: {e}", exc_info=True)
        try:
            err_engine = WorkflowEngine(project_id=project_id, db=db)
            err_engine.reset_step(5)
        except Exception:
            pass
        await websocket.send_json({"type": "error", "message": f"❌ 步骤5失败，已通知海梅处理"})
        return True
