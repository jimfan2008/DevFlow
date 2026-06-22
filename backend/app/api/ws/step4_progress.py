import json as _json
import asyncio
import logging
import os
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


@router.websocket("/step4/progress/{project_id}")
async def step4_progress_ws(websocket: WebSocket, project_id: str,
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
                    await _run_step4(project_id, db)
                    await websocket.send_json({"type": "done", "message": "✅ 步骤4：全部设计文档已完成"})
                    break
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        finally:
            conns = _active_connections.get(project_id, [])
            if websocket in conns:
                conns.remove(websocket)
    except Exception as e:
        logger.error(f"Step4 WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()


async def _run_step4(project_id: str, db):
    """调用houwang Agent生成4份设计文档"""
    from app.services.workflow_engine import WorkflowEngine
    from app.models.project import Project
    from app.config import settings
    from app.services.gateway_client import GatewayClient

    engine = WorkflowEngine(project_id=project_id, db=db)

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or
                   step3.get("requirement") or step3.get("srs") or "")
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        await broadcast(project_id, {"type": "error", "message": "项目不存在"})
        return
    slug = proj.slug or project_id.replace("-", "")
    docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    proj_name = proj.name or ""
    proj_desc = proj.description or ""

    engine.advance_step(4)
    await broadcast(project_id, {"type": "stage", "message": "🏗️ 后旺架构师团队启动，开始生成设计文档..."})

    sub_flows = [
        {"doc_type": "ARCHITECTURE", "label": "架构设计文档", "prefix": "arch",
         "instruction": (
             "你是资深架构师后旺（HouWang），负责设计系统架构。\n"
             f"项目：{proj_name}\n核心目标：{core_goal}\n"
             f"需求文档：{requirement[:3000]}\n"
             "请输出完整的技术架构设计文档，包括：系统架构图、模块划分、技术选型、接口设计。\n"
             "不要输出推理过程。"
         )},
        {"doc_type": "FRONTEND", "label": "前端设计文档", "prefix": "frontend",
         "instruction": (
             "你是资深前端架构师后旺（HouWang），负责设计前端架构。\n"
             f"项目：{proj_name}\n核心目标：{core_goal}\n"
             f"需求文档：{requirement[:3000]}\n"
             "请输出完整的前端设计文档，包括：组件树、状态管理、路由设计、UI框架选型。\n"
             "不要输出推理过程。"
         )},
        {"doc_type": "BACKEND", "label": "后端设计文档", "prefix": "backend",
         "instruction": (
             "你是资深后端架构师后旺（HouWang），负责设计后端架构。\n"
             f"项目：{proj_name}\n核心目标：{core_goal}\n"
             f"需求文档：{requirement[:3000]}\n"
             "请输出完整的后端设计文档，包括：API设计、服务拆分、数据流、中间件选型。\n"
             "不要输出推理过程。"
         )},
        {"doc_type": "DATABASE", "label": "数据库设计脚本", "prefix": "db",
         "instruction": (
             "你是资深数据库架构师后旺（HouWang），负责设计数据库。\n"
             f"项目：{proj_name}\n核心目标：{core_goal}\n"
             f"需求文档：{requirement[:3000]}\n"
             "请输出完整的数据库设计文档，包括：ER图、表结构、索引策略、迁移脚本。\n"
             "不要输出推理过程。"
         )},
    ]

    async def run_one(cfg):
        doc_type = cfg["doc_type"]
        label = cfg["label"]
        prefix = cfg["prefix"]
        instruction = cfg["instruction"]

        await broadcast(project_id, {
            "type": "stage", "message": f"📝 {label}：houwang Agent处理中...",
            "subflow": doc_type,
        })

        client = GatewayClient(profile_name="houwang", timeout=1200)
        chunks = []
        async for chunk in client.chat_isolated(
            messages=[{"role": "user", "content": instruction}],
            project_id=project_id, project_name=proj_name,
            project_description=proj_desc, core_goal=core_goal,
            agent_name=f"后旺-{doc_type}设计师",
            stream=True, max_tokens=64000,
        ):
            if chunk.strip():
                chunks.append(chunk)
                await broadcast(project_id, {
                    "type": "progress", "content": chunk,
                    "subflow": doc_type,
                })

        content = "".join(chunks).strip()
        gen_path = os.path.join(docs_dir, f"{slug}_{prefix}_V1.md")
        with open(gen_path, "w", encoding="utf-8") as f:
            f.write(content)

        await broadcast(project_id, {
            "type": "stage", "message": f"✅ {label}：houwang完成",
            "subflow": doc_type,
        })
        return {"doc_type": doc_type, "content": content, "path": gen_path}

    tasks = [run_one(cfg) for cfg in sub_flows]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        await broadcast(project_id, {"type": "error", "message": f"❌ 文档生成失败: {errors[0]}"})
        engine.reset_step(4)
        return

    merged = {}
    for r in results:
        if isinstance(r, dict):
            merged[f"design_doc_{r['doc_type'].lower()}"] = r["content"]
    merged["status"] = "done"
    engine.save_step4_artifacts(merged)
    engine.complete_step(4)
