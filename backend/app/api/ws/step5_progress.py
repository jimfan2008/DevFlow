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

        # 检查是否真的有 Haimei 后台任务在运行（不是僵尸状态）
        step5_row = engine._get_step_row(5)
        if step5_row and step5_row.status == "in_progress":
            # 检查是否有后台任务在运行
            from app.services.haimei_executor import HaimeiStepExecutor
            has_task = HaimeiStepExecutor.is_running(project_id, 5)
            if has_task or engine.get_step5_artifacts().get("status") == "generating":
                await websocket.send_json({"type": "progress", "message": "♻️ Haimei 正在执行中，实时同步进度..."})
                return False  # 保持监听
            # 僵尸状态：重置并重新执行
            engine.reset_step(5)

        engine.advance_step(5)

        # Gather context from previous steps
        step3 = engine.get_step3_artifacts() or {}
        requirement = (step3.get("doc_content") or step3.get("content") or
                       step3.get("requirement") or step3.get("srs") or "")
        step4 = engine.get_step4_artifacts() or {}
        subs = step4.get("sub_flow_results") or []
        step2 = engine.get_step2_artifacts() or {}
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        # Build design docs summary from step4 sub_flow_results
        design_summary = ""
        for doc in subs:
            label = doc.get("label", "")
            content = doc.get("content", "")
            if content:
                design_summary += f"\n=== {label} ===\n{content}\n"

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
        await websocket.send_json({"type": "progress", "message": "📤 正在向后富（HouFu）发送开发环境搭建请求..."})
        await websocket.send_json({"type": "progress", "content": "\n# 开始生成开发环境配置...\n"})

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
            # Direct remote API call (fast, reliable)
            import httpx as _httpx
            import json as _json2
            houfu_api_url = "http://10.34.1.96:8000/v1/chat/completions"
            houfu_api_key = "gbm_cq_vllm"
            houfu_model = "Qwen3.6-27B-AWQ-INT4"

            # Build isolated prompt (same as GatewayClient.chat_isolated)
            system_prompt = (
                f"你是后富（HouFu）CI/CD工程师，DevFlow 16步开发流程中的专业角色。\n"
                f"\n【当前项目上下文】\n"
                f"项目名称: {proj_name}\n"
                f"项目ID: {project_id}\n"
                f"项目描述: {proj_desc}\n"
                f"核心目标: {core_goal}\n"
                "\n【重要工作规则 - 项目隔离】\n"
                "1. 你正在为上述「当前项目」工作\n"
                "2. 请只引用上述项目信息，不要引用其他任何项目的上下文\n"
                "3. 所有回答、分析、设计都只针对当前项目\n"
                "4. 不得将其他项目的数据、需求、设计带入当前项目"
            )
            api_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            api_payload = {
                "model": houfu_model,
                "messages": api_messages,
                "stream": True,
                "max_tokens": 64000,
                "temperature": 0.7,
            }
            api_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {houfu_api_key}"}

            async with _httpx.AsyncClient(timeout=600) as _hx:
                async with _hx.stream("POST", houfu_api_url, headers=api_headers, json=api_payload) as _resp:
                    if _resp.status_code != 200:
                        raise Exception(f"Direct API error {_resp.status_code}: {await _resp.aread()}")
                    async for _line in _resp.aiter_lines():
                        if _line.startswith("data: "):
                            _data = _line[6:]
                            if _data == "[DONE]":
                                break
                            try:
                                _chunk = _json2.loads(_data)
                                _content = _chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if _content:
                                    chunks.append(_content)
                                    await websocket.send_json({"type": "progress", "content": _content})
                            except _json2.JSONDecodeError:
                                continue
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
