import json as _json
import asyncio
import logging
import os
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws.auth import verify_token
from app.api.ws.step3_qa import _inspect_via_subagent

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
    """调用houwang+hourong 4份设计文档生成 + 逐轮收敛检验"""
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
         "dim_key": "arch_reasonableness",
         "instruction": (
             "你是资深架构师后旺（HouWang），负责设计系统架构。\n"
             f"项目：{proj_name}\n核心目标：{core_goal}\n"
             f"需求文档：{requirement[:3000]}\n"
             "请输出完整的技术架构设计文档，包括：系统架构图、模块划分、技术选型、接口设计。\n"
             "不要输出推理过程。"
         )},
        {"doc_type": "FRONTEND", "label": "前端设计文档", "prefix": "frontend",
         "dim_key": "frontend_feasibility",
         "instruction": (
             "你是资深前端架构师后旺（HouWang），负责设计前端架构。\n"
             f"项目：{proj_name}\n核心目标：{core_goal}\n"
             f"需求文档：{requirement[:3000]}\n"
             "请输出完整的前端设计文档，包括：组件树、状态管理、路由设计、UI框架选型。\n"
             "不要输出推理过程。"
         )},
        {"doc_type": "BACKEND", "label": "后端设计文档", "prefix": "backend",
         "dim_key": "backend_feasibility",
         "instruction": (
             "你是资深后端架构师后旺（HouWang），负责设计后端架构。\n"
             f"项目：{proj_name}\n核心目标：{core_goal}\n"
             f"需求文档：{requirement[:3000]}\n"
             "请输出完整的后端设计文档，包括：API设计、服务拆分、数据流、中间件选型。\n"
             "不要输出推理过程。"
         )},
        {"doc_type": "DATABASE", "label": "数据库设计脚本", "prefix": "db",
         "dim_key": "database_design",
         "instruction": (
             "你是资深数据库架构师后旺（HouWang），负责设计数据库。\n"
             f"项目：{proj_name}\n核心目标：{core_goal}\n"
             f"需求文档：{requirement[:3000]}\n"
             "请输出完整的数据库设计文档，包括：ER图、表结构、索引策略、迁移脚本。\n"
             "不要输出推理过程。"
         )},
    ]

    merged = {}
    convergence_log = []

    for cfg in sub_flows:
        doc_type = cfg["doc_type"]
        label = cfg["label"]
        prefix = cfg["prefix"]
        dim_key = cfg["dim_key"]
        instruction = cfg["instruction"]

        await broadcast(project_id, {
            "type": "stage",
            "message": f"📝 {label}：houwang 开始生成（第1轮）...",
            "subflow": doc_type,
        })

        content = ""
        final_path = ""
        failed_dim_keys = None

        for fix_round in range(1, 11):
            nv = fix_round
            gen_path = os.path.join(docs_dir, f"{slug}_{prefix}_V{nv}.md")

            if fix_round == 1:
                client = GatewayClient(profile_name="houwang", timeout=1200)
                chunks = []
                async for chunk in client.chat_isolated(
                    messages=[{"role": "user", "content": instruction}],
                    project_id=project_id, project_name=proj_name,
                    project_description=proj_desc, core_goal=core_goal,
                    agent_name=f"后旺-{doc_type}设计师",
                    stream=True, max_tokens=64000,
                    project_slug=slug,
                ):
                    if chunk.strip():
                        chunks.append(chunk)
                        await broadcast(project_id, {
                            "type": "progress", "content": chunk,
                            "subflow": doc_type,
                        })
                content = "".join(chunks).strip()
            else:
                feedback_lines = []
                for cr in convergence_log:
                    if cr.get("dim_key") == dim_key:
                        for r in cr.get("results", []):
                            if not r.get("passed", True) and r.get("detail"):
                                feedback_lines.append(f"- {r.get('detail', '')}")
                feedback = "\n".join(feedback_lines) if feedback_lines else "请优化设计文档质量"
                prev_ver = fix_round - 1
                prev_path = os.path.join(docs_dir, f"{slug}_{prefix}_V{prev_ver}.md")

                fix_instruction = (
                    f"你是资深架构师后旺（HouWang）。\n"
                    f"项目：{proj_name}\n核心目标：{core_goal}\n"
                    f"需求文档：{requirement[:3000]}\n"
                    f"请根据以下检验反馈，修改设计文档（{prev_path}）。\n"
                    "⚠️ 收敛性要求：仅修复以下不合格项，禁止扩大修改范围，已合格项目不得改动。\n\n"
                    f"=== 需要修复的问题 ===\n{feedback}\n"
                    "不要输出推理过程。"
                )
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"🔄 {label}：houwang 根据hourong反馈修复（第{fix_round}轮）...",
                    "subflow": doc_type,
                })
                client = GatewayClient(profile_name="houwang", timeout=1200)
                chunks = []
                async for chunk in client.chat_isolated(
                    messages=[{"role": "user", "content": fix_instruction}],
                    project_id=project_id, project_name=proj_name,
                    project_description=proj_desc, core_goal=core_goal,
                    agent_name=f"后旺-{doc_type}设计师",
                    stream=True, max_tokens=64000,
                    project_slug=slug,
                ):
                    if chunk.strip():
                        chunks.append(chunk)
                        await broadcast(project_id, {
                            "type": "progress", "content": chunk,
                            "subflow": doc_type,
                        })
                content = "".join(chunks).strip()

            with open(gen_path, "w", encoding="utf-8") as f:
                f.write(content)
            final_path = gen_path

            if not content.strip():
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"⚠️ {label}：houwang未生成有效内容，重试",
                    "subflow": doc_type,
                })
                continue

            # hourong 检验
            await broadcast(project_id, {
                "type": "stage",
                "message": f"🔍 {label}：hourong 正在检验（第{fix_round}轮）...",
                "subflow": doc_type,
            })

            focus_hint = ""
            if failed_dim_keys:
                focus_hint = f"\n⚠️ 本次只检验不合格维度：{failed_dim_keys}，禁止扩大范围。"
            convergence_hint = (
                "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。"
                "后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
            )
            scoring_hint = (
                "\n评分规则：整体评分1-5分，≥4分为合格。"
                "每个维度起始100分，每发现一个缺陷扣减相应分数（轻微扣5-10，一般扣15-20，严重扣25-30）。"
                "维度得分≥90则该维度passed为true。"
            )

            insp_prompt = (
                "你是一个专业的设计方案QA检验员（后荣）。请严格检验以下设计文档。\n\n"
                f"=== {label} ===\n{content}\n\n"
                f"{focus_hint}{convergence_hint}{scoring_hint}\n\n"
                "只输出 JSON 数组，不要其他文字：\n"
                f'[{{"key": "{dim_key}", "score": 100, "deduction": "", "passed": true/false, "detail": "具体检验意见..."}}]'
            )

            qa_r = await _inspect_via_subagent(prompt=insp_prompt, max_retries=3)

            brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
            if brace_s != -1 and brace_e > brace_s:
                qa_r = qa_r[brace_s:brace_e]
            try:
                parsed = _json.loads(qa_r) if qa_r else None
            except Exception:
                parsed = None

            if not parsed or not isinstance(parsed, list):
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"⚠️ {label}：hourong返回格式异常，跳过本轮检验",
                    "subflow": doc_type,
                })
                continue

            dim_passed = True
            dim_results = []
            for r in parsed:
                score = int(r.get("score", 100))
                passed = r.get("passed", score >= 90)
                if isinstance(passed, str):
                    passed = passed.lower() == "true"
                case_passed = passed and score >= 90
                if not case_passed:
                    dim_passed = False
                dim_results.append({
                    "key": r.get("key", dim_key),
                    "score": score,
                    "passed": case_passed,
                    "detail": r.get("detail", ""),
                })

            convergence_log.append({
                "dim_key": dim_key,
                "round": fix_round,
                "passed": dim_passed,
                "results": dim_results,
            })

            if dim_passed:
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"✅ {label}：已通过 hourong 检验（共{fix_round}轮）",
                    "subflow": doc_type,
                })
                merged[f"design_doc_{doc_type.lower()}"] = content
                merged[f"{prefix}_path"] = final_path
                break
            else:
                failed_dim_keys = [r.get("key", dim_key) for r in dim_results if not r["passed"]]
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"⚠️ {label}：未通过检验，houwang 正在针对不合格项修复（第{fix_round}轮）",
                    "subflow": doc_type,
                })
        else:
            await broadcast(project_id, {
                "type": "stage",
                "message": f"❌ {label}：经10轮仍未通过检验",
                "subflow": doc_type,
            })
            merged[f"design_doc_{doc_type.lower()}"] = content
            merged[f"{prefix}_path"] = final_path

    merged["status"] = "done"
    merged["convergence_log"] = convergence_log
    engine.save_step4_artifacts(merged)
    engine.complete_step(4)
