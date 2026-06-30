import json as _json
import os
import glob
import re as _re
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

TDD_PLAN_DIMENSIONS = [
    {"key": "coverage", "label": "覆盖率", "description": "测试用例是否覆盖所有功能和非功能需求"},
    {"key": "atomicity", "label": "原子性", "description": "每个测试用例是否最小原子化"},
    {"key": "verifiability", "label": "可验证性", "description": "验收标准是否明确可量化"},
    {"key": "priority", "label": "优先级", "description": "是否标注优先级和执行顺序"},
    {"key": "feasibility", "label": "可行性", "description": "测试用例是否在技术上可执行"},
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


async def _inspect_tdd_plan(
    websocket: WebSocket, project_id: str, doc_content: str,
    project_name: str = "", project_description: str = "",
    core_goal: str = "", agent_label: str = "",
    max_retries: int = 3,
) -> dict:
    import asyncio as _asyncio
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in TDD_PLAN_DIMENSIONS])

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "progress", "message": f"🔄 hourong 正在第{attempt}次重新检验TDD计划..."})

        if not doc_content or not doc_content.strip():
            await broadcast(project_id, {"type": "error", "message": "❌ 检验文档内容为空，无法检验"})
            return {"detail": "文档内容为空"}

        insp_prompt = (
            "你是一个专业的测试计划QA检验员（后荣）。请严格检验以下TDD测试用例编写计划。\n\n"
            "=== 检验项目与标准 ===\n"
            f"{dims_json}\n\n"
            "=== 待检验文档内容 ===\n"
            f"{doc_content[:20000]}\n\n"
            "请严格逐项检验。\n"
            "⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。"
            "后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。\n"
            "只输出 JSON 数组，不要有其他文字:\n"
            + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in TDD_PLAN_DIMENSIONS) + "\n"
        )
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(
            messages=[{"role": "user", "content": insp_prompt}],
            project_id=project_id, project_name=project_name, project_description=project_description,
            core_goal=core_goal, agent_name=agent_label or "后荣-TDD计划QA检验员",
            stream=True, max_tokens=8192,
        ):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()

        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 未返回检验结果，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回检验结果"}

        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 返回无法解析的报告，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}

        if isinstance(parsed, list) and parsed:
            all_passed = all(bool(r.get("passed")) for r in parsed)
            return {"passed": all_passed, "detail": "", "failed_details": [r.get("detail", "") for r in parsed if not r.get("passed")], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 返回格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


async def _run_step6(websocket: WebSocket, project_id: str, db) -> bool:
    """执行步骤6：海梅制订TDD测试用例计划，hourong自动检验+收敛修复"""
    import asyncio as _asyncio

    # Register this WS for broadcasts
    if websocket not in _active_connections.get(project_id, []):
        _active_connections.setdefault(project_id, []).append(websocket)

    try:
        engine = WorkflowEngine(project_id=project_id, db=db)
        engine.advance_step(6)

        # Gather context from previous steps
        step3 = engine.get_step3_artifacts() or {}
        requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
        step4 = engine.get_step4_artifacts() or {}
        design_doc = step4.get("design_doc") or ""
        step5 = engine.get_step5_artifacts() or {}
        env_info = step5.get("env_info") or step5.get("environment") or ""
        step2 = engine.get_step2_artifacts() or {}
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        engine.save_step6_artifacts({"status": "generating", "message": "📋 海梅正在制订TDD测试用例编写计划..."})
        await broadcast(project_id, {"type": "progress", "message": "📋 海梅正在制订TDD测试用例编写计划..."})

        # Resolve project info
        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            await broadcast(project_id, {"type": "error", "message": "Project not found"})
            return True
        slug = proj.slug or project_id.replace("-", "")
        docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        proj_name = proj.name
        proj_desc = proj.description or ""

        # Check for existing artifacts (resume case)
        existing = engine.get_step6_artifacts() or {}
        if existing.get("qa_passed") and existing.get("doc_path") and os.path.exists(existing["doc_path"]):
            engine.save_step6_artifacts({**existing, "status": "done", "message": "♻️ 续跑：TDD计划已通过检验，跳过"})
            engine.complete_step(6, artifacts={**engine.get_step6_artifacts(), "qa_passed": True})
            await broadcast(project_id, {"type": "done", "message": "✅ TDD计划已生成（续跑）"})
            return True

        # ── 获取参考文档路径（禁止在prompt中包含文档内容）──
        srs_path = step3.get("doc_path") or step3.get("file_path") or ""
        if not srs_path or not os.path.exists(srs_path):
            max_sv = 0
            for f in glob.glob(os.path.join(docs_dir, f"{slug}_SRS_V*.md")):
                m = _re.search(r'V(\d+)', os.path.basename(f))
                if m: max_sv = max(max_sv, int(m.group(1)))
            if max_sv > 0:
                srs_path = os.path.join(docs_dir, f"{slug}_SRS_V{max_sv}.md")
            elif requirement:
                srs_path = os.path.join(docs_dir, f"{slug}_SRS_V1.md")
                with open(srs_path, "w", encoding="utf-8") as f:
                    f.write(requirement)

        design_path = ""
        design_doc_paths = step4.get("doc_paths", {})
        if isinstance(design_doc_paths, dict):
            design_path = design_doc_paths.get('arch_reasonableness', '') or design_doc_paths.get('architecture', '')
        if not design_path or not os.path.exists(design_path):
            max_dv = 0
            for f in glob.glob(os.path.join(docs_dir, f"{slug}_ARCHITECTURE_V*.md")):
                m = _re.search(r'V(\d+)', os.path.basename(f))
                if m: max_dv = max(max_dv, int(m.group(1)))
            if max_dv > 0:
                design_path = os.path.join(docs_dir, f"{slug}_ARCHITECTURE_V{max_dv}.md")
            elif design_doc:
                design_path = os.path.join(docs_dir, f"{slug}_ARCHITECTURE_V1.md")
                with open(design_path, "w", encoding="utf-8") as f:
                    f.write(design_doc)

        env_path = ""
        if env_info:
            max_ev = 0
            for f in glob.glob(os.path.join(docs_dir, f"{slug}_ENV_V*.md")):
                m = _re.search(r'V(\d+)', os.path.basename(f))
                if m: max_ev = max(max_ev, int(m.group(1)))
            if max_ev > 0:
                env_path = os.path.join(docs_dir, f"{slug}_ENV_V{max_ev}.md")
            else:
                env_path = os.path.join(docs_dir, f"{slug}_ENV_V1.md")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(env_info)

        max_ver = 0
        for f in glob.glob(os.path.join(docs_dir, f"{slug}_tddplan_V*.md")):
            m = _re.search(r'V(\d+)', os.path.basename(f))
            if m: max_ver = max(max_ver, int(m.group(1)))

        convergence_log, final_path, final_content = [], "", ""

        # Check for existing TDD doc on disk that never passed QA — skip haimei, go straight to hourong
        _skip_arts = engine.get_step6_artifacts() or {}
        _skip_doc = _skip_arts.get("tdd_plan", "")
        if not _skip_doc and _skip_arts.get("doc_path") and os.path.exists(_skip_arts["doc_path"]):
            try:
                with open(_skip_arts["doc_path"], "r", encoding="utf-8") as f:
                    _skip_doc = f.read()
            except Exception:
                pass
        if not _skip_doc and max_ver > 0:
            latest_path = os.path.join(docs_dir, f"{slug}_tddplan_V{max_ver}.md")
            if os.path.exists(latest_path):
                try:
                    with open(latest_path, "r", encoding="utf-8") as f:
                        _skip_doc = f.read()
                    if _skip_doc and _skip_doc.strip():
                        _skip_arts["doc_path"] = latest_path
                except Exception:
                    pass
        skip_haimei_round1 = bool(_skip_doc and _skip_doc.strip())

        for fix_round in range(1, 11):
            nv = max_ver + fix_round
            gen_path = os.path.join(docs_dir, f"{slug}_tddplan_V{nv}.md")

            if skip_haimei_round1 and fix_round == 1:
                content = _skip_doc
                if not os.path.exists(gen_path) or _skip_arts.get("doc_path") != gen_path:
                    with open(gen_path, "w", encoding="utf-8") as f:
                        f.write(content)
                skip_haimei_round1 = False
                await broadcast(project_id, {"type": "progress", "message": f"⏩ 使用已有TDD计划文档，跳过海梅生成，直接提交hourong检验（第{fix_round}轮）"})
                await broadcast(project_id, {"type": "prompt", "prompt": "(使用已有文档，跳过海梅生成)", "round": fix_round, "total_rounds": 10})
            else:
                await broadcast(project_id, {"type": "progress", "message": f"📋 海梅正在{'修复' if fix_round > 1 else '制订'}TDD计划（第{fix_round}轮）..."})

                feedback = ""
                if fix_round > 1 and convergence_log:
                    last = convergence_log[-1]
                    failed = last.get("failed_details", [])
                    feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)

                prompt_lines = [
                    "你是资深项目经理海梅（HaiMei），负责制订TDD测试用例编写计划。\n",
                ]
                if srs_path:
                    try:
                        with open(srs_path, "r", encoding="utf-8") as _f:
                            _srs = _f.read()
                    except Exception:
                        _srs = ""
                    if _srs:
                        prompt_lines.append(f"=== 需求文档（SRS） ===\n{_srs[:15000]}\n\n")
                    else:
                        prompt_lines.append(f"请读取需求文档（SRS）：{srs_path}\n\n")
                if design_path:
                    try:
                        with open(design_path, "r", encoding="utf-8") as _f:
                            _design = _f.read()
                    except Exception:
                        _design = ""
                    if _design:
                        prompt_lines.append(f"=== 架构设计文档 ===\n{_design[:30000]}\n\n")
                    else:
                        prompt_lines.append(f"请读取架构设计文档：{design_path}\n\n")
                if env_path:
                    try:
                        with open(env_path, "r", encoding="utf-8") as _f:
                            _env = _f.read()
                    except Exception:
                        _env = ""
                    if _env:
                        prompt_lines.append(f"=== 开发环境信息 ===\n{_env[:10000]}\n\n")
                    else:
                        prompt_lines.append(f"请读取开发环境信息：{env_path}\n\n")
                if feedback:
                    prompt_lines.append(f"=== 上次检验未通过项 ===\n{feedback}\n请只针对不合格项修改，不要扩大修改范围。\n\n")
                prompt_lines.append(
                    f"请将完整计划保存到：{gen_path}\n"
                    "要求：1.每个测试用例最小原子化 2.每个测试用例有明确可量化验收标准\n"
                    "3.覆盖所有功能和非功能需求 4.标注优先级和执行顺序\n不要输出推理过程。"
                )
                prompt = "\n".join(prompt_lines)

                # Send the haimei prompt for frontend display
                await broadcast(project_id, {"type": "prompt", "prompt": prompt, "round": fix_round, "total_rounds": 10})

                client = GatewayClient(profile_name="haimei", timeout=3600)
                chunks = []
                try:
                    async for chunk in client.chat_isolated(
                        messages=[{"role": "user", "content": prompt}],
                        project_id=project_id, project_name=proj_name, project_description=proj_desc,
                        core_goal=core_goal, agent_name="海梅（HaiMei）-TDD计划制订",
                        stream=True, max_tokens=64000,
                    ):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "content", "content": chunk})
                except Exception as e:
                    logger.error(f"Step6 haimei调用失败: {e}", exc_info=True)
                    await broadcast(project_id, {"type": "error", "message": f"❌ 海梅执行失败: {str(e)[:100]}"})
                    engine.reset_step(6)
                    return True

                if os.path.exists(gen_path):
                    with open(gen_path, "r", encoding="utf-8") as f:
                        content = f.read()
                else:
                    content = "".join(chunks).strip()
                    with open(gen_path, "w", encoding="utf-8") as f:
                        f.write(content)

                if not content.strip():
                    await broadcast(project_id, {"type": "progress", "message": "❌ 海梅未生成有效内容，重试"})
                    continue

            final_path, final_content = gen_path, content
            engine.save_step6_artifacts({"tdd_plan": content, "doc_path": gen_path, "status": "generating"})

            await broadcast(project_id, {"type": "progress", "message": f"🔍 hourong 正在检验TDD计划（第{fix_round}轮）"})
            qa_result = await _inspect_tdd_plan(websocket, project_id, content, project_name=proj_name, project_description=proj_desc, core_goal=core_goal)

            # If hourong failed to return a valid report, retry within the same round (never send to haimei fix without a report)
            hr_retry = 0
            while "passed" not in qa_result and hr_retry < 3:
                hr_retry += 1
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong未生成有效检验报告，第{hr_retry}次重新检验..."})
                qa_result = await _inspect_tdd_plan(websocket, project_id, content, project_name=proj_name, project_description=proj_desc, core_goal=core_goal)

            if "passed" not in qa_result:
                await broadcast(project_id, {"type": "error", "message": "❌ hourong多次无法生成有效检验报告，终止步骤"})
                convergence_log.append({"round": fix_round, "detail": "hourong多次未能生成有效检验报告", "passed": False, "failed_details": ["hourong检验失败"]})
                break

            if qa_result.get("passed"):
                await broadcast(project_id, {"type": "progress", "message": f"✅ TDD计划已通过 hourong 检验（共{fix_round}轮）"})
                engine.save_step6_artifacts({"tdd_plan": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ TDD计划制订完成"})
                engine.complete_step(6, artifacts={**engine.get_step6_artifacts(), "qa_passed": True})
                await broadcast(project_id, {"type": "done", "message": "✅ TDD计划已生成"})
                return True

            await broadcast(project_id, {"type": "progress", "message": f"⚠️ 未通过：{'；'.join(str(d) for d in qa_result.get('failed_details', ['未知']))[:80]}，修复中"})

        await broadcast(project_id, {"type": "progress", "message": "❌ 经10轮仍未通过检验"})
        await broadcast(project_id, {"type": "error", "message": "❌ 经10轮仍未通过检验"})
        engine.save_step6_artifacts({"tdd_plan": final_content, "doc_path": final_path, "convergence": convergence_log, "status": "error"})
        engine.reset_step(6)
        return True

    except Exception as e:
        logger.error(f"Step6 execution error: {e}", exc_info=True)
        try:
            err_engine = WorkflowEngine(project_id=project_id, db=db)
            err_engine.reset_step(6)
        except Exception:
            pass
        await broadcast(project_id, {"type": "error", "message": f"❌ 步骤6失败: {str(e)[:200]}"})
        return True


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
        try:
            while True:
                data = await websocket.receive_text()
                logger.info(f"Step6 WS received: {data}")
                payload = _json.loads(data)
                action = payload.get("action", "")
                logger.info(f"Step6 action: {action}")

                if action == "execute":
                    logger.info(f"Step6: Starting _run_step6 for project {project_id}")
                    should_close = await _run_step6(websocket, project_id, db)
                    logger.info(f"Step6: _run_step6 completed for project {project_id}")
                    if should_close:
                        break

                elif action == "subscribe":
                    logger.info(f"Step6: Subscribed for project {project_id}")
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
        logger.error(f"Step6 WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()
