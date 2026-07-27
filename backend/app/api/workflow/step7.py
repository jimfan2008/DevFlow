import json
from datetime import datetime, timezone
import glob
from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest,
    TDD_TESTCASE_DIMENSIONS, Step7ChatRequest, _wf_engines, WorkflowEngine,
)


@router.post("/{project_id}/step7/chat")
async def step7_chat(project_id: str, body: Step7ChatRequest,
                     db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """后发（HouFa）对话 - 项目隔离"""
    from app.services.gateway_client import GatewayClient
    from app.models.project import Project
    try:
        engine = _get_engine(project_id, db)
        step2 = engine.get_step2_artifacts()
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        messages = body.messages + [{"role": "user", "content": body.message}]
        client = GatewayClient(profile_name="houfa", timeout=1200)
        reply_chunks = []
        async for chunk in client.chat_completions(messages=messages, stream=False):
            reply_chunks.append(chunk)
        reply = "".join(reply_chunks)
        if not reply or len(reply.strip()) < 5:
            return APIResponse(code=1, message="后发未生成有效回复", data=None)
        return APIResponse(code=0, message="success", data={"reply": reply})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step7 chat: {e}")
        return APIResponse(code=1, message="与后发对话失败", data=None)


async def _inspect_tdd_cases(project_id: str, doc_path: str, project_name: str = "", project_description: str = "", core_goal: str = "", agent_label: str = "", max_retries: int = 3, focus_items: Optional[list[str]] = None) -> dict:
    import json as _json, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step7_progress import broadcast
    active_dims = [d for d in TDD_TESTCASE_DIMENSIONS if not focus_items or d["key"] in focus_items]
    if not active_dims:
        return {"passed": True, "detail": "无待检验项", "failed_details": [], "failed_keys": [], "results": []}
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in active_dims])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "progress", "message": f"🔄 hourong 第{attempt}次重新检验TDD用例..."})
        focus_hint = f"\n⚠️ 本轮只检验以下项目（上一轮未通过）：{[d['label'] for d in active_dims]}" if focus_items else ""
        insp_prompt = f"你是一个专业的TDD测试用例QA检验员（后荣）。请严格检验以下测试用例。\n\n=== 检验项目与标准 ===\n{dims_json}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n只输出 JSON 数组，不要有其他文字:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims) + f"{focus_hint}\n"
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_completions(messages=[{"role": "user", "content": insp_prompt}], stream=True, max_tokens=8192):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 未返回，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回"}
        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}
        if isinstance(parsed, list) and parsed:
            failed_keys = [r.get("key", "") for r in parsed if not r.get("passed")]
            return {"passed": all(bool(r.get("passed")) for r in parsed), "detail": "", "failed_details": [r.get("detail", "") for r in parsed if not r.get("passed")], "failed_keys": failed_keys, "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


@router.post("/{project_id}/step7/execute")
async def execute_step7_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """异步启动第七步：后发编写TDD测试用例，hourong 自动检验+收敛修复"""
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        if resume:
            existing = engine.get_step7_artifacts() or {}
        else:
            step7_row = engine._get_step_row(7)
            if step7_row and step7_row.status == "in_progress":
                engine.reset_step(7)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            try:
                from sqlalchemy import text
                engine.db.execute(
                    text("UPDATE workflow_steps SET status='in_progress', started_at=:now, output_artifacts=:arts WHERE project_id=:pid AND step_number=7"),
                    {"now": datetime.now(timezone.utc).isoformat(), "arts": json.dumps({"status": "generating", "message": "Step 7 started..."}), "pid": project_id}
                )
                engine.db.execute(
                    text("UPDATE projects SET current_step=7 WHERE id=:pid"),
                    {"pid": project_id}
                )
                engine.db.commit()
                engine.current_step = 7
            except Exception as e:
                logger.error(f"[STEP7_DEBUG] start failed: {e}")
                return APIResponse(code=1, message=f"无法开始步骤7: {str(e)[:200]}")
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤7: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""

    step6 = engine.get_step6_artifacts() or {}
    tdd_plan = step6.get("tdd_plan") or step6.get("plan_content") or ""

    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    
    async def _generate():
        try:
            from app.database import SessionLocal
            from app.models.project import Project
            from app.api.ws.step7_progress import broadcast
            bg_db = SessionLocal()
            try:
                bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                proj = bg_db.query(Project).filter(Project.id == project_id).first()
                slug = proj.slug if proj else project_id.replace("-", "")
                docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
                os.makedirs(docs_dir, exist_ok=True)
                proj_name = proj.name if proj else ""
                proj_desc = proj.description or ""


                prev = existing if resume else {}
                if resume and prev.get("qa_passed") and prev.get("doc_path") and os.path.exists(prev["doc_path"]):
                    await broadcast(project_id, {"type": "progress", "message": "♻️ 续跑：TDD用例已通过检验，跳过"})
                    bg_engine.save_step7_artifacts({**prev, "status": "done", "message": "♻️ 续跑：TDD用例已通过"})
                    bg_engine.complete_step(7)
                    await broadcast(project_id, {"type": "done", "message": "✅ TDD用例已生成（续跑）"})
                    return

                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_tdctest_V*.md")):
                    import re as _re
                    m = _re.search(r'V(\d+)', os.path.basename(f))
                    if m:
                        max_ver = max(max_ver, int(m.group(1)))
                convergence_log, final_path, final_content = [], "", ""
                fix_round = 0
                while True:
                    fix_round += 1
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_tdctest_V{nv}.md")
                    await broadcast(project_id, {"type": "progress", "message": f"🧪 后发正在{'修复' if fix_round > 1 else '编写'}TDD用例（第{fix_round}轮）..."})
                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        failed = convergence_log[-1].get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)
                    prompt = (
                        "你是资深程序员后发（HouFa），负责编写完整的TDD测试用例。\n\n"
                        f"=== 需求文档 ===\n{requirement}\n\n=== 架构设计文档 ===\n{design_doc}\n\n"
                        f"=== TDD测试用例编写计划 ===\n{str(tdd_plan)}\n\n"
                        + (f"=== 上次检验未通过项 ===\n{feedback}\n只针对不合格项修改，不要扩大修改范围。\n\n" if feedback else "")
                        + f"请将完整测试用例保存到：{gen_path}\n要求：1.每个测试用例最小原子化 2.每个测试用例有明确可量化验收标准\n3.按计划的优先级和执行顺序编写 4.直接输出测试用例代码和文档\n不要输出推理过程。"
                    )
                    client = GatewayClient(profile_name="houfa", timeout=7200)
                    chunks = []
                    await broadcast(project_id, {"type": "stage", "message": f"🤖 后发正在{'修复' if fix_round > 1 else '编写'}TDD用例（第{fix_round}轮）..."})
                    async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=True, max_tokens=64000):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "content", "content": chunk})
                    if os.path.exists(gen_path):
                        content = open(gen_path, "r", encoding="utf-8").read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    if not content.strip():
                        await broadcast(project_id, {"type": "progress", "message": "❌ 后发未生成有效内容，重试"})
                        continue
                    final_path, final_content = gen_path, content
                    bg_engine.save_step7_artifacts({"tdd_cases": content, "doc_path": gen_path, "status": "generating"})
                    await broadcast(project_id, {"type": "progress", "message": f"🔍 hourong 正在检验TDD用例（文件：{gen_path}）"})
                    focus_items = []
                    if fix_round > 1 and convergence_log:
                        focus_items = convergence_log[-1].get("failed_keys", [])
                    qa_result = await _inspect_tdd_cases(project_id, gen_path, focus_items=focus_items or None)
                    convergence_log.append({"detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", []), "failed_keys": qa_result.get("failed_keys", [])})
                    bg_engine.save_step7_artifacts({"tdd_cases": content, "doc_path": gen_path, "convergence": convergence_log, "status": "generating", "message": f"第{fix_round}轮QA结果已保存"})
                    if qa_result.get("passed"):
                        await broadcast(project_id, {"type": "progress", "message": f"✅ TDD用例已通过 hourong 检验（共{fix_round}轮）"})
                        bg_engine.save_step7_artifacts({"tdd_cases": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ TDD用例编写完成"})
                        bg_engine.complete_step(7)
                        await broadcast(project_id, {"type": "done", "message": "✅ TDD用例已生成"})
                        return
                    await broadcast(project_id, {"type": "progress", "message": f"⚠️ 未通过，修复中"})
                await broadcast(project_id, {"type": "progress", "message": f"🔄 第{fix_round}轮未通过，自动退回重做..."})
            except Exception as e:
                logger.error(f"Step7: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step7_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
                    bg_engine.reset_step(7)
                except Exception as e2:
                    logger.error(f"Step7 failed to reset: {e2}", exc_info=True)
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step7 fatal: {e}")
        finally:
            from app.services.haimei_executor import HaimeiStepExecutor
            HaimeiStepExecutor._tasks.pop(f"{project_id}:step7", None)
    task = _asyncio.create_task(_generate())
    from app.services.haimei_executor import HaimeiStepExecutor
    task_key = f"{project_id}:step7"
    HaimeiStepExecutor._tasks[task_key] = task
    return APIResponse(code=0, data={"message": "第七步已启动", "status": "generating"})


@router.post("/{project_id}/step7/reset")
def reset_step7(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(7)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第七步已重置"})


@router.get("/{project_id}/step7/status")
def get_step7_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step7_artifacts())


@router.post("/{project_id}/step7/artifacts")
def save_step7_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step7_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤7状态已保存"})


@router.post("/{project_id}/step7/inspect")
async def inspect_step7(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services.gateway_client import GatewayClient
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in TDD_TESTCASE_DIMENSIONS]})
    active_dims = [d for d in TDD_TESTCASE_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    prompt = f"你是一个专业的TDD测试用例QA检验员（后荣）。\n\n=== TDD用例 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
    try:
        client = GatewayClient(profile_name="hourong", timeout=120)
        chunks = []
        async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=False, max_tokens=2000):
            chunks.append(chunk)
        reply = "".join(chunks).strip()
        if not reply:
            raise ValueError("后荣未返回")
        parsed = _json.loads(reply)
        if not isinstance(parsed, list):
            raise ValueError("不是数组")
    except Exception:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in active_dims]})
    results = []
    for dim in active_dims:
        m = next((r for r in parsed if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "passed": bool(m.get("passed", False)) if m else False, "detail": m.get("detail", "") if m else ""})
    return APIResponse(code=0, data={"passed": all(r["passed"] for r in results), "dimensions": results})


@router.post("/{project_id}/step7/qa")
def qa_step7(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(7)
    else:
        result = engine.fail_qa(7, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"第七步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})